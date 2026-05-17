"""Renders a Quality-of-Earnings report as Markdown from engine + valuation output."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.services.qoe.engine import FinancialPeriod, QoEResult
from app.services.qoe.valuation import ValuationResult


def _money(value) -> str:
    d = value if isinstance(value, Decimal) else Decimal(str(value))
    return f"${d:,.2f}"


def _pct(value) -> str:
    d = value if isinstance(value, Decimal) else Decimal(str(value))
    return f"{d:.1f}%"


def render_markdown(
    company_name: str,
    qoe: QoEResult,
    valuation: ValuationResult,
    periods: list[FinancialPeriod],
    context: dict | None = None,
    observations: list[str] | None = None,
    diligence_flags: list[str] | None = None,
) -> str:
    primary = qoe.primary
    lines: list[str] = []
    a = lines.append

    a(f"# Quality of Earnings — {company_name}")
    a("")
    a(f"*Baseline QoE analysis generated {date.today().isoformat()}. "
      "Prepared from the seller's cash-basis P&Ls. This is an internal baseline, "
      "not a formal appraisal or audit.*")
    a("")

    # ── Executive summary ─────────────────────────────────────────────────
    a("## Executive summary")
    a("")
    a(f"- **Valuation basis period:** {primary.label}")
    a(f"- **Revenue:** {_money(primary.revenue)}")
    a(f"- **Gross margin:** {_pct(primary.gross_margin_pct)}")
    a(f"- **Reported EBITDA:** {_money(primary.reported_ebitda)}")
    a(f"- **Adjusted EBITDA:** {_money(primary.adjusted_ebitda)}")
    a(f"- **Seller's Discretionary Earnings (SDE):** {_money(primary.sde)}")
    a(f"- **Baseline valuation range:** {_money(valuation.low_value)} – "
      f"{_money(valuation.high_value)} "
      f"(midpoint **{_money(valuation.mid_value)}** at {valuation.mid_multiple}x SDE)")
    if qoe.revenue_cagr_pct is not None:
        a(f"- **Revenue CAGR (full years):** {_pct(qoe.revenue_cagr_pct)}")
    a("")

    # ── Business overview ─────────────────────────────────────────────────
    if context:
        a("## Business overview")
        a("")
        for key, value in context.items():
            a(f"- **{key.replace('_', ' ').title()}:** {value}")
        a("")

    # ── Revenue & margin trend ────────────────────────────────────────────
    a("## Revenue & margin trend")
    a("")
    a("| Period | Months | Revenue | Gross profit | Gross margin | Operating income |")
    a("|---|---|---|---|---|---|")
    for r in qoe.periods:
        a(f"| {r.label} | {r.months} | {_money(r.revenue)} | {_money(r.gross_profit)} "
          f"| {_pct(r.gross_margin_pct)} | {_money(r.operating_income)} |")
    a("")
    for note in qoe.notes:
        a(f"> {note}")
    if qoe.notes:
        a("")

    # ── EBITDA -> SDE bridge ──────────────────────────────────────────────
    a(f"## EBITDA → SDE bridge — {primary.label}")
    a("")
    a("| Line | Amount |")
    a("|---|---|")
    a(f"| Operating income | {_money(primary.operating_income)} |")
    a(f"| Reported EBITDA | {_money(primary.reported_ebitda)} |")
    a(f"| EBITDA normalizing addbacks | {_money(primary.ebitda_addbacks)} |")
    a(f"| **Adjusted EBITDA** | **{_money(primary.adjusted_ebitda)}** |")
    a(f"| Owner / discretionary / financing addbacks | {_money(primary.sde_addbacks)} |")
    a(f"| **Seller's Discretionary Earnings (SDE)** | **{_money(primary.sde)}** |")
    a(f"| SDE margin | {_pct(primary.sde_margin_pct)} |")
    a("")

    # ── Addback schedule ──────────────────────────────────────────────────
    a("## Addback schedule")
    a("")
    a("| Period | Addback | Amount | Applies to | Category | Confidence | Rationale |")
    a("|---|---|---|---|---|---|---|")
    for p in periods:
        for ab in p.addbacks:
            a(f"| {p.label} | {ab.label} | {_money(ab.amount)} | {ab.applies_to.upper()} "
              f"| {ab.category} | {ab.confidence} | {ab.rationale} |")
    a("")

    # ── Valuation ─────────────────────────────────────────────────────────
    a("## Baseline valuation")
    a("")
    a(f"Valued on **{primary.label} SDE of {_money(valuation.base_value)}**.")
    a("")
    a("| Scenario | Multiple | Enterprise value |")
    a("|---|---|---|")
    a(f"| Low | {valuation.low_multiple}x | {_money(valuation.low_value)} |")
    a(f"| Midpoint | {valuation.mid_multiple}x | {_money(valuation.mid_value)} |")
    a(f"| High | {valuation.high_multiple}x | {_money(valuation.high_value)} |")
    a("")
    a("**Sensitivity:**")
    a("")
    a("| SDE multiple | Value |")
    a("|---|---|")
    for row in valuation.sensitivity:
        a(f"| {row['multiple']}x | {_money(row['value'])} |")
    a("")
    if valuation.rationale:
        a("**Multiple rationale:**")
        a("")
        for r in valuation.rationale:
            a(f"- {r}")
        a("")

    # ── Observations ──────────────────────────────────────────────────────
    if observations:
        a("## Earnings-quality observations")
        a("")
        for o in observations:
            a(f"- {o}")
        a("")

    # ── Diligence flags ───────────────────────────────────────────────────
    if diligence_flags:
        a("## Open diligence items")
        a("")
        for f in diligence_flags:
            a(f"- [ ] {f}")
        a("")

    return "\n".join(lines)
