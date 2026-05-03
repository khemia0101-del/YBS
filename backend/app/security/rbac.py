from __future__ import annotations

from fastapi import Depends, HTTPException, status

from app.models.users import User
from app.security.auth import get_current_active_user

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {"*"},
    "analyst": {
        "read:*",
        "write:staging",
        "write:esop_adjustments",
        "approve:medium",
        "approve:high",
    },
    "operator": {
        "read:*",
        "write:staging",
        "approve:low",
        "approve:medium",
    },
    "viewer": {"read:*"},
    "agent": {
        "read:raw_records",
        "read:staged_records",
        "read:customers",
        "read:contracts",
        "read:invoices",
        "read:payments",
        "read:labor_shifts",
        "write:raw_records",
        "write:staged_records",
        "write:agent_tasks",
        "write:agent_action_logs",
        "write:approval_requests",
        "write:rule_change_proposals",
    },
}

# Tables that agents are NEVER allowed to write to directly.
AGENT_WRITE_PROHIBITED: set[str] = {
    "customers",
    "contracts",
    "sites",
    "invoices",
    "payments",
    "labor_shifts",
    "subcontractors",
    "supervisors",
    "profitability_runs",
    "profitability_run_lines",
    "dso_snapshots",
    "cash_forecast_runs",
    "cash_forecast_weeks",
    "qoe_runs",
    "esop_adjustments",
    "decisions",
}


class AgentGuardrailViolation(Exception):
    """Raised when an agent attempts a prohibited write."""


def require_role(*roles: str):
    """
    FastAPI dependency factory.

    Usage::

        @router.get("/admin-only")
        async def endpoint(user = Depends(require_role("admin"))):
            ...

        @router.get("/analyst-or-admin")
        async def endpoint(user = Depends(require_role("analyst", "admin"))):
            ...
    """

    async def _check(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {' or '.join(roles)}. Got: {current_user.role}",
            )
        return current_user

    return _check


def has_permission(role: str, permission: str) -> bool:
    """
    Check whether a given role has the specified permission string.
    Admin has everything (wildcard "*"). Others use prefix matching on read:* / write:*.
    """
    perms = ROLE_PERMISSIONS.get(role, set())
    if "*" in perms:
        return True
    if permission in perms:
        return True
    # Prefix wildcard: "read:*" grants any "read:…"
    prefix = permission.split(":")[0] + ":*"
    return prefix in perms


def validate_agent_writes(actor_type: str, tables_written: list[str]) -> None:
    """
    Raise AgentGuardrailViolation if an agent is attempting to write
    to a prohibited table.
    """
    if actor_type == "agent":
        violations = set(tables_written) & AGENT_WRITE_PROHIBITED
        if violations:
            raise AgentGuardrailViolation(
                f"Agent attempted prohibited write to: {sorted(violations)}"
            )
