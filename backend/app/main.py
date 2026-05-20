from __future__ import annotations

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (
    admin,
    agents,
    approvals,
    auth,
    automation,
    business,
    cash,
    contracts,
    coo,
    customers,
    decisions,
    employee_tasks,
    esop,
    financial,
    growth,
    health,
    ingestion,
    integrations,
    interview,
    knowledge,
    monitor,
    qoe,
    staging,
    tenants,
)

logger = structlog.get_logger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="YBS OS",
        version="0.1.0",
        description="Financial Truth Reconstruction and ESOP Readiness Platform",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Root health check (no prefix)
    app.include_router(health.router)

    # Versioned API routes
    v1 = settings.API_V1_PREFIX
    app.include_router(auth.router, prefix=f"{v1}/auth", tags=["auth"])
    app.include_router(tenants.router, prefix=f"{v1}/tenants", tags=["tenants"])
    app.include_router(business.router, prefix=f"{v1}/business", tags=["business"])
    app.include_router(
        integrations.router, prefix=f"{v1}/integrations", tags=["integrations"]
    )
    app.include_router(ingestion.router, prefix=f"{v1}/ingestion", tags=["ingestion"])
    app.include_router(staging.router, prefix=f"{v1}/staging", tags=["staging"])
    app.include_router(customers.router, prefix=f"{v1}/customers", tags=["customers"])
    app.include_router(contracts.router, prefix=f"{v1}/contracts", tags=["contracts"])
    app.include_router(financial.router, prefix=f"{v1}/financial", tags=["financial"])
    app.include_router(cash.router, prefix=f"{v1}/cash", tags=["cash"])
    app.include_router(decisions.router, prefix=f"{v1}/decisions", tags=["decisions"])
    app.include_router(esop.router, prefix=f"{v1}/esop", tags=["esop"])
    app.include_router(qoe.router, prefix=f"{v1}/qoe", tags=["qoe"])
    app.include_router(interview.router, prefix=f"{v1}/interview", tags=["interview"])
    app.include_router(
        automation.router, prefix=f"{v1}/automation", tags=["automation"]
    )
    app.include_router(growth.router, prefix=f"{v1}/growth", tags=["growth"])
    app.include_router(coo.router, prefix=f"{v1}/coo", tags=["coo"])
    app.include_router(knowledge.router, prefix=f"{v1}/knowledge", tags=["knowledge"])
    app.include_router(monitor.router, prefix=f"{v1}/monitor", tags=["monitor"])
    app.include_router(
        employee_tasks.router, prefix=f"{v1}/employee-tasks", tags=["employee-tasks"]
    )
    app.include_router(agents.router, prefix=f"{v1}/agents", tags=["agents"])
    app.include_router(approvals.router, prefix=f"{v1}/approvals", tags=["approvals"])
    app.include_router(admin.router, prefix=f"{v1}/admin", tags=["admin"])

    @app.on_event("startup")
    async def on_startup() -> None:
        logger.info("YBS OS starting up", environment=settings.ENVIRONMENT)

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        from app.database import engine
        await engine.dispose()
        logger.info("YBS OS shut down cleanly")

    return app


app = create_app()
