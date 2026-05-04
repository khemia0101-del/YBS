from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_active_user, require_operator
from app.models.raw import StagedRecord
from app.models.users import User
from app.schemas.common import PaginatedResponse
from app.schemas.staging import (
    ApproveRequest,
    BulkApproveRequest,
    ExceptionResponse,
    ExceptionStats,
    MatchRequest,
)
from app.security.audit import write_audit_log

router = APIRouter()


@router.get("/exceptions", response_model=PaginatedResponse[ExceptionResponse])
async def list_exceptions(
    status: str | None = Query(None),
    record_type: str | None = Query(None),
    confidence_min: float | None = Query(None, ge=0, le=1),
    confidence_max: float | None = Query(None, ge=0, le=1),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
) -> PaginatedResponse[ExceptionResponse]:
    q = select(StagedRecord)
    if status:
        q = q.where(StagedRecord.status == status)
    if record_type:
        q = q.where(StagedRecord.record_type == record_type)
    if confidence_min is not None:
        q = q.where(StagedRecord.confidence_score >= confidence_min)
    if confidence_max is not None:
        q = q.where(StagedRecord.confidence_score <= confidence_max)
    if date_from:
        q = q.where(StagedRecord.created_at >= date_from)
    if date_to:
        q = q.where(StagedRecord.created_at <= date_to)

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar() or 0

    q = q.order_by(StagedRecord.created_at.desc())
    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    items = result.scalars().all()

    pages = max(1, (total + page_size - 1) // page_size)
    return PaginatedResponse(
        items=[ExceptionResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/exceptions/{exception_id}", response_model=ExceptionResponse)
async def get_exception(
    exception_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
) -> ExceptionResponse:
    result = await db.execute(
        select(StagedRecord).where(StagedRecord.id == exception_id)
    )
    rec = result.scalar_one_or_none()
    if rec is None:
        raise HTTPException(status_code=404, detail="Staged record not found")
    return ExceptionResponse.model_validate(rec)


@router.post("/exceptions/{exception_id}/approve", response_model=ExceptionResponse)
async def approve_exception(
    exception_id: UUID,
    body: ApproveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_operator),
) -> ExceptionResponse:
    result = await db.execute(
        select(StagedRecord).where(StagedRecord.id == exception_id)
    )
    rec = result.scalar_one_or_none()
    if rec is None:
        raise HTTPException(status_code=404, detail="Staged record not found")
    if rec.status not in ("pending", "needs_review"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot approve record with status '{rec.status}'",
        )

    before = {"status": rec.status}
    rec.status = "approved"
    rec.reviewed_by = current_user.id
    rec.reviewed_at = datetime.now(timezone.utc)
    rec.review_notes = body.notes

    await write_audit_log(
        session=db,
        event_type="staged_record.approved",
        actor_id=current_user.id,
        actor_type="user",
        table_name="staged_records",
        record_id=rec.id,
        before_state=before,
        after_state={"status": "approved"},
    )
    return ExceptionResponse.model_validate(rec)


@router.post("/exceptions/{exception_id}/reject", response_model=ExceptionResponse)
async def reject_exception(
    exception_id: UUID,
    body: ApproveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_operator),
) -> ExceptionResponse:
    result = await db.execute(
        select(StagedRecord).where(StagedRecord.id == exception_id)
    )
    rec = result.scalar_one_or_none()
    if rec is None:
        raise HTTPException(status_code=404, detail="Staged record not found")

    before = {"status": rec.status}
    rec.status = "rejected"
    rec.reviewed_by = current_user.id
    rec.reviewed_at = datetime.now(timezone.utc)
    rec.review_notes = body.notes

    await write_audit_log(
        session=db,
        event_type="staged_record.rejected",
        actor_id=current_user.id,
        actor_type="user",
        table_name="staged_records",
        record_id=rec.id,
        before_state=before,
        after_state={"status": "rejected"},
    )
    return ExceptionResponse.model_validate(rec)


@router.post("/exceptions/{exception_id}/match", response_model=ExceptionResponse)
async def match_exception(
    exception_id: UUID,
    body: MatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_operator),
) -> ExceptionResponse:
    result = await db.execute(
        select(StagedRecord).where(StagedRecord.id == exception_id)
    )
    rec = result.scalar_one_or_none()
    if rec is None:
        raise HTTPException(status_code=404, detail="Staged record not found")

    before_data = dict(rec.extracted_data or {})
    extracted = dict(rec.extracted_data or {})
    extracted["matched_entity_id"] = str(body.entity_id)
    extracted["matched_entity_type"] = body.entity_type
    rec.extracted_data = extracted
    rec.status = "approved"
    rec.reviewed_by = current_user.id
    rec.reviewed_at = datetime.now(timezone.utc)
    rec.review_notes = body.notes

    await write_audit_log(
        session=db,
        event_type="staged_record.matched",
        actor_id=current_user.id,
        actor_type="user",
        table_name="staged_records",
        record_id=rec.id,
        before_state={"extracted_data": before_data},
        after_state={"matched_entity_id": str(body.entity_id)},
    )
    return ExceptionResponse.model_validate(rec)


@router.post("/exceptions/bulk-approve")
async def bulk_approve(
    body: BulkApproveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_operator),
) -> dict:
    if not body.ids:
        return {"approved": 0, "failed": []}

    result = await db.execute(
        select(StagedRecord).where(StagedRecord.id.in_(body.ids))
    )
    records = result.scalars().all()
    approved = 0
    failed = []
    now = datetime.now(timezone.utc)

    for rec in records:
        if rec.status in ("pending", "needs_review"):
            rec.status = "approved"
            rec.reviewed_by = current_user.id
            rec.reviewed_at = now
            rec.review_notes = body.notes
            approved += 1
        else:
            failed.append(str(rec.id))

    return {"approved": approved, "failed": failed}


@router.get("/stats", response_model=ExceptionStats)
async def staging_stats(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
) -> ExceptionStats:
    total_result = await db.execute(select(func.count(StagedRecord.id)))
    total = total_result.scalar() or 0

    status_rows = await db.execute(
        select(StagedRecord.status, func.count(StagedRecord.id)).group_by(StagedRecord.status)
    )
    by_status = {row[0]: row[1] for row in status_rows}

    type_rows = await db.execute(
        select(StagedRecord.record_type, func.count(StagedRecord.id)).group_by(
            StagedRecord.record_type
        )
    )
    by_record_type = {row[0]: row[1] for row in type_rows}

    avg_conf_result = await db.execute(select(func.avg(StagedRecord.confidence_score)))
    avg_conf = avg_conf_result.scalar()

    auto_result = await db.execute(
        select(func.count(StagedRecord.id)).where(StagedRecord.status == "auto_approved")
    )
    auto_count = auto_result.scalar() or 0
    auto_approve_rate = (auto_count / total) if total > 0 else None

    return ExceptionStats(
        total=total,
        by_status=by_status,
        by_record_type=by_record_type,
        avg_confidence=float(avg_conf) if avg_conf is not None else None,
        auto_approve_rate=auto_approve_rate,
    )
