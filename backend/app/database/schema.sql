-- MITRA Relational Schema (SQLite)
-- 100% Free, Local, Simulated Digital-Twin Environment

PRAGMA foreign_keys = ON;

-- 1. Merchant Profile & Deterministic Guardrail Policies
CREATE TABLE IF NOT EXISTS merchants (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    location TEXT NOT NULL,
    minimum_margin REAL NOT NULL DEFAULT 0.10,
    daily_budget REAL NOT NULL DEFAULT 12000.0,
    max_discount REAL NOT NULL DEFAULT 100.0,
    max_campaign_frequency INTEGER NOT NULL DEFAULT 3,
    autonomy_level TEXT NOT NULL DEFAULT 'APPROVAL_REQUIRED',
    created_at TEXT NOT NULL
);

-- 2. Merchant Customers
CREATE TABLE IF NOT EXISTS customers (
    id TEXT PRIMARY KEY,
    merchant_id TEXT NOT NULL,
    segment TEXT NOT NULL, -- 'repeat_customer', 'regular', 'new_customer', 'inactive'
    orders_count INTEGER NOT NULL DEFAULT 0,
    last_order_at TEXT,
    engagement_score REAL NOT NULL DEFAULT 0.5,
    notification_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (merchant_id) REFERENCES merchants (id)
);

-- 3. Transactions (Digital-Twin Telemetry)
CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    merchant_id TEXT NOT NULL,
    customer_id TEXT,
    amount REAL NOT NULL,
    transaction_type TEXT NOT NULL DEFAULT 'SALE', -- 'SALE', 'REFUND'
    channel TEXT NOT NULL DEFAULT 'SOUNDBOX_UPI', -- 'SOUNDBOX_UPI', 'QR_UPI', 'CARD_MACHINE'
    timestamp TEXT NOT NULL,
    FOREIGN KEY (merchant_id) REFERENCES merchants (id),
    FOREIGN KEY (customer_id) REFERENCES customers (id)
);

-- 4. Merchant Marketing & Cashback Campaigns
CREATE TABLE IF NOT EXISTS campaigns (
    id TEXT PRIMARY KEY,
    merchant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    campaign_type TEXT NOT NULL,
    discount_amount REAL NOT NULL DEFAULT 0.0,
    discount_percent REAL NOT NULL DEFAULT 0.0,
    budget REAL NOT NULL DEFAULT 0.0,
    target_customer_count INTEGER NOT NULL DEFAULT 0,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    status TEXT NOT NULL, -- 'ACTIVE', 'EXPIRED', 'SCHEDULED', 'DRAFT'
    FOREIGN KEY (merchant_id) REFERENCES merchants (id)
);

-- 5. Time-Series Business Metrics
CREATE TABLE IF NOT EXISTS business_metrics (
    id TEXT PRIMARY KEY,
    merchant_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (merchant_id) REFERENCES merchants (id)
);

-- 6. Business Signals (Anomalies & Opportunities)
CREATE TABLE IF NOT EXISTS signals (
    id TEXT PRIMARY KEY,
    merchant_id TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    severity TEXT NOT NULL, -- 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    metric_name TEXT NOT NULL,
    baseline_value REAL NOT NULL,
    observed_value REAL NOT NULL,
    change_percentage REAL NOT NULL DEFAULT 0.0,
    decline_percentage REAL NOT NULL DEFAULT 0.0,
    description TEXT NOT NULL,
    detected_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE', -- 'ACTIVE', 'ACKNOWLEDGED', 'RESOLVED'
    context_data TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (merchant_id) REFERENCES merchants (id)
);

-- 7. Deep Investigations
CREATE TABLE IF NOT EXISTS investigations (
    id TEXT PRIMARY KEY,
    signal_id TEXT NOT NULL,
    status TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.8,
    finding TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (signal_id) REFERENCES signals (id)
);

-- 8. Candidate Action Proposals
CREATE TABLE IF NOT EXISTS actions (
    id TEXT PRIMARY KEY,
    merchant_id TEXT NOT NULL,
    signal_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    parameters TEXT NOT NULL, -- JSON string
    status TEXT NOT NULL DEFAULT 'PROPOSED', -- 'PROPOSED', 'EVALUATED', 'REJECTED'
    created_at TEXT NOT NULL,
    FOREIGN KEY (merchant_id) REFERENCES merchants (id),
    FOREIGN KEY (signal_id) REFERENCES signals (id)
);

-- 9. Deterministic Guardrail Evaluations
CREATE TABLE IF NOT EXISTS guardrail_evaluations (
    id TEXT PRIMARY KEY,
    action_id TEXT NOT NULL,
    merchant_id TEXT NOT NULL DEFAULT 'MID-DEMO-98234',
    overall_status TEXT NOT NULL DEFAULT 'PASS',
    passed INTEGER NOT NULL DEFAULT 1, -- 1 for True, 0 for False
    checks TEXT NOT NULL DEFAULT '[]', -- JSON string of GuardrailCheck array
    passed_checks TEXT NOT NULL DEFAULT '[]', -- JSON string array
    failed_checks TEXT NOT NULL DEFAULT '[]', -- JSON string array
    warnings TEXT NOT NULL DEFAULT '[]', -- JSON string array
    modifications TEXT NOT NULL DEFAULT '{}', -- JSON string
    original_values TEXT NOT NULL DEFAULT '{}', -- JSON string
    modified_values TEXT NOT NULL DEFAULT '{}', -- JSON string
    notes TEXT NOT NULL DEFAULT '',
    evaluated_at TEXT NOT NULL,
    is_deterministic INTEGER NOT NULL DEFAULT 1,
    rule_name TEXT DEFAULT 'ALL_GUARDRAILS',
    actual_value TEXT DEFAULT '',
    required_value TEXT DEFAULT '',
    reason TEXT DEFAULT '',
    FOREIGN KEY (action_id) REFERENCES actions (id)
);

-- 10. Authoritative Decisions (Strictly PASS / MODIFY / BLOCK / ESCALATE + Merchant Sign-off)
CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    action_id TEXT NOT NULL,
    evaluation_id TEXT NOT NULL DEFAULT '',
    merchant_id TEXT NOT NULL DEFAULT 'MID-DEMO-98234',
    decision_state TEXT NOT NULL DEFAULT 'PASS',
    state TEXT NOT NULL DEFAULT 'PASS',
    reason TEXT NOT NULL DEFAULT '',
    rationale TEXT NOT NULL DEFAULT '',
    triggered_rules TEXT NOT NULL DEFAULT '[]',
    modifications TEXT NOT NULL DEFAULT '{}',
    approval_required INTEGER NOT NULL DEFAULT 1,
    approval_status TEXT NOT NULL DEFAULT 'PENDING',
    decided_at TEXT NOT NULL DEFAULT '',
    decided_by TEXT NOT NULL DEFAULT 'MITRA_DECISION_ENGINE',
    approved_at TEXT DEFAULT NULL,
    rejected_at TEXT DEFAULT NULL,
    proposal_hash TEXT NOT NULL DEFAULT '',
    evaluation_hash TEXT NOT NULL DEFAULT '',
    is_deterministic INTEGER NOT NULL DEFAULT 1,
    approved_action TEXT NOT NULL DEFAULT '{}',
    requires_human_review INTEGER NOT NULL DEFAULT 0,
    is_execution_eligible INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (action_id) REFERENCES actions (id)
);

-- 11. Execution Dispatch Records (Strictly SIMULATION mode)
CREATE TABLE IF NOT EXISTS executions (
    id TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL UNIQUE,
    action_id TEXT NOT NULL DEFAULT '',
    merchant_id TEXT NOT NULL DEFAULT 'MID-DEMO-98234',
    action_type TEXT NOT NULL,
    execution_state TEXT NOT NULL DEFAULT 'PENDING',
    execution_mode TEXT NOT NULL DEFAULT 'SIMULATION',
    simulated INTEGER NOT NULL DEFAULT 1,
    approved_action TEXT NOT NULL DEFAULT '{}',
    result TEXT NOT NULL DEFAULT '{}',
    error TEXT DEFAULT NULL,
    status TEXT NOT NULL DEFAULT 'COMPLETED', -- backward compatibility
    output TEXT NOT NULL DEFAULT '{}', -- backward compatibility
    executed_at TEXT NOT NULL,
    FOREIGN KEY (decision_id) REFERENCES decisions (id)
);

-- 12. Post-Execution Outcome Measurements (Phase 9)
CREATE TABLE IF NOT EXISTS outcomes (
    id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    decision_id TEXT,
    action_id TEXT,
    merchant_id TEXT NOT NULL DEFAULT 'MID-DEMO-98234',
    baseline_window TEXT NOT NULL DEFAULT '{}',
    measurement_window TEXT NOT NULL DEFAULT '{}',
    baseline_metrics TEXT NOT NULL DEFAULT '{}',
    post_action_metrics TEXT NOT NULL DEFAULT '{}',
    metric_changes TEXT NOT NULL DEFAULT '{}',
    outcome_status TEXT NOT NULL DEFAULT 'MEASURED',
    status TEXT NOT NULL DEFAULT 'MEASURED',
    measurement_mode TEXT NOT NULL DEFAULT 'SIMULATION',
    simulated INTEGER NOT NULL DEFAULT 1,
    disclaimer TEXT NOT NULL DEFAULT 'SIMULATED - PROTOTYPE - NOT REAL PAYTM PERFORMANCE',
    measured_at TEXT NOT NULL,
    -- Backward compatibility columns from Phase 2
    metric_name TEXT DEFAULT 'evening_orders',
    baseline_value REAL DEFAULT 0.0,
    observed_value REAL DEFAULT 0.0,
    delta_percent REAL DEFAULT 0.0,
    roi REAL DEFAULT 0.0,
    verified_at TEXT,
    FOREIGN KEY (execution_id) REFERENCES executions (id)
);

-- 13. Audit Events (Hash-Chained Ledger)
CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    event_id TEXT,
    timestamp TEXT NOT NULL,
    stage TEXT NOT NULL,
    actor TEXT NOT NULL,
    event_type TEXT NOT NULL DEFAULT 'WORKFLOW_STEP',
    action_description TEXT,
    input_payload TEXT NOT NULL,
    output_payload TEXT NOT NULL,
    decision TEXT,
    reason TEXT,
    previous_hash TEXT NOT NULL DEFAULT 'GENESIS',
    integrity_hash TEXT NOT NULL,
    correlation_id TEXT,
    merchant_id TEXT NOT NULL DEFAULT 'MID-DEMO-98234',
    signal_id TEXT,
    investigation_id TEXT,
    action_id TEXT,
    decision_id TEXT,
    execution_id TEXT,
    outcome_id TEXT,
    impact_id TEXT,
    simulated INTEGER NOT NULL DEFAULT 1
);

-- 14. Post-Outcome Business Impact & ROI Analysis (Phase 10)
CREATE TABLE IF NOT EXISTS business_impacts (
    id TEXT PRIMARY KEY,
    outcome_id TEXT NOT NULL UNIQUE,
    execution_id TEXT NOT NULL,
    decision_id TEXT,
    action_id TEXT,
    merchant_id TEXT NOT NULL DEFAULT 'MID-DEMO-98234',
    impact_status TEXT NOT NULL DEFAULT 'CALCULATED',
    status TEXT NOT NULL DEFAULT 'CALCULATED',
    baseline_revenue REAL NOT NULL DEFAULT 0.0,
    post_action_revenue REAL NOT NULL DEFAULT 0.0,
    incremental_revenue REAL NOT NULL DEFAULT 0.0,
    baseline_orders REAL NOT NULL DEFAULT 0.0,
    post_action_orders REAL NOT NULL DEFAULT 0.0,
    incremental_orders REAL NOT NULL DEFAULT 0.0,
    orders_change REAL NOT NULL DEFAULT 0.0,
    baseline_evening_orders REAL NOT NULL DEFAULT 0.0,
    post_action_evening_orders REAL NOT NULL DEFAULT 0.0,
    evening_orders_change REAL NOT NULL DEFAULT 0.0,
    campaign_cost REAL NOT NULL DEFAULT 0.0,
    gross_profit_impact REAL DEFAULT NULL,
    roi REAL DEFAULT NULL,
    roi_percentage REAL DEFAULT NULL,
    cost_per_incremental_order REAL DEFAULT NULL,
    revenue_per_campaign_rupee REAL DEFAULT NULL,
    impact_classification TEXT NOT NULL DEFAULT 'POSITIVE',
    measurement_mode TEXT NOT NULL DEFAULT 'SIMULATION',
    simulated INTEGER NOT NULL DEFAULT 1,
    disclaimer TEXT NOT NULL DEFAULT 'SIMULATED - PROTOTYPE - NOT REAL PAYTM PERFORMANCE',
    calculated_at TEXT NOT NULL,
    FOREIGN KEY (outcome_id) REFERENCES outcomes (id),
    FOREIGN KEY (execution_id) REFERENCES executions (id)
);

-- Indices for rapid queries
CREATE INDEX IF NOT EXISTS idx_transactions_merchant_timestamp ON transactions (merchant_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_customers_merchant_segment ON customers (merchant_id, segment);
CREATE INDEX IF NOT EXISTS idx_metrics_merchant_name_time ON business_metrics (merchant_id, metric_name, timestamp);
CREATE UNIQUE INDEX IF NOT EXISTS idx_business_impacts_outcome_id ON business_impacts (outcome_id);
CREATE INDEX IF NOT EXISTS idx_business_impacts_execution_id ON business_impacts (execution_id);
CREATE INDEX IF NOT EXISTS idx_business_impacts_merchant ON business_impacts (merchant_id);

-- 15. Controlled Autonomy Evaluations (Phase 12)
CREATE TABLE IF NOT EXISTS autonomy_evaluations (
    id TEXT PRIMARY KEY,
    correlation_id TEXT NOT NULL,
    merchant_id TEXT NOT NULL DEFAULT 'MID-DEMO-98234',
    action_id TEXT NOT NULL UNIQUE,
    guardrail_evaluation_id TEXT NOT NULL,
    decision_id TEXT NOT NULL,
    autonomy_mode TEXT NOT NULL DEFAULT 'APPROVAL_REQUIRED',
    guardrail_status TEXT NOT NULL DEFAULT 'PASS',
    approval_required INTEGER NOT NULL DEFAULT 1,
    auto_approval_allowed INTEGER NOT NULL DEFAULT 0,
    auto_approval_reason TEXT NOT NULL DEFAULT '',
    approval_source TEXT NOT NULL DEFAULT 'PENDING',
    actor_type TEXT NOT NULL DEFAULT 'SYSTEM',
    blocked INTEGER NOT NULL DEFAULT 0,
    escalated INTEGER NOT NULL DEFAULT 0,
    approved_action TEXT NOT NULL DEFAULT '{}',
    evaluated_risk REAL NOT NULL DEFAULT 0.0,
    policy_threshold REAL NOT NULL DEFAULT 0.30,
    policy_version TEXT NOT NULL DEFAULT '1.0.0',
    passed_checks TEXT NOT NULL DEFAULT '[]',
    failed_checks TEXT NOT NULL DEFAULT '[]',
    simulation_mode INTEGER NOT NULL DEFAULT 1,
    evaluated_at TEXT NOT NULL,
    FOREIGN KEY (action_id) REFERENCES actions (id),
    FOREIGN KEY (guardrail_evaluation_id) REFERENCES guardrail_evaluations (id),
    FOREIGN KEY (decision_id) REFERENCES decisions (id)
);

CREATE INDEX IF NOT EXISTS idx_autonomy_evaluations_correlation ON autonomy_evaluations (correlation_id);
CREATE INDEX IF NOT EXISTS idx_autonomy_evaluations_merchant ON autonomy_evaluations (merchant_id);
CREATE INDEX IF NOT EXISTS idx_autonomy_evaluations_decision ON autonomy_evaluations (decision_id);

