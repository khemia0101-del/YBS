"""
Import all models here so that Alembic (and other tools) can detect them
via Base.metadata without explicit imports scattered everywhere.
"""
from __future__ import annotations

# Base must be first
from app.models.base import Base, TimestampMixin, UUIDMixin

# Core domain models (no FK deps on other app models)
from app.models.users import User
from app.models.audit import AuditLog

# Core operational models
from app.models.core import (
    Company,
    ComplianceDocument,
    Contract,
    Customer,
    Site,
    Subcontractor,
    Supervisor,
    Tenant,
)

# Adaptive business profile
from app.models.business import BusinessProfile, MetricDefinition, MetricSnapshot

# AI interview
from app.models.interview import InterviewInsight, InterviewMessage, InterviewSession

# Automation roadmap
from app.models.automation import AutomationItem

# Raw/staged ingestion
from app.models.raw import RawRecord, StagedRecord

# Transactions
from app.models.transactions import Invoice, LaborShift, Payment

# Financial analytics
from app.models.financial import (
    CashForecastRun,
    CashForecastWeek,
    Decision,
    DSOSnapshot,
    LaborBurdenAssumption,
    ManualOverride,
    PredictionTracking,
    ProfitabilityRun,
    ProfitabilityRunLine,
    StressTestRun,
)

# ESOP
from app.models.esop import ESOPAdjustment, QoERun, ValuationEvidenceFile

# Agent
from app.models.agent import (
    AgentActionLog,
    AgentMemoryExport,
    AgentTask,
    ApprovalRequest,
    CommunicationTemplate,
    RuleChangeProposal,
)

# Sync / integrations
from app.models.sync import IntegrationCredential, SyncLog

__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDMixin",
    # users
    "User",
    "AuditLog",
    # core
    "Tenant",
    "Company",
    "Customer",
    "Site",
    "Contract",
    "Supervisor",
    "Subcontractor",
    "ComplianceDocument",
    # business profile
    "BusinessProfile",
    "MetricDefinition",
    "MetricSnapshot",
    # interview
    "InterviewSession",
    "InterviewMessage",
    "InterviewInsight",
    # automation
    "AutomationItem",
    # raw
    "RawRecord",
    "StagedRecord",
    # transactions
    "Invoice",
    "Payment",
    "LaborShift",
    # financial
    "LaborBurdenAssumption",
    "ProfitabilityRun",
    "ProfitabilityRunLine",
    "DSOSnapshot",
    "CashForecastRun",
    "CashForecastWeek",
    "StressTestRun",
    "Decision",
    "ManualOverride",
    "PredictionTracking",
    # esop
    "QoERun",
    "ESOPAdjustment",
    "ValuationEvidenceFile",
    # agent
    "AgentTask",
    "AgentActionLog",
    "ApprovalRequest",
    "CommunicationTemplate",
    "RuleChangeProposal",
    "AgentMemoryExport",
    # sync
    "SyncLog",
    "IntegrationCredential",
]
