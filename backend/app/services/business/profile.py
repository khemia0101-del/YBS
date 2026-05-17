"""
Business profile helpers.

The profile is the adaptive core: metrics, automation, and growth engines all read it
instead of hardcoding a vertical. ``CREDIT_REPAIR_METRICS`` seeds CRR and serves as a
reference template; the AI interviewer (Phase 5) infers an equivalent set for any other
business from its own inputs.
"""
from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business import BusinessProfile, MetricDefinition


async def get_or_create_profile(db: AsyncSession, company_id: UUID) -> BusinessProfile:
    """Return the company's profile, creating an empty one on first access."""
    result = await db.execute(
        select(BusinessProfile).where(BusinessProfile.company_id == company_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = BusinessProfile(
            id=uuid.uuid4(), company_id=company_id, source="manual"
        )
        db.add(profile)
        await db.flush()
    return profile


# Starter KPI set for a credit-repair business.
CREDIT_REPAIR_METRICS: list[dict] = [
    {
        "key": "active_members", "name": "Active Members", "unit": "count",
        "category": "growth", "is_north_star": True,
        "description": "Subscribers with an active credit-repair plan.",
    },
    {
        "key": "mrr", "name": "Monthly Recurring Revenue", "unit": "currency",
        "category": "financial",
    },
    {
        "key": "new_enrollments", "name": "New Enrollments / Month", "unit": "count",
        "category": "growth",
    },
    {
        "key": "churn_rate", "name": "Monthly Churn Rate", "unit": "percent",
        "category": "growth",
    },
    {
        "key": "arpu", "name": "Average Revenue per User", "unit": "currency",
        "category": "financial",
    },
    {
        "key": "cac", "name": "Customer Acquisition Cost", "unit": "currency",
        "category": "growth",
    },
    {
        "key": "ltv", "name": "Lifetime Value", "unit": "currency",
        "category": "financial",
    },
    {
        "key": "files_per_month", "name": "Files Processed / Month", "unit": "count",
        "category": "operational",
    },
    {
        "key": "dispute_success_rate", "name": "Dispute Success Rate", "unit": "percent",
        "category": "operational",
    },
    {
        "key": "gross_margin", "name": "Gross Margin", "unit": "percent",
        "category": "financial",
    },
    {
        "key": "sde", "name": "Seller's Discretionary Earnings", "unit": "currency",
        "category": "financial",
    },
]


def build_metric_definitions(
    company_id: UUID, profile_id: UUID, templates: list[dict]
) -> list[MetricDefinition]:
    """Materialize metric-definition rows from a list of template dicts."""
    rows: list[MetricDefinition] = []
    for t in templates:
        rows.append(
            MetricDefinition(
                id=uuid.uuid4(),
                company_id=company_id,
                profile_id=profile_id,
                key=t["key"],
                name=t["name"],
                description=t.get("description"),
                unit=t.get("unit", "count"),
                category=t.get("category"),
                source=t.get("source", "manual"),
                formula=t.get("formula"),
                is_north_star=t.get("is_north_star", False),
            )
        )
    return rows
