"""
Unit tests for the confidence scoring engine.
"""
from __future__ import annotations

import pytest

from app.services.staging.confidence import SOURCE_RELIABILITY, score_extraction


# ---------------------------------------------------------------------------
# Source reliability weights
# ---------------------------------------------------------------------------


def test_quickbooks_highest_reliability() -> None:
    assert SOURCE_RELIABILITY["quickbooks"] > SOURCE_RELIABILITY["email"]
    assert SOURCE_RELIABILITY["quickbooks"] >= 0.90


def test_email_lowest_non_manual() -> None:
    non_manual = {k: v for k, v in SOURCE_RELIABILITY.items() if k != "manual"}
    assert SOURCE_RELIABILITY["email"] == min(non_manual.values())


# ---------------------------------------------------------------------------
# Completeness scoring
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "record_type, extracted_data, source, expected_min_score",
    [
        # Perfect invoice from QuickBooks
        (
            "invoice",
            {
                "customer_id": "cust-123",
                "invoice_date": "2024-03-01",
                "amount": "5000.00",
                "invoice_number": "INV-001",
                "due_date": "2024-04-01",
                "contract_id": "ctr-456",
            },
            "quickbooks",
            0.80,
        ),
        # Minimal invoice from email
        (
            "invoice",
            {
                "customer_id": "cust-123",
                "invoice_date": "2024-03-01",
                "amount": "5000.00",
            },
            "email",
            0.50,
        ),
        # Complete labor shift from payroll
        (
            "labor_shift",
            {
                "employee_id": "EMP-001",
                "shift_date": "2024-03-01",
                "hours_worked": "8.0",
                "worker_type": "W2",
                "clock_in": "2024-03-01T08:00:00",
                "clock_out": "2024-03-01T16:00:00",
                "hourly_rate": "18.00",
            },
            "payroll",
            0.75,
        ),
        # Missing required fields
        (
            "contract",
            {
                "customer_id": "cust-123",
                # missing start_date, monthly_value, contract_type
            },
            "manual",
            0.30,
        ),
        # Unknown record type with no required fields
        (
            "unknown_type",
            {"anything": "goes"},
            "manual",
            0.70,  # Default source reliability dominates
        ),
    ],
)
def test_score_extraction_thresholds(
    record_type: str,
    extracted_data: dict,
    source: str,
    expected_min_score: float,
) -> None:
    result = score_extraction(
        record_type=record_type,
        extracted_data=extracted_data,
        match_suggestions=[],
        source_system=source,
    )
    assert "overall" in result
    assert 0.0 <= result["overall"] <= 1.0
    assert result["overall"] >= expected_min_score, (
        f"Expected score >= {expected_min_score} for {record_type}/{source}, "
        f"got {result['overall']}. Reasons: {result['reasons']}"
    )


def test_match_corroboration_boosts_score() -> None:
    """Having a high-confidence match suggestion should increase overall score."""
    base = score_extraction(
        record_type="customer",
        extracted_data={"name": "Acme Corp", "customer_type": "commercial"},
        match_suggestions=[],
        source_system="manual",
    )
    with_match = score_extraction(
        record_type="customer",
        extracted_data={"name": "Acme Corp", "customer_type": "commercial"},
        match_suggestions=[{"entity_id": "aaa-111", "score": 0.95}],
        source_system="manual",
    )
    assert with_match["overall"] > base["overall"]


def test_missing_required_fields_penalizes_score() -> None:
    complete = score_extraction(
        record_type="invoice",
        extracted_data={
            "customer_id": "cust-123",
            "invoice_date": "2024-01-01",
            "amount": "100.00",
        },
        match_suggestions=[],
        source_system="quickbooks",
    )
    incomplete = score_extraction(
        record_type="invoice",
        extracted_data={},  # No required fields
        match_suggestions=[],
        source_system="quickbooks",
    )
    assert complete["overall"] > incomplete["overall"]


def test_result_has_expected_keys() -> None:
    result = score_extraction(
        record_type="payment",
        extracted_data={"customer_id": "c1", "payment_date": "2024-01-01", "amount": "500"},
        match_suggestions=[],
        source_system="bank_csv",
    )
    required_keys = {"overall", "field_scores", "reasons", "source_reliability", "completeness"}
    assert required_keys.issubset(result.keys())


def test_score_never_exceeds_one() -> None:
    """Score must be capped at 1.0 regardless of inputs."""
    result = score_extraction(
        record_type="invoice",
        extracted_data={
            "customer_id": "c",
            "invoice_date": "2024-01-01",
            "amount": "999",
            "invoice_number": "I1",
            "due_date": "2024-02-01",
            "contract_id": "ctr",
        },
        match_suggestions=[
            {"entity_id": "x", "score": 1.0},
            {"entity_id": "y", "score": 0.99},
        ],
        source_system="quickbooks",
    )
    assert result["overall"] <= 1.0
