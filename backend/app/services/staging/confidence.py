from __future__ import annotations

# Source reliability weights — how much we trust data from each system
SOURCE_RELIABILITY: dict[str, float] = {
    "quickbooks": 0.95,
    "bank_csv": 0.85,
    "payroll": 0.85,
    "swept": 0.80,
    "email": 0.65,
    "manual": 0.90,
}

# Required fields per record type for completeness scoring
REQUIRED_FIELDS: dict[str, list[str]] = {
    "customer": ["name", "customer_type"],
    "contract": ["customer_id", "start_date", "monthly_value", "contract_type"],
    "site": ["customer_id", "site_name"],
    "invoice": ["customer_id", "invoice_date", "amount"],
    "payment": ["customer_id", "payment_date", "amount"],
    "labor_shift": ["employee_id", "shift_date", "hours_worked", "worker_type"],
    "subcontractor": ["name"],
}

# High-confidence bonus fields — having these adds confidence
BONUS_FIELDS: dict[str, list[str]] = {
    "invoice": ["invoice_number", "due_date", "contract_id"],
    "payment": ["reference_number", "invoice_id", "payment_method"],
    "labor_shift": ["clock_in", "clock_out", "hourly_rate", "contract_id"],
    "customer": ["qb_customer_id", "industry"],
    "contract": ["contract_number", "end_date", "service_frequency"],
    "site": ["address", "square_footage"],
    "subcontractor": ["contact_info", "w9_on_file", "payment_terms"],
}


def score_extraction(
    record_type: str,
    extracted_data: dict,
    match_suggestions: list[dict],
    source_system: str,
) -> dict:
    """
    Compute a confidence score for an extracted record.

    Returns a dict with:
    - overall: float (0-1)
    - field_scores: {field: bool}
    - reasons: list[str]

    Scoring components:
    1. Source reliability (30% weight)
    2. Field completeness — required fields present and non-null (40% weight)
    3. Bonus fields present (10% weight)
    4. Match corroboration — top match score from suggestions (20% weight)
    """
    reasons: list[str] = []
    field_scores: dict[str, bool] = {}

    # 1. Source reliability
    source_weight = SOURCE_RELIABILITY.get(source_system, 0.75)
    reasons.append(f"source={source_system} reliability={source_weight:.2f}")

    # 2. Completeness
    required = REQUIRED_FIELDS.get(record_type, [])
    if not required:
        completeness = 1.0
        reasons.append("no required fields defined for record_type")
    else:
        present_count = 0
        for field in required:
            val = extracted_data.get(field)
            is_present = val is not None and val != "" and val != []
            field_scores[field] = is_present
            if is_present:
                present_count += 1
            else:
                reasons.append(f"missing_required_field={field}")
        completeness = present_count / len(required)
        reasons.append(f"completeness={completeness:.2f} ({present_count}/{len(required)})")

    # 3. Bonus fields
    bonus = BONUS_FIELDS.get(record_type, [])
    if bonus:
        bonus_present = sum(
            1
            for f in bonus
            if extracted_data.get(f) is not None and extracted_data.get(f) != ""
        )
        bonus_score = bonus_present / len(bonus)
        reasons.append(f"bonus_fields={bonus_score:.2f} ({bonus_present}/{len(bonus)})")
    else:
        bonus_score = 1.0

    # 4. Match corroboration
    if match_suggestions:
        top_match_score = max((m.get("score", 0) for m in match_suggestions), default=0.0)
        reasons.append(f"top_match_score={top_match_score:.2f}")
    else:
        top_match_score = 0.5  # Neutral — no suggestions, not necessarily bad
        reasons.append("no_match_suggestions")

    # Weighted composite
    overall = (
        source_weight * 0.30
        + completeness * 0.40
        + bonus_score * 0.10
        + top_match_score * 0.20
    )
    overall = round(min(1.0, max(0.0, overall)), 4)

    return {
        "overall": overall,
        "field_scores": field_scores,
        "reasons": reasons,
        "source_reliability": source_weight,
        "completeness": completeness,
        "bonus_score": bonus_score,
        "match_corroboration": top_match_score,
    }
