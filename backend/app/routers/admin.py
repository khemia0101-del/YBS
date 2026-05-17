from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_tenant_id, require_admin
from app.models.audit import AuditLog
from app.models.users import User
from app.schemas.auth import UserResponse
from app.security.auth import hash_password
from app.config import settings

router = APIRouter()


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _user=Depends(require_admin),
) -> list[UserResponse]:
    result = await db.execute(
        select(User)
        .where(User.tenant_id == tenant_id)
        .order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@router.post("/users", response_model=UserResponse)
async def create_user(
    email: str,
    password: str,
    full_name: str | None = None,
    role: str = "viewer",
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _user=Depends(require_admin),
) -> UserResponse:
    # Check uniqueness
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already exists")

    valid_roles = {"admin", "analyst", "operator", "viewer", "agent"}
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")

    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return UserResponse.model_validate(user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    role: str | None = None,
    is_active: bool | None = None,
    full_name: str | None = None,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _user=Depends(require_admin),
) -> UserResponse:
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == tenant_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if role is not None:
        valid_roles = {"admin", "analyst", "operator", "viewer", "agent"}
        if role not in valid_roles:
            raise HTTPException(status_code=400, detail=f"Invalid role: {role}")
        user.role = role
    if is_active is not None:
        user.is_active = is_active
    if full_name is not None:
        user.full_name = full_name

    return UserResponse.model_validate(user)


@router.get("/audit-logs")
async def get_audit_logs(
    event_type: str | None = Query(None),
    actor_type: str | None = Query(None),
    table_name: str | None = Query(None),
    actor_id: UUID | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_admin),
) -> dict:
    q = select(AuditLog)
    if event_type:
        q = q.where(AuditLog.event_type == event_type)
    if actor_type:
        q = q.where(AuditLog.actor_type == actor_type)
    if table_name:
        q = q.where(AuditLog.table_name == table_name)
    if actor_id:
        q = q.where(AuditLog.actor_id == actor_id)
    if date_from:
        q = q.where(AuditLog.created_at >= date_from)
    if date_to:
        q = q.where(AuditLog.created_at <= date_to)

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar() or 0

    q = q.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    logs = result.scalars().all()

    return {
        "items": [
            {
                "id": str(l.id),
                "event_type": l.event_type,
                "actor_id": str(l.actor_id) if l.actor_id else None,
                "actor_type": l.actor_type,
                "table_name": l.table_name,
                "record_id": str(l.record_id) if l.record_id else None,
                "before_state": l.before_state,
                "after_state": l.after_state,
                "created_at": l.created_at.isoformat(),
            }
            for l in logs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
    }


@router.get("/system-health")
async def system_health(
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_admin),
) -> dict:
    import psutil
    import redis as sync_redis

    # DB pool stats
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
        from app.database import engine

        pool = engine.pool
        db_info = {
            "status": db_status,
            "pool_size": pool.size(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
        }
    except Exception as exc:
        db_info = {"status": f"error: {exc}"}

    # Redis
    try:
        r = sync_redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        r.ping()
        redis_info_raw = r.info("server")
        redis_info = {
            "status": "ok",
            "version": redis_info_raw.get("redis_version"),
            "uptime_seconds": redis_info_raw.get("uptime_in_seconds"),
        }
        r.close()
    except Exception as exc:
        redis_info = {"status": f"error: {exc}"}

    # Celery workers (via inspect)
    celery_info: dict = {}
    try:
        from app.workers.celery_app import app as celery_app

        inspect = celery_app.control.inspect(timeout=2)
        active = inspect.active()
        celery_info = {
            "status": "ok" if active else "no_workers",
            "workers": list(active.keys()) if active else [],
        }
    except Exception as exc:
        celery_info = {"status": f"error: {exc}"}

    # System
    sys_info = {
        "cpu_pct": psutil.cpu_percent(interval=0.1),
        "memory_pct": psutil.virtual_memory().percent,
        "disk_pct": psutil.disk_usage("/").percent,
    }

    return {
        "db": db_info,
        "redis": redis_info,
        "celery": celery_info,
        "system": sys_info,
        "version": "0.1.0",
    }
