export type DecisionState = 'PASS' | 'MODIFY' | 'BLOCK' | 'ESCALATE';

export type ApprovalStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'NOT_REQUIRED';

export type SignalSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type WorkflowStage =
  | 'DETECT'
  | 'INVESTIGATE'
  | 'PLAN'
  | 'GUARD'
  | 'DECIDE'
  | 'APPROVE'
  | 'ACT'
  | 'LEARN';

export interface PaytmProduct {
  name: string;
  status: string;
  battery_pct?: number;
  placement?: string;
}

export interface MerchantProfile {
  id: string;
  name: string;
  category: string;
  location: string;
  minimum_margin: number;
  daily_budget: number;
  max_discount: number;
  max_campaign_frequency: number;
  autonomy_level: string;
  simulated: boolean;
  simulation_disclaimer?: string;
  paytm_products?: PaytmProduct[];
}

export interface MerchantMetrics {
  merchant_id: string;
  total_revenue_inr: number;
  total_orders: int_or_number;
  avg_basket_size_inr: number;
  evening_orders_current: number;
  evening_orders_baseline: number;
  evening_orders_variance_pct: number;
  repeat_conversion_current: number;
  repeat_conversion_baseline: number;
  target_campaign_customers: number;
  simulated: boolean;
  metrics_breakdown?: Array<{
    name: string;
    value: number;
    unit: string;
    description: string;
  }>;
}

type int_or_number = number;

export interface CustomerSegmentSummary {
  merchant_id: string;
  total_customers: number;
  segment_breakdown: Record<string, number>;
  target_campaign_customers: number;
  simulated: boolean;
}

export interface CampaignItem {
  id: string;
  name: string;
  campaign_type: string;
  discount_amount: number;
  discount_percent: number;
  budget: number;
  target_customer_count: number;
  started_at: string;
  ended_at?: string;
  status: string;
  simulated: boolean;
}

export interface SystemStatus {
  service: string;
  version: string;
  environment: string;
  simulation_mode: boolean;
  simulation_disclaimer: string;
  llm_provider: string;
  llm_is_active: boolean;
  guardrails_enforced: boolean;
  merchant_profile: {
    merchant_id: string;
    business_name: string;
    category: string;
    location: string;
    tier?: string;
    paytm_products?: PaytmProduct[];
    average_daily_gmv_inr?: number;
    average_daily_txns?: number;
  };
}

export interface BusinessSignal {
  signal_id: string;
  merchant_id: string;
  signal_type: string;
  severity: SignalSeverity;
  metric_name: string;
  baseline_value: number;
  observed_value: number;
  variance_percentage?: number;
  change_percentage: number;
  decline_percentage: number;
  description: string;
  status: 'ACTIVE' | 'ACKNOWLEDGED' | 'RESOLVED';
  detected_at: string;
  context_data?: Record<string, unknown>;
}

export interface AuditRecord {
  event_id: string;
  timestamp: string;
  stage: string;
  actor: string;
  action_description: string;
  integrity_hash: string;
}

export interface EvidenceItem {
  evidence_id: string;
  category: string;
  metric: string;
  baseline: string | number;
  current: string | number;
  change_percentage?: number | null;
  observation: string;
  source: string;
}

export interface EvidenceBundle {
  signal_id: string;
  signal_type: string;
  severity: string;
  merchant_id: string;
  primary_metric: string;
  created_at: string;
  evidence_items: EvidenceItem[];
}

export interface Hypothesis {
  hypothesis: string;
  rationale: string;
  supporting_evidence_ids: string[];
  confidence: 'LOW' | 'MEDIUM' | 'HIGH';
}

export interface InvestigationResult {
  investigation_id: string;
  signal_id: string;
  merchant_id: string;
  status: string;
  summary: string;
  findings: string[];
  hypotheses: Hypothesis[];
  confidence: 'LOW' | 'MEDIUM' | 'HIGH';
  evidence_ids: string[];
  limitations: string[];
  created_at: string;
  is_fallback: boolean;
  evidence_bundle?: EvidenceBundle;
}

export interface ActionProposal {
  proposal_id: string;
  action_id: string;
  signal_id: string;
  investigation_id?: string;
  merchant_id: string;
  action_type: string;
  objective?: string;
  target_segment?: string;
  target_customer_count?: number;
  incentive_type?: string;
  incentive_value?: number;
  duration?: string;
  parameters: Record<string, unknown>;
  reason: string;
  confidence: number;
  estimated_cost_inr: number;
  supporting_evidence_ids: string[];
  constraints: Record<string, unknown>;
  status: string; // 'PROPOSED'
  is_fallback: boolean;
  created_at?: string;
}

export interface GuardrailCheck {
  check_id: string;
  check_type: string;
  status: 'PASS' | 'FAIL' | 'WARN' | 'MODIFIED';
  rule: string;
  actual_value?: unknown;
  threshold_value?: unknown;
  message: string;
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
}

export interface GuardrailEvaluation {
  evaluation_id: string;
  action_id: string;
  merchant_id: string;
  overall_status: 'PASS' | 'MODIFY' | 'BLOCK' | 'ESCALATE';
  passed: boolean;
  checks: GuardrailCheck[];
  passed_checks: string[];
  failed_checks: string[];
  warnings: string[];
  modifications: Record<string, unknown>;
  original_values: Record<string, unknown>;
  modified_values: Record<string, unknown>;
  notes: string;
  evaluated_at?: string;
  is_deterministic: boolean;
}

export interface Decision {
  decision_id: string;
  action_id: string;
  evaluation_id: string;
  merchant_id: string;
  decision_state: DecisionState;
  state?: DecisionState;
  reason: string;
  rationale?: string;
  triggered_rules: string[];
  modifications: Record<string, unknown>;
  approval_required: boolean;
  approval_status: ApprovalStatus;
  decided_at: string;
  decided_by: string;
  approved_at?: string;
  rejected_at?: string;
  proposal_hash: string;
  evaluation_hash: string;
  is_deterministic: boolean;
  approved_action?: {
    action_type: string;
    parameters: Record<string, unknown>;
    confidence?: number;
    incentive_value?: number;
    target_customer_count?: number;
    estimated_cost_inr?: number;
    modifications_applied?: Record<string, unknown>;
  } | null;
  is_execution_eligible: boolean;
  escalation_reason?: string;
  requires_human_review: boolean;
}

export type ExecutionState = 'PENDING' | 'EXECUTING' | 'COMPLETED' | 'FAILED' | 'BLOCKED';
export type ExecutionMode = 'SIMULATION';

export interface ExecutionResult {
  execution_id: string;
  decision_id: string;
  action_id: string;
  merchant_id: string;
  action_type: string;
  execution_state: ExecutionState;
  status?: string;
  success: boolean;
  execution_mode: ExecutionMode;
  simulated: boolean;
  approved_action: Record<string, unknown>;
  result: Record<string, unknown>;
  output_details?: Record<string, unknown>;
  error?: string | null;
  executed_at: string;
}

export type OutcomeStatus = 'PENDING' | 'MEASURED' | 'INSUFFICIENT_DATA' | 'FAILED';
export type MeasurementMode = 'SIMULATION';

export interface MetricChangeDetail {
  baseline: number | null;
  post_action: number | null;
  absolute_change: number;
  percentage_change: number | null;
  status: string;
  is_positive?: boolean | null;
  description: string;
}

export interface OutcomeResult {
  outcome_id: string;
  execution_id: string;
  decision_id?: string;
  action_id?: string;
  merchant_id: string;
  baseline_window: {
    start?: string;
    end?: string;
    duration_days?: number;
    label?: string;
  };
  measurement_window: {
    start?: string;
    end?: string;
    duration_days?: number;
    label?: string;
  };
  baseline_metrics: Record<string, number>;
  post_action_metrics: Record<string, number>;
  metric_changes: Record<string, MetricChangeDetail>;
  outcome_status: OutcomeStatus;
  status?: string;
  simulated: boolean;
  measurement_mode: MeasurementMode;
  disclaimer: string;
  measured_at: string;
  metric_name?: string;
  baseline_value?: number;
  observed_value?: number;
  delta_percentage?: number;
  is_positive?: boolean;
}

export type ImpactStatus = 'PENDING' | 'CALCULATED' | 'INSUFFICIENT_DATA' | 'FAILED';
export type ImpactClassification = 'POSITIVE' | 'NEUTRAL' | 'NEGATIVE' | 'INSUFFICIENT_DATA';

export interface BusinessImpact {
  impact_id: string;
  outcome_id: string;
  execution_id: string;
  decision_id?: string;
  action_id?: string;
  merchant_id: string;
  impact_status: ImpactStatus;
  status?: string;

  baseline_revenue: number;
  post_action_revenue: number;
  incremental_revenue: number;

  baseline_orders: number;
  post_action_orders: number;
  incremental_orders: number;
  orders_change: number;

  baseline_evening_orders: number;
  post_action_evening_orders: number;
  evening_orders_change: number;

  campaign_cost: number;
  gross_profit_impact?: number | null;

  roi?: number | null;
  roi_percentage?: number | null;

  cost_per_incremental_order?: number | null;
  revenue_per_campaign_rupee?: number | null;

  impact_classification: ImpactClassification;

  simulated: boolean;
  measurement_mode: MeasurementMode;
  disclaimer: string;
  calculated_at: string;
}

export interface AuditEvent {
  id?: string;
  event_id: string;
  timestamp: string;
  stage: string;
  actor: string;
  event_type: string;
  action_description: string;
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown>;
  decision?: string | null;
  reason?: string | null;
  previous_hash: string;
  integrity_hash: string;
  correlation_id?: string | null;
  merchant_id: string;
  signal_id?: string | null;
  investigation_id?: string | null;
  action_id?: string | null;
  decision_id?: string | null;
  execution_id?: string | null;
  outcome_id?: string | null;
  impact_id?: string | null;
  simulated: boolean;
  description?: string;
  source?: string;
}

export interface FactItem {
  id: string;
  fact_type: string;
  statement: string;
  source: string;
  provenance_record?: Record<string, unknown>;
  is_verified: boolean;
}

export interface HypothesisItem {
  id: string;
  statement: string;
  confidence: number;
  non_causal_caveat: string;
  suggested_action?: string | null;
}

export interface WorkflowAuditVerification {
  correlation_id: string;
  valid: boolean;
  event_count: number;
  verification_mode: string;
  error?: string | null;
  verified_at: string;
}

export interface ExplainabilitySummary {
  explanation_id: string;
  correlation_id: string;
  merchant_id: string;
  signal_summary: Record<string, unknown>;
  facts: FactItem[];
  hypotheses: HypothesisItem[];
  evidence_provenance: Array<Record<string, unknown>>;
  action_summary?: Record<string, unknown> | null;
  guardrail_summary?: Record<string, unknown> | null;
  decision_summary?: Record<string, unknown> | null;
  execution_summary?: Record<string, unknown> | null;
  outcome_summary?: Record<string, unknown> | null;
  business_impact_summary?: Record<string, unknown> | null;
  autonomy_summary?: Record<string, unknown> | null;
  audit_timeline: AuditEvent[];
  audit_verification: WorkflowAuditVerification;
  disclaimer: string;
  limitations: string[];
  generated_at: string;
}

export type AutonomyMode = 'APPROVAL_REQUIRED' | 'AUTO_APPROVE_SAFE' | 'FULL_AUTONOMY';

export type ApprovalSource = 'HUMAN_APPROVED' | 'AUTO_APPROVED' | 'REJECTED' | 'BLOCKED' | 'ESCALATED' | 'PENDING';

export type ActorType = 'MERCHANT' | 'AUTONOMY_POLICY' | 'SYSTEM';

export type AutonomyStatus = 'APPROVAL_REQUIRED' | 'AUTO_APPROVED' | 'HUMAN_APPROVED' | 'BLOCKED' | 'ESCALATED' | 'REJECTED';

export interface AutonomyEvaluation {
  autonomy_evaluation_id: string;
  id?: string;
  correlation_id: string;
  merchant_id: string;
  action_id: string;
  guardrail_evaluation_id: string;
  decision_id: string;
  autonomy_mode: AutonomyMode;
  guardrail_status: DecisionState;
  approval_required: boolean;
  auto_approval_allowed: boolean;
  auto_approval_reason: string;
  approval_source: ApprovalSource;
  actor_type: ActorType;
  blocked: boolean;
  escalated: boolean;
  approved_action?: Record<string, unknown> | null;
  evaluated_risk: number;
  policy_threshold: number;
  policy_version: string;
  passed_checks: string[];
  failed_checks: string[];
  evaluated_at: string;
  simulation_mode: boolean;
}

export interface MerchantAutonomyPolicy {
  merchant_id: string;
  autonomy_mode: AutonomyMode;
  auto_approval_risk_threshold: number;
  full_autonomy_risk_threshold: number;
  auto_approval_max_budget: number;
  auto_approval_max_discount: number;
  require_human_for_modify: boolean;
  require_human_for_escalation: boolean;
  simulated: boolean;
  updated_at?: string | null;
}

// ==========================================
// Phase 13: Command Center AI & Live Experience
// ==========================================

export type AIResponseType =
  | 'SIGNAL_EXPLANATION'
  | 'ACTION_EXPLANATION'
  | 'OUTCOME_SUMMARY'
  | 'BUSINESS_SUMMARY'
  | 'MERCHANT_QA';

export interface AIResponse {
  response_id: string;
  response_type: AIResponseType;
  provider: string;
  answer: string;
  disclaimer: string;
  fact_ids: string[];
  grounding_data: Record<string, unknown>;
  is_cached: boolean;
  generated_at: string;
}

export interface AIProviderStatus {
  active_provider: string;
  available_providers: string[];
  gemini_configured: boolean;
  hf_configured: boolean;
  simulation_mode: boolean;
}

export interface AIMerchantQuestionRequest {
  question: string;
  merchant_id?: string;
  correlation_id?: string;
  action_id?: string;
}

export interface DemoScenarioResult {
  scenario: string;
  signal_id?: string;
  correlation_id?: string;
  action_id?: string;
  original_discount?: number;
  clamped_discount?: number;
  decision_state?: string;
  approval_status?: string;
  autonomy_status?: string;
  approval_source?: string;
  is_execution_eligible?: boolean;
  description: string;
  status?: string;
}

// ==========================================
// Phase 14: Demo Hardening & Reliability
// ==========================================

export interface SystemHealthResponse {
  backend: string;
  database: string;
  ai: string;
  ai_status: string;
  guardrails: string;
  audit: string;
  execution: string;
  autonomy_mode: string;
  simulation_mode: boolean;
  disclaimer: string;
  timestamp: string;
}

export interface DemoResetResponse {
  status: string;
  message: string;
  merchant_id: string;
  autonomy_mode: string;
  active_scenario: string;
  active_signal_id: string;
  audit_preserved: boolean;
  audit_events_count: number;
  ai_provider: string;
  simulated: boolean;
  seed_summary: Record<string, unknown>;
  timestamp: string;
}

