from __future__ import annotations

from pydantic import BaseModel


class AddbackInput(BaseModel):
    label: str
    amount: float
    applies_to: str = "sde"  # "ebitda" | "sde"
    category: str = "discretionary"
    rationale: str = ""
    confidence: str = "medium"


class PeriodInput(BaseModel):
    label: str
    revenue: float
    cogs: float = 0
    operating_expenses: float = 0
    interest: float = 0
    depreciation: float = 0
    amortization: float = 0
    net_income: float | None = None
    months: int = 12
    notes: str = ""
    addbacks: list[AddbackInput] = []


class QoEAnalyzeRequest(BaseModel):
    periods: list[PeriodInput]
    primary_label: str | None = None
    low_multiple: float = 2.0
    mid_multiple: float = 2.75
    high_multiple: float = 3.5
    valuation_rationale: list[str] = []
    persist: bool = True
