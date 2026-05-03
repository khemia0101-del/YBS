import {
  ExceptionStatus,
  ContractStatus,
  InvoiceStatus,
  AgentTaskStatus,
  RiskLevel,
  DecisionLabel,
  UserRole,
} from './enums'

export interface User {
  id: string
  email: string
  full_name: string
  role: UserRole
  company_id: string
  is_active: boolean
  created_at: string
  last_login: string | null
}

export interface Company {
  id: string
  name: string
  legal_name: string
  ein: string | null
  address: string | null
  city: string | null
  state: string | null
  zip: string | null
  created_at: string
}

export interface Customer {
  id: string
  company_id: string
  external_id: string | null
  name: string
  contact_email: string | null
  contact_phone: string | null
  billing_address: string | null
  is_active: boolean
  created_at: string
}

export interface Site {
  id: string
  company_id: string
  customer_id: string
  name: string
  address: string
  city: string
  state: string
  zip: string
  is_active: boolean
  created_at: string
}

export interface Contract {
  id: string
  company_id: string
  customer_id: string
  site_id: string | null
  contract_number: string
  status: ContractStatus
  start_date: string
  end_date: string | null
  monthly_value: number
  annual_value: number
  service_type: string
  auto_renew: boolean
  created_at: string
  updated_at: string
  customer?: Customer
  site?: Site
}

export interface Invoice {
  id: string
  company_id: string
  customer_id: string
  contract_id: string | null
  invoice_number: string
  status: InvoiceStatus
  issue_date: string
  due_date: string
  amount: number
  amount_paid: number
  amount_due: number
  tax_amount: number
  notes: string | null
  created_at: string
  updated_at: string
  customer?: Customer
}

export interface Payment {
  id: string
  company_id: string
  customer_id: string
  invoice_id: string | null
  amount: number
  payment_date: string
  method: string
  reference: string | null
  notes: string | null
  created_at: string
}

export interface LaborShift {
  id: string
  company_id: string
  site_id: string | null
  employee_id: string
  employee_name: string
  shift_date: string
  hours_worked: number
  pay_rate: number
  bill_rate: number
  total_cost: number
  total_billed: number
  job_type: string
  source_system: string
  created_at: string
}

export interface RawRecord {
  id: string
  company_id: string
  source_system: string
  record_type: string
  external_id: string | null
  raw_payload: Record<string, unknown>
  extracted_at: string
  processing_status: string
}

export interface MatchCandidate {
  entity_id: string
  entity_type: string
  entity_name: string
  confidence: number
  match_fields: Record<string, unknown>
}

export interface StagedException {
  id: string
  company_id: string
  raw_record_id: string
  record_type: string
  source_system: string
  extracted_data: Record<string, unknown>
  confidence_score: number
  confidence_breakdown: Record<string, number>
  exception_reason: string
  status: ExceptionStatus
  financial_impact: number | null
  match_candidates: MatchCandidate[]
  assigned_to: string | null
  review_notes: string | null
  reviewed_by: string | null
  reviewed_at: string | null
  evidence_id: string | null
  created_at: string
  updated_at: string
  age_days: number
}

export interface ProfitabilityRunLine {
  id: string
  run_id: string
  contract_id: string
  customer_id: string
  customer_name: string
  contract_number: string
  period_start: string
  period_end: string
  revenue: number
  labor_cost: number
  gross_profit: number
  gross_margin: number
  confidence_score: number
  confidence_breakdown: Record<string, number>
  flags: string[]
}

export interface ProfitabilityRun {
  id: string
  company_id: string
  period_start: string
  period_end: string
  total_revenue: number
  total_labor_cost: number
  gross_profit: number
  gross_margin: number
  run_at: string
  status: string
  lines: ProfitabilityRunLine[]
}

export interface DSOSnapshot {
  id: string
  company_id: string
  snapshot_date: string
  dso_days: number
  ar_balance: number
  revenue_trailing_90: number
  notes: string | null
  created_at: string
}

export interface CashForecastWeek {
  id: string
  run_id: string
  week_number: number
  week_start: string
  week_end: string
  beginning_cash: number
  inflows: number
  outflows: number
  net_cash: number
  ending_cash: number
  payroll_amount: number
  payroll_covered: boolean
  notes: string | null
}

export interface CashForecastRun {
  id: string
  company_id: string
  run_date: string
  beginning_cash: number
  weeks: CashForecastWeek[]
  payroll_covered_through: string | null
  min_ending_cash: number
  status: string
  created_at: string
}

export interface StressTestRun {
  id: string
  company_id: string
  forecast_run_id: string
  scenario_name: string
  revenue_reduction_pct: number
  ar_delay_days: number
  payroll_increase_pct: number
  result_min_cash: number
  result_payroll_covered_through: string | null
  created_at: string
  weeks: CashForecastWeek[]
}

export interface Decision {
  id: string
  company_id: string
  decision_type: string
  label: DecisionLabel
  description: string
  rationale: string
  inputs: Record<string, unknown>
  outputs: Record<string, unknown>
  risk_level: RiskLevel
  confidence_score: number
  requires_approval: boolean
  approved_by: string | null
  approved_at: string | null
  rejected_by: string | null
  rejected_at: string | null
  rejection_reason: string | null
  status: string
  created_at: string
  updated_at: string
}

export interface QoERun {
  id: string
  company_id: string
  period_start: string
  period_end: string
  normalized_ebitda: number
  book_ebitda: number
  total_addbacks: number
  total_deductions: number
  run_at: string
  status: string
  notes: string | null
  adjustments: ESOPAdjustment[]
}

export interface ESOPAdjustment {
  id: string
  run_id: string
  category: string
  description: string
  amount: number
  is_addback: boolean
  evidence_id: string | null
  approval_status: string
  approved_by: string | null
  approved_at: string | null
  notes: string | null
  created_at: string
}

export interface AgentTask {
  id: string
  company_id: string
  task_type: string
  status: AgentTaskStatus
  priority: number
  description: string
  inputs: Record<string, unknown>
  outputs: Record<string, unknown> | null
  error_message: string | null
  created_by: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
  requires_approval: boolean
}

export interface AgentActionLog {
  id: string
  task_id: string
  action_type: string
  description: string
  inputs: Record<string, unknown>
  outputs: Record<string, unknown> | null
  success: boolean
  error_message: string | null
  created_at: string
}

export interface ApprovalRequest {
  id: string
  company_id: string
  task_id: string | null
  exception_id: string | null
  decision_id: string | null
  requested_by: string
  requested_at: string
  risk_level: RiskLevel
  description: string
  context: Record<string, unknown>
  status: string
  reviewed_by: string | null
  reviewed_at: string | null
  review_notes: string | null
  task?: AgentTask
}

export interface ExceptionStats {
  total: number
  pending: number
  approved: number
  rejected: number
  needs_review: number
  auto_approved: number
  pending_financial_impact: number
}

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'down'
  last_sync: string | null
  pending_exceptions: number
  pending_approvals: number
  active_agents: number
  last_profitability_run: string | null
  last_cash_forecast: string | null
}
