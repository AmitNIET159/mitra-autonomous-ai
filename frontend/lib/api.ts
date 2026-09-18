import {
  CampaignItem,
  CustomerSegmentSummary,
  MerchantMetrics,
  MerchantProfile,
  SystemStatus,
} from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetchHealth(): Promise<{ status: string; service: string }> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/health`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Backend /api/health unavailable, falling back:', err);
    return { status: 'offline', service: 'MITRA' };
  }
}

export async function fetchSystemStatus(): Promise<SystemStatus> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/system/status`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Backend /api/system/status unavailable, falling back to digital twin:', err);
    return {
      service: 'MITRA',
      version: '0.1.0',
      environment: 'development',
      simulation_mode: true,
      simulation_disclaimer:
        'PROTOTYPE SIMULATION NOTICE: All merchant metrics, signals, and actions are synthetic simulations in digital-twin sandbox.',
      llm_provider: 'Deterministic Fallback Client (Local)',
      llm_is_active: false,
      guardrails_enforced: true,
      merchant_profile: {
        merchant_id: 'MID-DEMO-98234',
        business_name: 'Sharma Kirana & General Store',
        category: 'Retail / Grocery',
        location: 'Delhi NCR',
        tier: 'Tier-1 Metro Retail',
        paytm_products: [
          { name: 'Paytm Soundbox 4.0', status: 'ONLINE', battery_pct: 89 },
          { name: 'Paytm All-In-One QR', status: 'ACTIVE', placement: 'Front Counter' },
          { name: 'Paytm Card Machine', status: 'STANDBY' },
        ],
        average_daily_gmv_inr: 34417.0,
        average_daily_txns: 92,
      },
    };
  }
}

export async function fetchMerchant(): Promise<MerchantProfile> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/merchant`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return {
      ...data,
      paytm_products: [
        { name: 'Paytm Soundbox 4.0', status: 'ONLINE', battery_pct: 89 },
        { name: 'Paytm All-In-One QR', status: 'ACTIVE', placement: 'Front Counter' },
        { name: 'Paytm Card Machine', status: 'STANDBY' },
      ],
    };
  } catch (err) {
    console.warn('Backend /api/merchant unavailable, using seeded fallback:', err);
    return {
      id: 'MID-DEMO-98234',
      name: 'Sharma Kirana & General Store',
      category: 'Retail / Grocery',
      location: 'Delhi NCR',
      minimum_margin: 0.10,
      daily_budget: 12000.0,
      max_discount: 100.0,
      max_campaign_frequency: 3,
      autonomy_level: 'APPROVAL_REQUIRED',
      simulated: true,
      paytm_products: [
        { name: 'Paytm Soundbox 4.0', status: 'ONLINE', battery_pct: 89 },
        { name: 'Paytm All-In-One QR', status: 'ACTIVE', placement: 'Front Counter' },
        { name: 'Paytm Card Machine', status: 'STANDBY' },
      ],
    };
  }
}

export async function fetchMerchantMetrics(): Promise<MerchantMetrics> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/merchant/metrics`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Backend /api/merchant/metrics unavailable, using seeded fallback:', err);
    return {
      merchant_id: 'MID-DEMO-98234',
      total_revenue_inr: 481849.82,
      total_orders: 1284,
      avg_basket_size_inr: 375.27,
      evening_orders_current: 291,
      evening_orders_baseline: 410,
      evening_orders_variance_pct: -29.02,
      repeat_conversion_current: 0.148,
      repeat_conversion_baseline: 0.182,
      target_campaign_customers: 486,
      simulated: true,
    };
  }
}

export async function fetchCustomerSummary(): Promise<CustomerSegmentSummary> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/merchant/customers/summary`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Backend /api/merchant/customers/summary unavailable, using fallback:', err);
    return {
      merchant_id: 'MID-DEMO-98234',
      total_customers: 520,
      segment_breakdown: { repeat_customer: 216, regular: 240, inactive: 40, new_customer: 24 },
      target_campaign_customers: 486,
      simulated: true,
    };
  }
}

export async function fetchCampaigns(): Promise<CampaignItem[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/merchant/campaigns`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Backend /api/merchant/campaigns unavailable, using fallback:', err);
    return [
      {
        id: 'CAMP-2026-EVN-01',
        name: 'Evening Rush Cashback (Expired)',
        campaign_type: 'CASHBACK_OFFER',
        discount_amount: 50.0,
        discount_percent: 10.0,
        budget: 6000.0,
        target_customer_count: 486,
        started_at: '2026-08-31T21:00:00Z',
        ended_at: '2026-09-14T21:00:00Z',
        status: 'EXPIRED',
        simulated: true,
      },
    ];
  }
}

export async function resetSimulation(): Promise<{ status: string; message: string }> {
  const res = await fetch(`${API_BASE_URL}/api/simulation/reset`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export interface DetectSignalsResponse {
  merchant_id: string;
  signals_detected: import('@/types').BusinessSignal[];
  count: number;
  simulated: boolean;
}

export async function triggerSignalDetection(
  merchantId: string = 'MID-DEMO-98234'
): Promise<DetectSignalsResponse> {
  const res = await fetch(`${API_BASE_URL}/api/signals/detect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ merchant_id: merchantId }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to trigger signal detection`);
  return await res.json();
}

export async function fetchSignals(
  merchantId: string = 'MID-DEMO-98234',
  status?: string
): Promise<import('@/types').BusinessSignal[]> {
  try {
    const url = new URL(`${API_BASE_URL}/api/signals`);
    url.searchParams.set('merchant_id', merchantId);
    if (status) url.searchParams.set('status', status);

    const res = await fetch(url.toString(), { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Backend /api/signals unavailable, using seeded fallback:', err);
    return [
      {
        signal_id: 'SIG-EVN-DECLINE-01',
        merchant_id: merchantId,
        signal_type: 'EVENING_ORDER_DECLINE',
        severity: 'HIGH',
        metric_name: 'evening_orders',
        baseline_value: 410.0,
        observed_value: 291.0,
        change_percentage: -29.02,
        decline_percentage: 29.02,
        variance_percentage: -29.02,
        description:
          'Evening orders (5:00 PM - 8:59 PM) fell from 410.0 baseline to 291.0 in the recent 4-day window.',
        status: 'ACTIVE',
        detected_at: new Date().toISOString(),
        context_data: {
          detector: 'EveningOrderDeclineDetector',
          metric: 'evening_orders',
          hours: '17:00-20:59',
          baseline_orders: 410,
          observed_orders: 291,
          baseline_window: '2026-09-01 to 2026-09-10 (10 days)',
          observed_window: '2026-09-11 to 2026-09-14 (4 days)',
          decline_pct: 29.02,
        },
      },
    ];
  }
}

export async function triggerInvestigation(
  signalId: string,
  forceFallback: boolean = false
): Promise<import('@/types').InvestigationResult> {
  const url = new URL(`${API_BASE_URL}/api/investigations/${signalId}`);
  if (forceFallback) {
    url.searchParams.set('force_fallback', 'true');
  }
  const res = await fetch(url.toString(), {
    method: 'POST',
    cache: 'no-store',
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to trigger investigation`);
  return await res.json();
}

export async function fetchInvestigationBySignal(
  signalId: string
): Promise<import('@/types').InvestigationResult | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/signals/${signalId}/investigation`, {
      cache: 'no-store',
    });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Backend investigation query failed:', err);
    return null;
  }
}

export async function triggerActionPlanning(
  investigationId: string,
  forceFallback: boolean = false
): Promise<import('@/types').ActionProposal> {
  const url = new URL(`${API_BASE_URL}/api/actions/plan/${investigationId}`);
  if (forceFallback) {
    url.searchParams.set('force_fallback', 'true');
  }
  const res = await fetch(url.toString(), {
    method: 'POST',
    cache: 'no-store',
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to trigger action planning`);
  return await res.json();
}

export async function fetchActionByInvestigation(
  investigationId: string
): Promise<import('@/types').ActionProposal | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/investigations/${investigationId}/action`, {
      cache: 'no-store',
    });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Backend action query failed:', err);
    return null;
  }
}

export async function triggerGuardrailEvaluation(
  actionId: string,
  merchantId?: string
): Promise<import('@/types').GuardrailEvaluation> {
  const url = new URL(`${API_BASE_URL}/api/guardrails/evaluate/${actionId}`);
  if (merchantId) {
    url.searchParams.set('merchant_id', merchantId);
  }
  const res = await fetch(url.toString(), {
    method: 'POST',
    cache: 'no-store',
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to evaluate guardrails`);
  return await res.json();
}

export async function fetchGuardrailByAction(
  actionId: string
): Promise<import('@/types').GuardrailEvaluation | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/actions/${actionId}/guardrails`, {
      cache: 'no-store',
    });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Backend guardrail query failed:', err);
    return null;
  }
}

export async function triggerDecisionCreation(
  actionId: string,
  merchantId?: string
): Promise<import('@/types').Decision> {
  const url = new URL(`${API_BASE_URL}/api/decisions/create/${actionId}`);
  if (merchantId) {
    url.searchParams.set('merchant_id', merchantId);
  }
  const res = await fetch(url.toString(), {
    method: 'POST',
    cache: 'no-store',
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `HTTP ${res.status}: Failed to create decision`);
  }
  return await res.json();
}

export async function fetchDecisionByAction(
  actionId: string
): Promise<import('@/types').Decision | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/actions/${actionId}/decision`, {
      cache: 'no-store',
    });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Backend decision query failed:', err);
    return null;
  }
}
export async function approveDecision(
  decisionId: string,
  merchantId: string = 'MID-DEMO-98234',
  approver: string = 'Sharma Kirana Store Owner'
): Promise<import('@/types').Decision> {
  const res = await fetch(`${API_BASE_URL}/api/decisions/${decisionId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ merchant_id: merchantId, approver }),
    cache: 'no-store',
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `HTTP ${res.status}: Failed to approve decision`);
  }
  return await res.json();
}

export async function rejectDecision(
  decisionId: string,
  merchantId: string = 'MID-DEMO-98234',
  reason: string = 'Merchant rejected proposed action parameters',
  approver: string = 'Sharma Kirana Store Owner'
): Promise<import('@/types').Decision> {
  const res = await fetch(`${API_BASE_URL}/api/decisions/${decisionId}/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ merchant_id: merchantId, reason, approver }),
    cache: 'no-store',
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `HTTP ${res.status}: Failed to reject decision`);
  }
  return await res.json();
}

export async function executeSimulation(
  decisionId: string,
  merchantId: string = 'MID-DEMO-98234'
): Promise<import('@/types').ExecutionResult> {
  const res = await fetch(`${API_BASE_URL}/api/executions/execute/${decisionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ merchant_id: merchantId }),
    cache: 'no-store',
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `HTTP ${res.status}: Simulation execution failed`);
  }
  return await res.json();
}

export async function fetchExecutionByDecision(
  decisionId: string
): Promise<import('@/types').ExecutionResult | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/decisions/${decisionId}/execution`, {
      cache: 'no-store',
    });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Backend execution query failed:', err);
    return null;
  }
}

export async function fetchExecutionsHistory(
  merchantId: string = 'MID-DEMO-98234'
): Promise<import('@/types').ExecutionResult[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/executions?merchant_id=${merchantId}`, {
      cache: 'no-store',
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Backend executions history query failed:', err);
    return [];
  }
}

export async function measureOutcome(
  executionId: string,
  merchantId: string = 'MID-DEMO-98234',
  measurementWindow?: Record<string, unknown>
): Promise<import('@/types').OutcomeResult> {
  const res = await fetch(`${API_BASE_URL}/api/outcomes/measure/${executionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      merchant_id: merchantId,
      measurement_window: measurementWindow,
    }),
    cache: 'no-store',
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `HTTP ${res.status}: Outcome measurement failed`);
  }
  return await res.json();
}

export async function fetchOutcomeByExecution(
  executionId: string
): Promise<import('@/types').OutcomeResult | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/executions/${executionId}/outcome`, {
      cache: 'no-store',
    });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Backend outcome query failed:', err);
    return null;
  }
}

export async function fetchOutcome(
  outcomeId: string
): Promise<import('@/types').OutcomeResult | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/outcomes/${outcomeId}`, {
      cache: 'no-store',
    });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Backend outcome query failed:', err);
    return null;
  }
}

export async function fetchOutcomesByMerchant(
  merchantId: string = 'MID-DEMO-98234'
): Promise<import('@/types').OutcomeResult[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/outcomes?merchant_id=${merchantId}`, {
      cache: 'no-store',
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Backend outcomes list query failed:', err);
    return [];
  }
}

export async function analyzeBusinessImpact(
  outcomeId: string,
  merchantId: string = 'MID-DEMO-98234'
): Promise<import('@/types').BusinessImpact> {
  const res = await fetch(`${API_BASE_URL}/api/business-impact/analyze/${outcomeId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ merchant_id: merchantId }),
    cache: 'no-store',
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `HTTP ${res.status}: Business impact analysis failed`);
  }
  return await res.json();
}

export async function fetchBusinessImpactByOutcome(
  outcomeId: string
): Promise<import('@/types').BusinessImpact | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/outcomes/${outcomeId}/business-impact`, {
      cache: 'no-store',
    });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Backend business impact query failed:', err);
    return null;
  }
}

export async function fetchBusinessImpact(
  impactId: string
): Promise<import('@/types').BusinessImpact | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/business-impact/${impactId}`, {
      cache: 'no-store',
    });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Backend business impact query failed:', err);
    return null;
  }
}

export async function fetchBusinessImpactsByMerchant(
  merchantId: string = 'MID-DEMO-98234'
): Promise<import('@/types').BusinessImpact[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/business-impact?merchant_id=${merchantId}`, {
      cache: 'no-store',
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Backend business impacts list query failed:', err);
    return [];
  }
}

export async function fetchAuditEvents(
  merchantId: string = 'MID-DEMO-98234',
  correlationId?: string,
  limit: number = 50
): Promise<import('@/types').AuditEvent[]> {
  try {
    const url = new URL(`${API_BASE_URL}/api/audit/events`);
    url.searchParams.set('merchant_id', merchantId);
    url.searchParams.set('limit', String(limit));
    if (correlationId) url.searchParams.set('correlation_id', correlationId);
    const res = await fetch(url.toString(), { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Backend /api/audit/events query failed:', err);
    return [];
  }
}

export async function fetchWorkflowAudit(
  correlationId: string
): Promise<import('@/types').AuditEvent[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/audit/workflow/${correlationId}`, {
      cache: 'no-store',
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn(`Backend /api/audit/workflow/${correlationId} query failed:`, err);
    return [];
  }
}

export async function verifyWorkflowAudit(
  correlationId: string
): Promise<import('@/types').WorkflowAuditVerification | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/audit/workflow/${correlationId}/verify`, {
      cache: 'no-store',
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn(`Backend /api/audit/workflow/${correlationId}/verify failed:`, err);
    return null;
  }
}

export async function fetchWorkflowExplainability(
  correlationId: string
): Promise<import('@/types').ExplainabilitySummary | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/explainability/workflow/${correlationId}`, {
      cache: 'no-store',
    });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn(`Backend /api/explainability/workflow/${correlationId} failed:`, err);
    return null;
  }
}

export async function fetchEntityExplainability(
  entityType: string,
  entityId: string
): Promise<import('@/types').ExplainabilitySummary | null> {
  try {
    const res = await fetch(
      `${API_BASE_URL}/api/explainability/entity/${encodeURIComponent(entityType)}/${encodeURIComponent(entityId)}`,
      { cache: 'no-store' }
    );
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn(`Backend /api/explainability/entity/${entityType}/${entityId} failed:`, err);
    return null;
  }
}

export async function evaluateAutonomy(
  actionId: string,
  merchantId: string = 'MID-DEMO-98234',
  overrideMode?: import('@/types').AutonomyMode
): Promise<import('@/types').AutonomyEvaluation> {
  const url = new URL(`${API_BASE_URL}/api/autonomy/evaluate/${actionId}`);
  url.searchParams.set('merchant_id', merchantId);
  if (overrideMode) {
    url.searchParams.set('override_mode', overrideMode);
  }
  const res = await fetch(url.toString(), {
    method: 'POST',
    cache: 'no-store',
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `HTTP ${res.status}: Failed to evaluate autonomy`);
  }
  return await res.json();
}

export async function fetchAutonomyByAction(
  actionId: string
): Promise<import('@/types').AutonomyEvaluation | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/autonomy/${actionId}`, {
      cache: 'no-store',
    });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn(`Backend /api/autonomy/${actionId} query failed:`, err);
    return null;
  }
}

export async function fetchWorkflowAutonomy(
  correlationId: string
): Promise<import('@/types').AutonomyEvaluation | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/autonomy/workflow/${correlationId}`, {
      cache: 'no-store',
    });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn(`Backend /api/autonomy/workflow/${correlationId} query failed:`, err);
    return null;
  }
}

export async function approveAutonomyAction(
  actionId: string,
  merchantId: string = 'MID-DEMO-98234',
  approver: string = 'Sharma Kirana Store Owner'
): Promise<import('@/types').AutonomyEvaluation> {
  const res = await fetch(`${API_BASE_URL}/api/autonomy/${actionId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ merchant_id: merchantId, approver }),
    cache: 'no-store',
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `HTTP ${res.status}: Failed to approve action`);
  }
  return await res.json();
}

export async function rejectAutonomyAction(
  actionId: string,
  merchantId: string = 'MID-DEMO-98234',
  reason: string = 'Merchant rejected proposed action parameters',
  approver: string = 'Sharma Kirana Store Owner'
): Promise<import('@/types').AutonomyEvaluation> {
  const res = await fetch(`${API_BASE_URL}/api/autonomy/${actionId}/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ merchant_id: merchantId, reason, approver }),
    cache: 'no-store',
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `HTTP ${res.status}: Failed to reject action`);
  }
  return await res.json();
}

export async function fetchMerchantAutonomyPolicy(
  merchantId: string = 'MID-DEMO-98234'
): Promise<import('@/types').MerchantAutonomyPolicy> {
  const res = await fetch(`${API_BASE_URL}/api/merchants/${merchantId}/autonomy`, {
    cache: 'no-store',
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to load merchant autonomy policy`);
  return await res.json();
}

export async function updateMerchantAutonomyPolicy(
  merchantId: string = 'MID-DEMO-98234',
  payload: Partial<import('@/types').MerchantAutonomyPolicy>
): Promise<import('@/types').MerchantAutonomyPolicy> {
  const res = await fetch(`${API_BASE_URL}/api/merchants/${merchantId}/autonomy`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    cache: 'no-store',
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `HTTP ${res.status}: Failed to update merchant autonomy policy`);
  }
  return await res.json();
}

// ==========================================
// Phase 13: Command Center AI & Live Experience
// ==========================================

export async function fetchAIStatus(): Promise<import('@/types').AIProviderStatus> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/ai/status`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('AI status endpoint unavailable, falling back:', err);
    return {
      active_provider: 'Deterministic Fallback (Local)',
      available_providers: ['Deterministic Fallback (Local)'],
      gemini_configured: false,
      hf_configured: false,
      simulation_mode: true,
    };
  }
}

export async function requestAIExplanation(
  correlationId: string,
  responseType: import('@/types').AIResponseType = 'SIGNAL_EXPLANATION'
): Promise<import('@/types').AIResponse> {
  const res = await fetch(
    `${API_BASE_URL}/api/ai/explain/${correlationId}?response_type=${responseType}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      cache: 'no-store',
    }
  );
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `HTTP ${res.status}: Failed to generate AI explanation`);
  }
  return await res.json();
}

export async function askMitraCopilot(
  request: import('@/types').AIMerchantQuestionRequest
): Promise<import('@/types').AIResponse> {
  const res = await fetch(`${API_BASE_URL}/api/ai/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    cache: 'no-store',
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `HTTP ${res.status}: Failed to query MITRA Copilot`);
  }
  return await res.json();
}

export async function triggerDemoScenario(
  scenarioId: string,
  merchantId: string = 'MID-DEMO-98234'
): Promise<import('@/types').DemoScenarioResult> {
  const res = await fetch(`${API_BASE_URL}/api/ai/demo-scenario/${scenarioId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario: scenarioId, merchant_id: merchantId }),
    cache: 'no-store',
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `HTTP ${res.status}: Failed to trigger demo scenario`);
  }
  return await res.json();
}

export async function resetDemo(): Promise<import('@/types').DemoResetResponse> {
  const res = await fetch(`${API_BASE_URL}/api/demo/reset`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `HTTP ${res.status}: Failed to reset demo environment`);
  }
  return await res.json();
}

export async function getSystemHealth(): Promise<import('@/types').SystemHealthResponse> {
  const res = await fetch(`${API_BASE_URL}/api/demo/health`, {
    cache: 'no-store',
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `HTTP ${res.status}: Failed to fetch system health`);
  }
  return await res.json();
}








