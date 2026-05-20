"""Self-improving monitor — observations, diagnoses, approval."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import (
    assert_company_in_tenant,
    get_tenant_id,
    require_admin,
    require_analyst,
    tenant_company_ids,
)
from app.models.monitor import AgentObservation, MonitorDiagnosis
from app.models.users import User
from app.schemas.monitor import (
    ApproveDiagnosisResponse,
    DiagnosisResponse,
    ObservationResponse,
    RunMonitorResponse,
)
from app.services.monitor import github
from app.services.monitor.agent import diagnose
from app.services.monitor.collectors import run_all_collectors
from app.services.monitor.reviewer import review

router = APIRouter()


async def _tenant_filter(db: AsyncSession, tenant_id: UUID) -> list[UUID]:
    return await tenant_company_ids(db, tenant_id)


@router.post("/run", response_model=RunMonitorResponse)
async def run_monitor(
    db: AsyncSession = Depends(get_db),
    _tenant_id: UUID = Depends(get_tenant_id),
    _user: User = Depends(require_admin),
) -> RunMonitorResponse:
    """Run all collectors + diagnose every new observation. Admin only."""
    counts = await run_all_collectors(db)
    new_obs = (
        await db.execute(
            select(AgentObservation).where(AgentObservation.status == "new")
        )
    ).scalars().all()
    diagnosed = 0
    for obs in new_obs:
        diag = await diagnose(db, obs.id)
        if diag is not None:
            await review(db, diag.id)
            diagnosed += 1
    return RunMonitorResponse(
        observations_collected=counts, diagnoses_drafted=diagnosed
    )


@router.get("/observations", response_model=list[ObservationResponse])
async def list_observations(
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> list[ObservationResponse]:
    allowed = await _tenant_filter(db, tenant_id)
    stmt = select(AgentObservation).where(
        (AgentObservation.company_id.is_(None))
        | (AgentObservation.company_id.in_(allowed))
    )
    if status_filter:
        stmt = stmt.where(AgentObservation.status == status_filter)
    stmt = stmt.order_by(AgentObservation.created_at.desc())
    rows = (await db.execute(stmt)).scalars().all()
    return [ObservationResponse.model_validate(o) for o in rows]


@router.get("/diagnoses", response_model=list[DiagnosisResponse])
async def list_diagnoses(
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> list[DiagnosisResponse]:
    allowed = await _tenant_filter(db, tenant_id)
    stmt = (
        select(MonitorDiagnosis)
        .join(
            AgentObservation,
            MonitorDiagnosis.observation_id == AgentObservation.id,
        )
        .where(
            (AgentObservation.company_id.is_(None))
            | (AgentObservation.company_id.in_(allowed))
        )
        .order_by(MonitorDiagnosis.created_at.desc())
    )
    if status_filter:
        stmt = stmt.where(MonitorDiagnosis.status == status_filter)
    rows = (await db.execute(stmt)).scalars().all()
    return [DiagnosisResponse.model_validate(d) for d in rows]


async def _load_diagnosis(
    db: AsyncSession, diagnosis_id: UUID, tenant_id: UUID
) -> MonitorDiagnosis:
    diag = (
        await db.execute(
            select(MonitorDiagnosis).where(MonitorDiagnosis.id == diagnosis_id)
        )
    ).scalar_one_or_none()
    if diag is None:
        raise HTTPException(status_code=404, detail="Diagnosis not found")
    obs = (
        await db.execute(
            select(AgentObservation).where(
                AgentObservation.id == diag.observation_id
            )
        )
    ).scalar_one_or_none()
    if obs is not None and obs.company_id is not None:
        await assert_company_in_tenant(db, obs.company_id, tenant_id)
    return diag


@router.post(
    "/diagnoses/{diagnosis_id}/approve", response_model=ApproveDiagnosisResponse
)
async def approve_diagnosis(
    diagnosis_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _user: User = Depends(require_analyst),
) -> ApproveDiagnosisResponse:
    """Approve a diagnosis. Stores the PR description; if GitHub configured, opens a draft PR."""
    diag = await _load_diagnosis(db, diagnosis_id, tenant_id)
    if diag.status != "proposed":
        raise HTTPException(status_code=409, detail=f"Diagnosis is '{diag.status}'")
    diag.status = "approved"
    diag.pr_description = github.render_pr_description(diag)
    gh_result = await github.open_draft_pr(diag)
    if gh_result.get("status") == "created" and gh_result.get("url"):
        diag.pr_url = gh_result["url"]
    await db.flush()
    return ApproveDiagnosisResponse(
        diagnosis=DiagnosisResponse.model_validate(diag),
        github=gh_result,
    )


@router.post("/diagnoses/{diagnosis_id}/reject", response_model=DiagnosisResponse)
async def reject_diagnosis(
    diagnosis_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _user: User = Depends(require_analyst),
) -> DiagnosisResponse:
    diag = await _load_diagnosis(db, diagnosis_id, tenant_id)
    if diag.status != "proposed":
        raise HTTPException(status_code=409, detail=f"Diagnosis is '{diag.status}'")
    diag.status = "rejected"
    await db.flush()
    return DiagnosisResponse.model_validate(diag)
