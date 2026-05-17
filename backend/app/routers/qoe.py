"""Quality-of-Earnings analysis — runs the QoE engine + baseline valuation."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import assert_company_in_tenant, get_tenant_id, require_analyst
from app.models.esop import QoERun
from app.schemas.qoe import QoEAnalyzeRequest
from app.services.qoe.crr_data import (
    COMPANY_NAME,
    CRR_CONTEXT,
    CRR_PERIODS,
    VALUATION_RATIONALE,
)
from app.services.qoe.engine import FinancialPeriod, analyze
from app.services.qoe.report import render_markdown
from app.services.qoe.valuation import value_by_sde

router = APIRouter()


def _run_qoe(periods, primary_label, multiples, rationale):
    qoe = analyze(periods, primary_label=primary_label)
    valuation = value_by_sde(
        qoe.primary.sde,
        low_multiple=multiples[0],
        mid_multiple=multiples[1],
        high_multiple=multiples[2],
        rationale=rationale,
    )
    return qoe, valuation


@router.post("/analyze")
async def analyze_qoe(
    body: QoEAnalyzeRequest,
    company_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    user=Depends(require_analyst),
) -> dict:
    """Run a QoE analysis for a business and (optionally) persist it as a QoERun."""
    await assert_company_in_tenant(db, company_id, tenant_id)

    periods = [FinancialPeriod.from_payload(p.model_dump()) for p in body.periods]
    qoe, valuation = _run_qoe(
        periods,
        body.primary_label,
        (body.low_multiple, body.mid_multiple, body.high_multiple),
        body.valuation_rationale,
    )

    run_id: str | None = None
    if body.persist:
        run = QoERun(
            id=uuid.uuid4(),
            company_id=company_id,
            run_date=date.today(),
            analysis_period_start=date.today(),
            analysis_period_end=date.today(),
            status="draft",
            reported_ebitda=qoe.primary.reported_ebitda,
            adjusted_ebitda=qoe.primary.adjusted_ebitda,
            normalized_ebitda=qoe.primary.sde,
            evidence_bundle={"qoe": qoe.as_dict(), "valuation": valuation.as_dict()},
        )
        db.add(run)
        await db.flush()
        run_id = str(run.id)

    return {
        "run_id": run_id,
        "qoe": qoe.as_dict(),
        "valuation": valuation.as_dict(),
    }


@router.get("/crr-baseline")
async def crr_baseline(
    company_id: UUID = Query(...),
    as_markdown: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> dict:
    """The Credit Repair Resources baseline QoE, computed from its data-room P&Ls."""
    await assert_company_in_tenant(db, company_id, tenant_id)
    qoe, valuation = _run_qoe(
        CRR_PERIODS, "FY2024", (2.0, 2.75, 3.5), VALUATION_RATIONALE
    )
    payload = {
        "company": COMPANY_NAME,
        "qoe": qoe.as_dict(),
        "valuation": valuation.as_dict(),
    }
    if as_markdown:
        payload["markdown"] = render_markdown(
            COMPANY_NAME, qoe, valuation, CRR_PERIODS, context=CRR_CONTEXT
        )
    return payload
