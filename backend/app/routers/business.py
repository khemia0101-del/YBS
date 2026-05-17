"""Adaptive business profile + metric definitions/snapshots — tenant-scoped."""
from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import assert_company_in_tenant, get_tenant_id, require_analyst
from app.models.business import BusinessProfile, MetricDefinition, MetricSnapshot
from app.schemas.business import (
    BusinessProfileResponse,
    BusinessProfileUpdate,
    MetricDefinitionCreate,
    MetricDefinitionResponse,
    MetricDefinitionUpdate,
    MetricSnapshotCreate,
    MetricSnapshotResponse,
)
from app.services.business.profile import get_or_create_profile

router = APIRouter()


async def _metric_in_tenant(
    db: AsyncSession, metric_id: UUID, tenant_id: UUID
) -> MetricDefinition:
    result = await db.execute(
        select(MetricDefinition).where(MetricDefinition.id == metric_id)
    )
    metric = result.scalar_one_or_none()
    if metric is None:
        raise HTTPException(status_code=404, detail="Metric not found")
    await assert_company_in_tenant(db, metric.company_id, tenant_id)
    return metric


@router.get("/profile", response_model=BusinessProfileResponse)
async def get_profile(
    company_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> BusinessProfileResponse:
    await assert_company_in_tenant(db, company_id, tenant_id)
    profile = await get_or_create_profile(db, company_id)
    return BusinessProfileResponse.model_validate(profile)


@router.put("/profile", response_model=BusinessProfileResponse)
async def update_profile(
    body: BusinessProfileUpdate,
    company_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _user=Depends(require_analyst),
) -> BusinessProfileResponse:
    await assert_company_in_tenant(db, company_id, tenant_id)
    profile = await get_or_create_profile(db, company_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    await db.flush()
    return BusinessProfileResponse.model_validate(profile)


@router.get("/metrics", response_model=list[MetricDefinitionResponse])
async def list_metrics(
    company_id: UUID = Query(...),
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> list[MetricDefinitionResponse]:
    await assert_company_in_tenant(db, company_id, tenant_id)
    q = select(MetricDefinition).where(MetricDefinition.company_id == company_id)
    if not include_inactive:
        q = q.where(MetricDefinition.is_active.is_(True))
    result = await db.execute(q.order_by(MetricDefinition.category, MetricDefinition.name))
    return [MetricDefinitionResponse.model_validate(m) for m in result.scalars().all()]


@router.post("/metrics", response_model=MetricDefinitionResponse)
async def create_metric(
    body: MetricDefinitionCreate,
    company_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _user=Depends(require_analyst),
) -> MetricDefinitionResponse:
    await assert_company_in_tenant(db, company_id, tenant_id)
    existing = await db.execute(
        select(MetricDefinition).where(
            MetricDefinition.company_id == company_id, MetricDefinition.key == body.key
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Metric key '{body.key}' already exists")

    profile = await get_or_create_profile(db, company_id)
    metric = MetricDefinition(
        id=uuid.uuid4(),
        company_id=company_id,
        profile_id=profile.id,
        **body.model_dump(),
    )
    db.add(metric)
    await db.flush()
    return MetricDefinitionResponse.model_validate(metric)


@router.patch("/metrics/{metric_id}", response_model=MetricDefinitionResponse)
async def update_metric(
    metric_id: UUID,
    body: MetricDefinitionUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _user=Depends(require_analyst),
) -> MetricDefinitionResponse:
    metric = await _metric_in_tenant(db, metric_id, tenant_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(metric, field, value)
    await db.flush()
    return MetricDefinitionResponse.model_validate(metric)


@router.get(
    "/metrics/{metric_id}/snapshots", response_model=list[MetricSnapshotResponse]
)
async def list_snapshots(
    metric_id: UUID,
    limit: int = Query(90, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> list[MetricSnapshotResponse]:
    await _metric_in_tenant(db, metric_id, tenant_id)
    result = await db.execute(
        select(MetricSnapshot)
        .where(MetricSnapshot.metric_definition_id == metric_id)
        .order_by(MetricSnapshot.period_date.desc())
        .limit(limit)
    )
    return [MetricSnapshotResponse.model_validate(s) for s in result.scalars().all()]


@router.post(
    "/metrics/{metric_id}/snapshots", response_model=MetricSnapshotResponse
)
async def add_snapshot(
    metric_id: UUID,
    body: MetricSnapshotCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _user=Depends(require_analyst),
) -> MetricSnapshotResponse:
    metric = await _metric_in_tenant(db, metric_id, tenant_id)
    snapshot = MetricSnapshot(
        id=uuid.uuid4(),
        company_id=metric.company_id,
        metric_definition_id=metric_id,
        period_date=body.period_date,
        period_type=body.period_type,
        value=body.value,
        source=body.source,
    )
    db.add(snapshot)
    await db.flush()
    return MetricSnapshotResponse.model_validate(snapshot)
