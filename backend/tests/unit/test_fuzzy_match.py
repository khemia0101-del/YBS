"""
Unit tests for customer name fuzzy matching and payment matching.
"""
from __future__ import annotations

from decimal import Decimal
from datetime import date

import pytest

from app.services.staging.fuzzy_match import (
    compute_customer_match_score,
    compute_payment_match_score,
)


# ---------------------------------------------------------------------------
# Customer name matching
# ---------------------------------------------------------------------------

CUSTOMERS = [
    {"id": "aaa-111", "name": "Acme Corporation", "name_aliases": ["Acme Corp", "ACME"]},
    {"id": "bbb-222", "name": "TechCorp Industries", "name_aliases": ["TechCorp"]},
    {"id": "ccc-333", "name": "Blue Sky Services LLC", "name_aliases": ["Blue Sky", "BSS"]},
    {"id": "ddd-444", "name": "Smith & Associates", "name_aliases": None},
]


@pytest.mark.parametrize(
    "query, expected_top_id, min_score",
    [
        # Exact match
        ("Acme Corporation", "aaa-111", 0.95),
        # Alias match
        ("ACME", "aaa-111", 0.70),
        # Abbreviation — BSS should match Blue Sky Services LLC via alias
        ("BSS", "ccc-333", 0.60),
        # Typo — "Accme Corp"
        ("Accme Corp", "aaa-111", 0.60),
        # Partial "TechCorp"
        ("TechCorp", "bbb-222", 0.80),
        # No reasonable match
    ],
)
def test_customer_match_top_result(
    query: str, expected_top_id: str, min_score: float
) -> None:
    results = compute_customer_match_score(query, CUSTOMERS)
    assert len(results) > 0, f"Expected matches for '{query}', got none"
    top = results[0]
    assert top["entity_id"] == expected_top_id, (
        f"Expected top match '{expected_top_id}' for query '{query}', got '{top['entity_id']}'"
    )
    assert top["score"] >= min_score, (
        f"Expected score >= {min_score} for '{query}', got {top['score']}"
    )


def test_customer_match_returns_max_three() -> None:
    results = compute_customer_match_score("Corp", CUSTOMERS)
    assert len(results) <= 3


def test_customer_match_empty_candidates() -> None:
    results = compute_customer_match_score("Acme", [])
    assert results == []


def test_customer_match_deduplicates_aliases() -> None:
    """Each entity_id should appear at most once, even if both name and alias match."""
    results = compute_customer_match_score("Acme Corp", CUSTOMERS)
    ids = [r["entity_id"] for r in results]
    assert len(ids) == len(set(ids)), "Duplicate entity_ids in results"


def test_customer_match_score_normalized() -> None:
    """Scores should be in [0, 1] range."""
    results = compute_customer_match_score("Acme Corporation", CUSTOMERS)
    for r in results:
        assert 0.0 <= r["score"] <= 1.0, f"Score out of range: {r['score']}"


# ---------------------------------------------------------------------------
# Payment matching
# ---------------------------------------------------------------------------

INVOICES = [
    {
        "id": "inv-001",
        "amount": Decimal("5000.00"),
        "invoice_date": date(2024, 3, 1),
        "invoice_number": "INV-2024-001",
    },
    {
        "id": "inv-002",
        "amount": Decimal("12500.00"),
        "invoice_date": date(2024, 3, 15),
        "invoice_number": "INV-2024-002",
    },
    {
        "id": "inv-003",
        "amount": Decimal("750.00"),
        "invoice_date": date(2024, 2, 1),
        "invoice_number": "INV-2024-003",
    },
]


def test_exact_amount_match_with_reference() -> None:
    payment = {
        "amount": Decimal("5000.00"),
        "date": date(2024, 3, 5),
        "reference": "INV-2024-001",
    }
    results = compute_payment_match_score(payment, INVOICES)
    assert len(results) > 0
    top = results[0]
    assert top["entity_id"] == "inv-001"
    assert top["score"] >= 0.90  # Both amount and reference match perfectly


def test_near_exact_amount_match() -> None:
    payment = {
        "amount": Decimal("4999.99"),  # Within $0.01
        "date": date(2024, 3, 3),
        "reference": None,
    }
    results = compute_payment_match_score(payment, INVOICES)
    top = results[0]
    assert top["entity_id"] == "inv-001"
    assert top["breakdown"]["amount_score"] == 1.0  # Within $0.01 tolerance


def test_wrong_amount_no_match() -> None:
    payment = {
        "amount": Decimal("9999.00"),  # No close match
        "date": date(2024, 3, 1),
        "reference": None,
    }
    results = compute_payment_match_score(payment, INVOICES)
    # All scores should be low (amount mismatch = 0, only date contributes)
    for r in results:
        assert r["score"] < 0.50


def test_date_proximity_scoring() -> None:
    """Payment 3 days after invoice date should get high date score."""
    payment = {
        "amount": Decimal("12500.00"),
        "date": date(2024, 3, 18),  # 3 days after INV-2024-002
        "reference": None,
    }
    results = compute_payment_match_score(payment, INVOICES)
    inv2_result = next((r for r in results if r["entity_id"] == "inv-002"), None)
    assert inv2_result is not None
    assert inv2_result["breakdown"]["date_score"] == 1.0


def test_returns_at_most_5_results() -> None:
    many_invoices = [
        {
            "id": f"inv-{i:03d}",
            "amount": Decimal("5000.00"),
            "invoice_date": date(2024, 1, i + 1),
            "invoice_number": f"INV-{i:03d}",
        }
        for i in range(10)
    ]
    payment = {"amount": Decimal("5000.00"), "date": date(2024, 1, 5), "reference": None}
    results = compute_payment_match_score(payment, many_invoices)
    assert len(results) <= 5
