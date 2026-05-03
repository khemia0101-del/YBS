export enum ExceptionStatus {
  Pending = 'pending',
  Approved = 'approved',
  Rejected = 'rejected',
  NeedsReview = 'needs_review',
  AutoApproved = 'auto_approved',
}

export enum ContractStatus {
  Active = 'active',
  Expired = 'expired',
  Terminated = 'terminated',
  Pending = 'pending',
  Suspended = 'suspended',
}

export enum InvoiceStatus {
  Draft = 'draft',
  Open = 'open',
  Partial = 'partial',
  Paid = 'paid',
  Overdue = 'overdue',
  Void = 'void',
  Disputed = 'disputed',
}

export enum AgentTaskStatus {
  Queued = 'queued',
  Running = 'running',
  AwaitingApproval = 'awaiting_approval',
  Approved = 'approved',
  Completed = 'completed',
  Failed = 'failed',
}

export enum RiskLevel {
  Low = 'low',
  Medium = 'medium',
  High = 'high',
  Critical = 'critical',
}

export enum DecisionLabel {
  Auto = 'AUTO',
  ApprovalRequired = 'APPROVAL_REQUIRED',
  Blocked = 'BLOCKED',
}

export enum UserRole {
  Admin = 'admin',
  Analyst = 'analyst',
  Operator = 'operator',
  Viewer = 'viewer',
}
