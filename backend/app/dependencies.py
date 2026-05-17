"""
Centralised FastAPI dependency re-exports so routers can do:
    from app.dependencies import get_db, require_admin
"""
from __future__ import annotations

from app.database import get_db  # noqa: F401
from app.security.auth import get_current_active_user, get_current_user  # noqa: F401
from app.security.rbac import require_role
from app.security.tenant import (  # noqa: F401
    assert_company_in_tenant,
    get_tenant_id,
    resolve_scope_company_ids,
    tenant_company_ids,
)

# Named shortcuts used throughout routers
require_admin = require_role("admin")
require_analyst = require_role("analyst", "admin")
require_operator = require_role("operator", "analyst", "admin")

__all__ = [
    "get_db",
    "get_current_user",
    "get_current_active_user",
    "require_role",
    "require_admin",
    "require_analyst",
    "require_operator",
    "get_tenant_id",
    "tenant_company_ids",
    "assert_company_in_tenant",
    "resolve_scope_company_ids",
]
