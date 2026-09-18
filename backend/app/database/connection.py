import os
import sqlite3
from pathlib import Path
from app.core.logging import logger

DB_FILE = Path(__file__).resolve().parent.parent.parent / "mitra_local.db"
SCHEMA_FILE = Path(__file__).resolve().parent / "schema.sql"


def get_db_path() -> str:
    """Returns the local SQLite database file path."""
    return str(DB_FILE)


def get_connection() -> sqlite3.Connection:
    """Returns a SQLite connection with row factory and foreign keys enabled."""
    conn = sqlite3.connect(get_db_path(), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    return conn


def init_db() -> None:
    """Initializes local SQLite database and applies schema.sql."""
    logger.info("Initializing local SQLite database at %s", get_db_path())
    conn = get_connection()
    try:
        with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
            schema_script = f.read()
        conn.executescript(schema_script)

        # Migration helper: ensure new Phase 3 & 4 columns exist if table was previously created
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(signals);")
        existing_cols = {row["name"] for row in cursor.fetchall()}
        for col, col_def in [
            ("change_percentage", "REAL NOT NULL DEFAULT 0.0"),
            ("decline_percentage", "REAL NOT NULL DEFAULT 0.0"),
            ("context_data", "TEXT NOT NULL DEFAULT '{}'"),
        ]:
            if col not in existing_cols:
                cursor.execute(f"ALTER TABLE signals ADD COLUMN {col} {col_def};")

        cursor.execute("PRAGMA table_info(investigations);")
        existing_inv_cols = {row["name"] for row in cursor.fetchall()}
        for col, col_def in [
            ("summary", "TEXT NOT NULL DEFAULT ''"),
            ("hypotheses", "TEXT NOT NULL DEFAULT '[]'"),
            ("evidence_bundle", "TEXT NOT NULL DEFAULT '{}'"),
            ("evidence_ids", "TEXT NOT NULL DEFAULT '[]'"),
            ("limitations", "TEXT NOT NULL DEFAULT '[]'"),
            ("confidence_level", "TEXT NOT NULL DEFAULT 'MEDIUM'"),
            ("is_fallback", "INTEGER NOT NULL DEFAULT 0"),
        ]:
            if col not in existing_inv_cols:
                cursor.execute(f"ALTER TABLE investigations ADD COLUMN {col} {col_def};")

        cursor.execute("PRAGMA table_info(actions);")
        existing_action_cols = {row["name"] for row in cursor.fetchall()}
        for col, col_def in [
            ("investigation_id", "TEXT NOT NULL DEFAULT ''"),
            ("objective", "TEXT NOT NULL DEFAULT ''"),
            ("target_segment", "TEXT NOT NULL DEFAULT ''"),
            ("target_customer_count", "INTEGER NOT NULL DEFAULT 0"),
            ("incentive_type", "TEXT NOT NULL DEFAULT ''"),
            ("incentive_value", "REAL NOT NULL DEFAULT 0.0"),
            ("duration", "TEXT NOT NULL DEFAULT ''"),
            ("reason", "TEXT NOT NULL DEFAULT ''"),
            ("supporting_evidence_ids", "TEXT NOT NULL DEFAULT '[]'"),
            ("constraints", "TEXT NOT NULL DEFAULT '{}'"),
            ("estimated_cost_inr", "REAL NOT NULL DEFAULT 0.0"),
            ("is_fallback", "INTEGER NOT NULL DEFAULT 0"),
        ]:
            if col not in existing_action_cols:
                cursor.execute(f"ALTER TABLE actions ADD COLUMN {col} {col_def};")

        cursor.execute("PRAGMA table_info(guardrail_evaluations);")
        existing_grd_cols = {row["name"] for row in cursor.fetchall()}
        for col, col_def in [
            ("merchant_id", "TEXT NOT NULL DEFAULT 'MID-DEMO-98234'"),
            ("overall_status", "TEXT NOT NULL DEFAULT 'PASS'"),
            ("passed", "INTEGER NOT NULL DEFAULT 1"),
            ("checks", "TEXT NOT NULL DEFAULT '[]'"),
            ("passed_checks", "TEXT NOT NULL DEFAULT '[]'"),
            ("failed_checks", "TEXT NOT NULL DEFAULT '[]'"),
            ("warnings", "TEXT NOT NULL DEFAULT '[]'"),
            ("modifications", "TEXT NOT NULL DEFAULT '{}'"),
            ("original_values", "TEXT NOT NULL DEFAULT '{}'"),
            ("modified_values", "TEXT NOT NULL DEFAULT '{}'"),
            ("notes", "TEXT NOT NULL DEFAULT ''"),
            ("is_deterministic", "INTEGER NOT NULL DEFAULT 1"),
        ]:
            if col not in existing_grd_cols:
                cursor.execute(f"ALTER TABLE guardrail_evaluations ADD COLUMN {col} {col_def};")

        cursor.execute("PRAGMA table_info(decisions);")
        existing_dec_cols = {row["name"] for row in cursor.fetchall()}
        for col, col_def in [
            ("evaluation_id", "TEXT NOT NULL DEFAULT ''"),
            ("merchant_id", "TEXT NOT NULL DEFAULT 'MID-DEMO-98234'"),
            ("decision_state", "TEXT NOT NULL DEFAULT 'PASS'"),
            ("reason", "TEXT NOT NULL DEFAULT ''"),
            ("triggered_rules", "TEXT NOT NULL DEFAULT '[]'"),
            ("modifications", "TEXT NOT NULL DEFAULT '{}'"),
            ("approval_required", "INTEGER NOT NULL DEFAULT 1"),
            ("approval_status", "TEXT NOT NULL DEFAULT 'PENDING'"),
            ("decided_at", "TEXT NOT NULL DEFAULT ''"),
            ("decided_by", "TEXT NOT NULL DEFAULT 'MITRA_DECISION_ENGINE'"),
            ("approved_at", "TEXT DEFAULT NULL"),
            ("rejected_at", "TEXT DEFAULT NULL"),
            ("proposal_hash", "TEXT NOT NULL DEFAULT ''"),
            ("evaluation_hash", "TEXT NOT NULL DEFAULT ''"),
            ("is_deterministic", "INTEGER NOT NULL DEFAULT 1"),
            ("approved_action", "TEXT NOT NULL DEFAULT '{}'"),
            ("is_execution_eligible", "INTEGER NOT NULL DEFAULT 0"),
        ]:
            if col not in existing_dec_cols:
                cursor.execute(f"ALTER TABLE decisions ADD COLUMN {col} {col_def};")

        cursor.execute("PRAGMA table_info(executions);")
        existing_exec_cols = {row["name"] for row in cursor.fetchall()}
        for col, col_def in [
            ("action_id", "TEXT NOT NULL DEFAULT ''"),
            ("merchant_id", "TEXT NOT NULL DEFAULT 'MID-DEMO-98234'"),
            ("execution_state", "TEXT NOT NULL DEFAULT 'PENDING'"),
            ("execution_mode", "TEXT NOT NULL DEFAULT 'SIMULATION'"),
            ("approved_action", "TEXT NOT NULL DEFAULT '{}'"),
            ("result", "TEXT NOT NULL DEFAULT '{}'"),
            ("error", "TEXT DEFAULT NULL"),
        ]:
            if col not in existing_exec_cols:
                cursor.execute(f"ALTER TABLE executions ADD COLUMN {col} {col_def};")

        # Ensure unique index on executions(decision_id)
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_executions_decision_id ON executions (decision_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_executions_merchant_id ON executions (merchant_id);")

        # Dynamic migrations for outcomes table (Phase 9)
        cursor.execute("PRAGMA table_info(outcomes);")
        existing_out_cols = {row["name"] for row in cursor.fetchall()}
        for col, col_def in [
            ("decision_id", "TEXT DEFAULT NULL"),
            ("action_id", "TEXT DEFAULT NULL"),
            ("merchant_id", "TEXT NOT NULL DEFAULT 'MID-DEMO-98234'"),
            ("baseline_window", "TEXT NOT NULL DEFAULT '{}'"),
            ("measurement_window", "TEXT NOT NULL DEFAULT '{}'"),
            ("baseline_metrics", "TEXT NOT NULL DEFAULT '{}'"),
            ("post_action_metrics", "TEXT NOT NULL DEFAULT '{}'"),
            ("metric_changes", "TEXT NOT NULL DEFAULT '{}'"),
            ("outcome_status", "TEXT NOT NULL DEFAULT 'MEASURED'"),
            ("status", "TEXT NOT NULL DEFAULT 'MEASURED'"),
            ("measurement_mode", "TEXT NOT NULL DEFAULT 'SIMULATION'"),
            ("disclaimer", "TEXT NOT NULL DEFAULT 'SIMULATED - PROTOTYPE - NOT REAL PAYTM PERFORMANCE'"),
            ("measured_at", "TEXT NOT NULL DEFAULT ''"),
        ]:
            if col not in existing_out_cols:
                cursor.execute(f"ALTER TABLE outcomes ADD COLUMN {col} {col_def};")

        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_outcomes_execution_id ON outcomes (execution_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_merchant ON outcomes (merchant_id);")

        # Dynamic migrations for business_impacts table (Phase 10)
        cursor.execute(
            """
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
            """
        )
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_business_impacts_outcome_id ON business_impacts (outcome_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_business_impacts_execution_id ON business_impacts (execution_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_business_impacts_merchant ON business_impacts (merchant_id);")

        # Dynamic migrations for audit_events table (Phase 11)
        cursor.execute("PRAGMA table_info(audit_events);")
        existing_aud_cols = {row["name"] for row in cursor.fetchall()}
        for col, col_def in [
            ("previous_hash", "TEXT NOT NULL DEFAULT 'GENESIS'"),
            ("correlation_id", "TEXT DEFAULT NULL"),
            ("merchant_id", "TEXT NOT NULL DEFAULT 'MID-DEMO-98234'"),
            ("signal_id", "TEXT DEFAULT NULL"),
            ("investigation_id", "TEXT DEFAULT NULL"),
            ("action_id", "TEXT DEFAULT NULL"),
            ("decision_id", "TEXT DEFAULT NULL"),
            ("execution_id", "TEXT DEFAULT NULL"),
            ("outcome_id", "TEXT DEFAULT NULL"),
            ("impact_id", "TEXT DEFAULT NULL"),
            ("simulated", "INTEGER NOT NULL DEFAULT 1"),
        ]:
            if col not in existing_aud_cols:
                cursor.execute(f"ALTER TABLE audit_events ADD COLUMN {col} {col_def};")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_correlation_id ON audit_events (correlation_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_merchant ON audit_events (merchant_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON audit_events (timestamp);")

        # Dynamic migrations for merchants table (Phase 12 autonomy policy)
        cursor.execute("PRAGMA table_info(merchants);")
        existing_merch_cols = {row["name"] for row in cursor.fetchall()}
        for col, col_def in [
            ("autonomy_level", "TEXT NOT NULL DEFAULT 'APPROVAL_REQUIRED'"),
            ("auto_approval_risk_threshold", "REAL NOT NULL DEFAULT 0.30"),
            ("full_autonomy_risk_threshold", "REAL NOT NULL DEFAULT 0.50"),
            ("auto_approval_max_budget", "REAL NOT NULL DEFAULT 12000.0"),
            ("auto_approval_max_discount", "REAL NOT NULL DEFAULT 100.0"),
            ("require_human_for_modify", "INTEGER NOT NULL DEFAULT 0"),
            ("require_human_for_escalation", "INTEGER NOT NULL DEFAULT 1"),
        ]:
            if col not in existing_merch_cols:
                cursor.execute(f"ALTER TABLE merchants ADD COLUMN {col} {col_def};")

        # Dynamic migrations for autonomy_evaluations table (Phase 12)
        cursor.execute(
            """
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
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_autonomy_evaluations_correlation ON autonomy_evaluations (correlation_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_autonomy_evaluations_merchant ON autonomy_evaluations (merchant_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_autonomy_evaluations_decision ON autonomy_evaluations (decision_id);")

        conn.commit()
        logger.info("Local SQLite database schema initialized successfully.")
    except Exception as exc:
        logger.error("Failed to initialize database schema: %s", exc)
        raise
    finally:
        conn.close()
