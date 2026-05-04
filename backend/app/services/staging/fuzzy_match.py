from __future__ import annotations

from datetime import date
from decimal import Decimal

from rapidfuzz import fuzz, process

CUSTOMER_MATCH_THRESHOLD = 60  # minimum score (0-100) to include
PAYMENT_AMOUNT_TOLERANCE_PCT = Decimal("0.01")  # 1% tolerance


def compute_customer_match_score(
    name: str,
    existing_customers: list[dict],
) -> list[dict]:
    """
    Fuzzy-match an extracted customer name against known customers.

    Each existing_customer dict should have keys: id, name, name_aliases (list[str] | None).
    Returns top 3 matches above CUSTOMER_MATCH_THRESHOLD, sorted descending by score.

    Score (0-100) uses RapidFuzz WRatio which handles partial matches, transpositions,
    and abbreviation scenarios common in business names.
    """
    if not existing_customers:
        return []

    # Build a flat list of (display_name, entity_id, canonical_name) for scoring
    candidates: list[tuple[str, str, str]] = []
    for cust in existing_customers:
        cust_id = str(cust["id"])
        canonical = cust["name"]
        candidates.append((canonical, cust_id, canonical))
        for alias in (cust.get("name_aliases") or []):
            if alias:
                candidates.append((alias, cust_id, canonical))

    if not candidates:
        return []

    candidate_names = [c[0] for c in candidates]

    # Use process.extract for bulk scoring
    matches = process.extract(
        name,
        candidate_names,
        scorer=fuzz.WRatio,
        limit=20,
        score_cutoff=CUSTOMER_MATCH_THRESHOLD,
    )

    # Deduplicate by entity_id, keeping best score
    seen: dict[str, dict] = {}
    for match_name, score, idx in matches:
        _, cust_id, canonical = candidates[idx]
        if cust_id not in seen or seen[cust_id]["score"] < score:
            seen[cust_id] = {
                "entity_id": cust_id,
                "name": canonical,
                "score": round(score / 100, 4),  # normalize to 0-1
                "matched_alias": match_name if match_name != canonical else None,
            }

    result = sorted(seen.values(), key=lambda x: x["score"], reverse=True)
    return result[:3]


def compute_payment_match_score(
    payment: dict,
    open_invoices: list[dict],
) -> list[dict]:
    """
    Score how well a payment matches a list of open invoices.

    Payment dict keys: amount (Decimal|str|float), date (date|str), reference (str|None)
    Invoice dict keys: id (str), amount (Decimal|str|float), invoice_date (date|str),
                       invoice_number (str|None)

    Scoring weights:
    - Amount match (50%): exact ±$0.01 = 1.0, ±1% = 0.8, else 0
    - Date proximity (30%): ≤5 days = 1.0, 6–15 = 0.7, 16–30 = 0.4, >30 = 0
    - Reference match (20%): substring match = 0.9, else 0

    Returns sorted list of {entity_id, score, breakdown}.
    """
    pay_amount = Decimal(str(payment.get("amount", 0)))
    pay_ref = str(payment.get("reference") or "").strip().lower()

    pay_date = payment.get("date")
    if isinstance(pay_date, str):
        from datetime import datetime

        try:
            pay_date = datetime.fromisoformat(pay_date).date()
        except ValueError:
            pay_date = None
    elif not isinstance(pay_date, date):
        pay_date = None

    results = []
    for inv in open_invoices:
        inv_amount = Decimal(str(inv.get("amount", 0)))
        inv_num = str(inv.get("invoice_number") or "").strip().lower()

        inv_date = inv.get("invoice_date")
        if isinstance(inv_date, str):
            from datetime import datetime

            try:
                inv_date = datetime.fromisoformat(inv_date).date()
            except ValueError:
                inv_date = None
        elif not isinstance(inv_date, date):
            inv_date = None

        # Amount score
        diff = abs(pay_amount - inv_amount)
        if diff <= Decimal("0.01"):
            amount_score = 1.0
        elif inv_amount > 0 and (diff / inv_amount) <= PAYMENT_AMOUNT_TOLERANCE_PCT:
            amount_score = 0.8
        else:
            amount_score = 0.0

        # Date score
        date_score = 0.0
        if pay_date and inv_date:
            days_diff = abs((pay_date - inv_date).days)
            if days_diff <= 5:
                date_score = 1.0
            elif days_diff <= 15:
                date_score = 0.7
            elif days_diff <= 30:
                date_score = 0.4

        # Reference score
        ref_score = 0.0
        if pay_ref and inv_num and (pay_ref in inv_num or inv_num in pay_ref):
            ref_score = 0.9

        # Weighted composite
        composite = round(amount_score * 0.50 + date_score * 0.30 + ref_score * 0.20, 4)

        if composite > 0:
            results.append(
                {
                    "entity_id": str(inv["id"]),
                    "score": composite,
                    "breakdown": {
                        "amount_score": amount_score,
                        "date_score": date_score,
                        "ref_score": ref_score,
                    },
                }
            )

    return sorted(results, key=lambda x: x["score"], reverse=True)[:5]
