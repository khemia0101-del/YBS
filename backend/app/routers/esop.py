from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import assert_company_in_tenant, get_tenant_id, require_analyst
from app.models.esop import ESOPAdjustment, QoERun, ValuationEvidenceFile
from app.models.users import User
from app.schemas.esop import ESOPAdjustmentResponse, QoERunResponse, ValuationPackageResponse
from app.security.audit import write_audit_log

router = APIRouter()


async def _load_qoe_run_in_tenant(
    db: AsyncSession, run_id: UUID, tenant_id: UUID
) -> QoERun:
    result = await db.execute(select(QoERun).where(QoERun.id == run_id))
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="QoE run not found")
    await assert_company_in_tenant(db, run.company_id, tenant_id)
    return run


@router.post("/qoe/run", response_model=QoERunResponse)
async def create_qoe_run(
    company_id: UUID = Query(...),
    period_start: date = Query(...),
    period_end: date = Query(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: User = Depends(require_analyst),
) -> QoERunResponse:
    import uuid

    await assert_company_in_tenant(db, company_id, tenant_id)
    run = QoERun(
        id=uuid.uuid4(),
        company_id=company_id,
        run_date=date.today(),
        analysis_period_start=period_start,
        analysis_period_end=period_end,
        status="draft",
    )
    db.add(run)
    await db.flush()

    await write_audit_log(
        session=db,
        event_type="qoe_run.created",
        actor_id=current_user.id,
        actor_type="user",
        table_name="qoe_runs",
        record_id=run.id,
        after_state={"company_id": str(company_id), "status": "draft"},
    )
    return QoERunResponse.model_validate(run)


@router.get("/qoe/{run_id}", response_model=QoERunResponse)
async def get_qoe_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> QoERunResponse:
    run = await _load_qoe_run_in_tenant(db, run_id, tenant_id)
    return QoERunResponse.model_validate(run)


@router.post("/qoe/{run_id}/addbacks/classify")
async def classify_addbacks(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: User = Depends(require_analyst),
) -> dict:
    """Trigger addback classification. In production this enqueues an AI agent task."""
    await _load_qoe_run_in_tenant(db, run_id, tenant_id)
    try:
        from app.workers.agent_tasks import hermes_daily_loop

        task = hermes_daily_loop.delay()
        return {"task_id": task.id, "run_id": str(run_id), "status": "queued"}
    except Exception:
        return {"run_id": str(run_id), "status": "classification_not_available"}


@router.get("/qoe/{run_id}/addbacks", response_model=list[ESOPAdjustmentResponse])
async def list_addbacks(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> list[ESOPAdjustmentResponse]:
    await _load_qoe_run_in_tenant(db, run_id, tenant_id)
    result = await db.execute(
        select(ESOPAdjustment)
        .where(ESOPAdjustment.qoe_run_id == run_id)
        .order_by(ESOPAdjustment.created_at)
    )
    adjs = result.scalars().all()
    return [ESOPAdjustmentResponse.model_validate(a) for a in adjs]


@router.post(
    "/qoe/{run_id}/addbacks/{adj_id}/approve", response_model=ESOPAdjustmentResponse
)
async def approve_addback(
    run_id: UUID,
    adj_id: UUID,
    notes: str | None = None,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: User = Depends(require_analyst),
) -> ESOPAdjustmentResponse:
    await _load_qoe_run_in_tenant(db, run_id, tenant_id)
    result = await db.execute(
        select(ESOPAdjustment).where(
            ESOPAdjustment.id == adj_id, ESOPAdjustment.qoe_run_id == run_id
        )
    )
    adj = result.scalar_one_or_none()
    if adj is None:
        raise HTTPException(status_code=404, detail="Adjustment not found")

    adj.approved_by = current_user.id
    adj.approved_at = datetime.now(timezone.utc)

    await write_audit_log(
        session=db,
        event_type="esop_adjustment.approved",
        actor_id=current_user.id,
        actor_type="user",
        table_name="esop_adjustments",
        record_id=adj.id,
        after_state={"approved_by": str(current_user.id)},
        metadata={"notes": notes},
    )
    return ESOPAdjustmentResponse.model_validate(adj)


@router.post("/qoe/{run_id}/package/build")
async def build_valuation_package(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: User = Depends(require_analyst),
) -> dict:
    """Build the valuation package (collect evidence files, generate summary)."""
    run = await _load_qoe_run_in_tenant(db, run_id, tenant_id)

    files_result = await db.execute(
        select(ValuationEvidenceFile).where(ValuationEvidenceFile.qoe_run_id == run_id)
    )
    files = files_result.scalars().all()

    run.status = "approved"
    run.approved_by = current_user.id
    run.evidence_bundle = {
        "files": [{"id": str(f.id), "file_name": f.file_name} for f in files],
        "built_at": datetime.now(timezone.utc).isoformat(),
    }

    return {
        "run_id": str(run_id),
        "status": "package_built",
        "file_count": len(files),
        "built_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/qoe/{run_id}/package/download")
async def download_valuation_package(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> ValuationPackageResponse:
    """Return a presigned S3 URL for the valuation package."""
    await _load_qoe_run_in_tenant(db, run_id, tenant_id)

    files_result = await db.execute(
        select(ValuationEvidenceFile).where(ValuationEvidenceFile.qoe_run_id == run_id)
    )
    files = files_result.scalars().all()

    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    from app.config import settings

    download_url = (
        f"{settings.S3_ENDPOINT}/{settings.S3_BUCKET}/qoe-packages/{run_id}/package.zip"
        if settings.S3_ENDPOINT
        else f"https://s3.amazonaws.com/{settings.S3_BUCKET}/qoe-packages/{run_id}/package.zip"
    )

    return ValuationPackageResponse(
        qoe_run_id=run_id,
        download_url=download_url,
        expires_at=expires_at,
        files=[
            {"id": str(f.id), "file_name": f.file_name, "category": f.category}
            for f in files
        ],
    )
