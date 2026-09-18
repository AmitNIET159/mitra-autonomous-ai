from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
import uuid
from app.database.connection import get_connection


class MerchantRepository:
    """Repository for merchant digital twin profiles and guardrail limits."""

    @staticmethod
    def get_merchant(merchant_id: str = "MID-DEMO-98234") -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM merchants WHERE id = ?", (merchant_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()

    @staticmethod
    def upsert_merchant(merchant: Dict[str, Any]) -> None:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO merchants (
                    id, name, category, location, minimum_margin,
                    daily_budget, max_discount, max_campaign_frequency,
                    autonomy_level, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    category = excluded.category,
                    location = excluded.location,
                    minimum_margin = excluded.minimum_margin,
                    daily_budget = excluded.daily_budget,
                    max_discount = excluded.max_discount,
                    max_campaign_frequency = excluded.max_campaign_frequency,
                    autonomy_level = excluded.autonomy_level
                """,
                (
                    merchant["id"],
                    merchant["name"],
                    merchant["category"],
                    merchant["location"],
                    merchant.get("minimum_margin", 0.10),
                    merchant.get("daily_budget", 12000.0),
                    merchant.get("max_discount", 100.0),
                    merchant.get("max_campaign_frequency", 3),
                    merchant.get("autonomy_level", "APPROVAL_REQUIRED"),
                    merchant.get("created_at"),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_autonomy_policy(merchant_id: str = "MID-DEMO-98234") -> Dict[str, Any]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM merchants WHERE id = ?", (merchant_id,))
            row = cursor.fetchone()
            if not row:
                return {
                    "merchant_id": merchant_id,
                    "autonomy_mode": "APPROVAL_REQUIRED",
                    "auto_approval_risk_threshold": 0.30,
                    "full_autonomy_risk_threshold": 0.50,
                    "auto_approval_max_budget": 12000.0,
                    "auto_approval_max_discount": 100.0,
                    "require_human_for_modify": False,
                    "require_human_for_escalation": True,
                    "simulated": True,
                }
            r = dict(row)
            return {
                "merchant_id": r["id"],
                "autonomy_mode": r.get("autonomy_level") or "APPROVAL_REQUIRED",
                "auto_approval_risk_threshold": float(r.get("auto_approval_risk_threshold") or 0.30),
                "full_autonomy_risk_threshold": float(r.get("full_autonomy_risk_threshold") or 0.50),
                "auto_approval_max_budget": float(r.get("auto_approval_max_budget") or r.get("daily_budget") or 12000.0),
                "auto_approval_max_discount": float(r.get("auto_approval_max_discount") or r.get("max_discount") or 100.0),
                "require_human_for_modify": bool(r.get("require_human_for_modify", 0)),
                "require_human_for_escalation": bool(r.get("require_human_for_escalation", 1)),
                "simulated": True,
            }
        finally:
            conn.close()

    @staticmethod
    def update_autonomy_policy(
        merchant_id: str = "MID-DEMO-98234",
        autonomy_mode: str = "APPROVAL_REQUIRED",
        auto_approval_risk_threshold: Optional[float] = None,
        full_autonomy_risk_threshold: Optional[float] = None,
        auto_approval_max_budget: Optional[float] = None,
        auto_approval_max_discount: Optional[float] = None,
        require_human_for_modify: Optional[bool] = None,
        require_human_for_escalation: Optional[bool] = None,
    ) -> Dict[str, Any]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM merchants WHERE id = ?", (merchant_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Merchant {merchant_id} not found.")

            updates = ["autonomy_level = ?"]
            params: List[Any] = [autonomy_mode]

            if auto_approval_risk_threshold is not None:
                updates.append("auto_approval_risk_threshold = ?")
                params.append(auto_approval_risk_threshold)
            if full_autonomy_risk_threshold is not None:
                updates.append("full_autonomy_risk_threshold = ?")
                params.append(full_autonomy_risk_threshold)
            if auto_approval_max_budget is not None:
                updates.append("auto_approval_max_budget = ?")
                params.append(auto_approval_max_budget)
            if auto_approval_max_discount is not None:
                updates.append("auto_approval_max_discount = ?")
                params.append(auto_approval_max_discount)
            if require_human_for_modify is not None:
                updates.append("require_human_for_modify = ?")
                params.append(1 if require_human_for_modify else 0)
            if require_human_for_escalation is not None:
                updates.append("require_human_for_escalation = ?")
                params.append(1 if require_human_for_escalation else 0)

            params.append(merchant_id)
            cursor.execute(
                f"UPDATE merchants SET {', '.join(updates)} WHERE id = ?",
                tuple(params),
            )
            conn.commit()
            return MerchantRepository.get_autonomy_policy(merchant_id)
        finally:
            conn.close()


class CustomerRepository:
    """Repository for merchant customer digital twins and segmentation."""

    @staticmethod
    def get_customers_summary(merchant_id: str = "MID-DEMO-98234") -> Dict[str, Any]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT segment, COUNT(*) as count, AVG(engagement_score) as avg_engagement
                FROM customers
                WHERE merchant_id = ?
                GROUP BY segment
                """,
                (merchant_id,),
            )
            rows = cursor.fetchall()
            segments = {r["segment"]: r["count"] for r in rows}
            total = sum(segments.values())

            if total == 0:
                return {
                    "merchant_id": merchant_id,
                    "total_customers": 520,
                    "segment_breakdown": {
                        "repeat_customer": 182,
                        "regular": 248,
                        "inactive": 40,
                        "new": 50,
                    },
                    "target_campaign_customers": 486,
                }

            # Candidate campaign target segment:
            # All repeat_customer + regular + inactive customers with engagement >= 0.2
            cursor.execute(
                """
                SELECT COUNT(*) as target_count
                FROM customers
                WHERE merchant_id = ?
                  AND (segment IN ('repeat_customer', 'regular')
                       OR (segment = 'inactive' AND engagement_score >= 0.2))
                """,
                (merchant_id,),
            )
            target_row = cursor.fetchone()
            target_customer_count = target_row["target_count"] if target_row else 0

            return {
                "merchant_id": merchant_id,
                "total_customers": total,
                "segment_breakdown": segments,
                "target_campaign_customers": target_customer_count,
            }
        finally:
            conn.close()

    @staticmethod
    def get_customers(merchant_id: str = "MID-DEMO-98234", limit: int = 50) -> List[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM customers WHERE merchant_id = ? ORDER BY orders_count DESC LIMIT ?",
                (merchant_id, limit),
            )
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()


class TransactionRepository:
    """Repository for simulated digital-twin transactions and slot statistics."""

    @staticmethod
    def get_stats(merchant_id: str = "MID-DEMO-98234") -> Dict[str, Any]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total_orders,
                    COALESCE(SUM(amount), 0.0) as total_revenue,
                    COALESCE(AVG(amount), 0.0) as avg_basket_size
                FROM transactions
                WHERE merchant_id = ?
                """,
                (merchant_id,),
            )
            summary = dict(cursor.fetchone())

            # Determine the latest transaction timestamp to anchor evaluation window
            cursor.execute(
                "SELECT MAX(timestamp) as max_ts FROM transactions WHERE merchant_id = ?",
                (merchant_id,),
            )
            max_row = cursor.fetchone()
            max_ts = max_row["max_ts"] if max_row and max_row["max_ts"] else "2026-09-17T21:00:00"

            # Evening orders (5:00 PM to 8:59 PM) in the current evaluation window (last 4 days)
            cursor.execute(
                """
                SELECT COUNT(*) as evening_orders, COALESCE(SUM(amount), 0.0) as evening_gmv
                FROM transactions
                WHERE merchant_id = ?
                  AND date(timestamp) >= date(?, '-3 days')
                  AND strftime('%H', timestamp) >= '17'
                  AND strftime('%H', timestamp) < '21'
                """,
                (merchant_id, max_ts),
            )
            evening_current = dict(cursor.fetchone())

            # Evening orders in historical baseline window (prior 10 days)
            cursor.execute(
                """
                SELECT COUNT(*) as baseline_evening_orders, COALESCE(SUM(amount), 0.0) as baseline_evening_gmv
                FROM transactions
                WHERE merchant_id = ?
                  AND date(timestamp) < date(?, '-3 days')
                  AND strftime('%H', timestamp) >= '17'
                  AND strftime('%H', timestamp) < '21'
                """,
                (merchant_id, max_ts),
            )
            evening_baseline = dict(cursor.fetchone())

            return {
                "total_orders": summary["total_orders"],
                "total_revenue": round(summary["total_revenue"], 2),
                "avg_basket_size": round(summary["avg_basket_size"], 2),
                "evening_orders": evening_current["evening_orders"],
                "evening_revenue": round(evening_current["evening_gmv"], 2),
                "baseline_evening_orders": evening_baseline["baseline_evening_orders"],
                "baseline_evening_revenue": round(evening_baseline["baseline_evening_gmv"], 2),
            }
        finally:
            conn.close()

    @staticmethod
    def get_recent(merchant_id: str = "MID-DEMO-98234", limit: int = 25) -> List[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM transactions WHERE merchant_id = ? ORDER BY timestamp DESC LIMIT ?",
                (merchant_id, limit),
            )
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()


class CampaignRepository:
    """Repository for marketing and discount campaigns."""

    @staticmethod
    def get_campaigns(merchant_id: str = "MID-DEMO-98234") -> List[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM campaigns WHERE merchant_id = ? ORDER BY started_at DESC",
                (merchant_id,),
            )
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()


class BusinessMetricRepository:
    """Repository for time-series business metrics."""

    @staticmethod
    def get_metrics_map(merchant_id: str = "MID-DEMO-98234") -> Dict[str, float]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT metric_name, metric_value
                FROM business_metrics
                WHERE merchant_id = ?
                ORDER BY timestamp DESC
                """,
                (merchant_id,),
            )
            result = {}
            for row in cursor.fetchall():
                name = row["metric_name"]
                if name not in result:
                    result[name] = float(row["metric_value"])
            return result
        finally:
            conn.close()


class SignalRepository:
    """Repository for business anomaly signals and lifecycle tracking."""

    @staticmethod
    def upsert_active_signal(
        merchant_id: str,
        signal_type: str,
        severity: str,
        metric_name: str,
        baseline_value: float,
        observed_value: float,
        change_percentage: float,
        decline_percentage: float,
        description: str,
        evidence: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Idempotent signal creation.
        
        If an ACTIVE signal for merchant_id + signal_type exists, updates it.
        Otherwise, inserts a new ACTIVE signal.
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM signals
                WHERE merchant_id = ? AND signal_type = ? AND status = 'ACTIVE'
                """,
                (merchant_id, signal_type),
            )
            existing = cursor.fetchone()

            now_iso = datetime.now(timezone.utc).isoformat()
            context_json = json.dumps(evidence, default=str)

            # Ensure merchant exists to satisfy foreign key constraint
            cursor.execute("SELECT id FROM merchants WHERE id = ?", (merchant_id,))
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO merchants (
                        id, name, category, location, minimum_margin,
                        daily_budget, max_discount, max_campaign_frequency,
                        autonomy_level, created_at
                    ) VALUES (?, 'Simulated Merchant', 'Retail', 'Delhi NCR', 0.10, 12000.0, 100.0, 3, 'APPROVAL_REQUIRED', ?)
                    """,
                    (merchant_id, now_iso),
                )

            if existing:
                signal_id = existing["id"]
                cursor.execute(
                    """
                    UPDATE signals SET
                        severity = ?,
                        baseline_value = ?,
                        observed_value = ?,
                        change_percentage = ?,
                        decline_percentage = ?,
                        description = ?,
                        detected_at = ?,
                        context_data = ?
                    WHERE id = ?
                    """,
                    (
                        severity,
                        baseline_value,
                        observed_value,
                        change_percentage,
                        decline_percentage,
                        description,
                        now_iso,
                        context_json,
                        signal_id,
                    ),
                )
                conn.commit()
                cursor.execute("SELECT * FROM signals WHERE id = ?", (signal_id,))
                return dict(cursor.fetchone())
            else:
                import uuid
                signal_id = f"sig-{uuid.uuid4().hex[:10]}"
                cursor.execute(
                    """
                    INSERT INTO signals (
                        id, merchant_id, signal_type, severity, metric_name,
                        baseline_value, observed_value, change_percentage,
                        decline_percentage, description, detected_at, status, context_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?)
                    """,
                    (
                        signal_id,
                        merchant_id,
                        signal_type,
                        severity,
                        metric_name,
                        baseline_value,
                        observed_value,
                        change_percentage,
                        decline_percentage,
                        description,
                        now_iso,
                        context_json,
                    ),
                )
                conn.commit()
                cursor.execute("SELECT * FROM signals WHERE id = ?", (signal_id,))
                return dict(cursor.fetchone())
        finally:
            conn.close()

    @staticmethod
    def get_signals(
        merchant_id: str = "MID-DEMO-98234",
        status: Optional[str] = None,
        severity: Optional[str] = None,
        signal_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Queries signals with optional status, severity, and type filtering."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            query = "SELECT * FROM signals WHERE merchant_id = ?"
            params: List[Any] = [merchant_id]

            if status is not None and not isinstance(status, str):
                status = getattr(status, "default", None)
            if severity is not None and not isinstance(severity, str):
                severity = getattr(severity, "default", None)
            if signal_type is not None and not isinstance(signal_type, str):
                signal_type = getattr(signal_type, "default", None)

            if status:
                query += " AND status = ?"
                params.append(str(status).upper())
            if severity:
                query += " AND severity = ?"
                params.append(str(severity).upper())
            if signal_type:
                query += " AND signal_type = ?"
                params.append(str(signal_type).upper())

            query += " ORDER BY detected_at DESC"
            cursor.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def get_signal_by_id(signal_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM signals WHERE id = ?", (signal_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_signal(signal_id: str) -> Optional[Dict[str, Any]]:
        return SignalRepository.get_signal_by_id(signal_id)

    @staticmethod
    def get_signals_by_merchant(merchant_id: str) -> List[Dict[str, Any]]:
        return SignalRepository.get_signals(merchant_id=merchant_id)

    @staticmethod
    def create_signal(
        signal_id: Optional[str] = None,
        merchant_id: str = "MID-DEMO-98234",
        signal_type: str = "EVENING_ORDER_DECLINE",
        severity: str = "MEDIUM",
        metric_name: str = "evening_orders",
        baseline_value: float = 0.0,
        observed_value: float = 0.0,
        change_percentage: float = 0.0,
        decline_percentage: Optional[float] = None,
        description: str = "",
        context_data: Optional[Dict[str, Any]] = None,
        detected_at: Optional[str] = None,
        status: str = "ACTIVE",
    ) -> Dict[str, Any]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            sid = signal_id or f"sig-{uuid.uuid4().hex[:10]}"
            now_iso = detected_at or datetime.now(timezone.utc).isoformat()
            d_pct = decline_percentage if decline_percentage is not None else abs(change_percentage)
            ctx_json = json.dumps(context_data or {})
            cursor.execute(
                """
                INSERT INTO signals (
                    id, merchant_id, signal_type, severity, metric_name,
                    baseline_value, observed_value, change_percentage,
                    decline_percentage, description, detected_at, status, context_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    baseline_value = excluded.baseline_value,
                    observed_value = excluded.observed_value,
                    change_percentage = excluded.change_percentage,
                    decline_percentage = excluded.decline_percentage,
                    description = excluded.description,
                    detected_at = excluded.detected_at,
                    status = excluded.status
                """,
                (
                    sid, merchant_id, signal_type, severity, metric_name,
                    baseline_value, observed_value, change_percentage,
                    d_pct, description, now_iso, status, ctx_json
                ),
            )
            conn.commit()
            cursor.execute("SELECT * FROM signals WHERE id = ?", (sid,))
            return dict(cursor.fetchone())
        finally:
            conn.close()

    @staticmethod
    def resolve_disappeared_signals(merchant_id: str, active_detected_types: List[str]) -> List[str]:
        """Marks any previously ACTIVE signals as RESOLVED if not detected in current run."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, signal_type FROM signals WHERE merchant_id = ? AND status = 'ACTIVE'",
                (merchant_id,),
            )
            rows = cursor.fetchall()
            resolved_ids = []
            for r in rows:
                if r["signal_type"] not in active_detected_types:
                    cursor.execute("UPDATE signals SET status = 'RESOLVED' WHERE id = ?", (r["id"],))
                    resolved_ids.append(r["id"])
            conn.commit()
            return resolved_ids
        finally:
            conn.close()


class InvestigationRepository:
    """Repository for deep investigations linked to business signals."""

    @staticmethod
    def create_or_update_investigation(
        signal_id: str,
        investigation_id: Optional[str] = None,
        status: str = "COMPLETED",
        finding: str = "",
        confidence: float = 0.8,
        summary: str = "",
        hypotheses: Optional[List[Dict[str, Any]]] = None,
        evidence_bundle: Optional[Dict[str, Any]] = None,
        evidence_ids: Optional[List[str]] = None,
        limitations: Optional[List[str]] = None,
        confidence_level: str = "MEDIUM",
        is_fallback: bool = False,
    ) -> Dict[str, Any]:
        """Persists or updates an investigation for a signal idempotently."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM investigations WHERE signal_id = ? ORDER BY created_at DESC LIMIT 1",
                (signal_id,),
            )
            existing = cursor.fetchone()

            now_iso = datetime.now(timezone.utc).isoformat()
            hypotheses_json = json.dumps(hypotheses or [])
            bundle_json = json.dumps(evidence_bundle or {})
            evidence_ids_json = json.dumps(evidence_ids or [])
            limitations_json = json.dumps(limitations or [])
            fallback_int = 1 if is_fallback else 0

            # Ensure parent signal exists to satisfy foreign key constraints
            cursor.execute("SELECT id FROM signals WHERE id = ?", (signal_id,))
            if not cursor.fetchone():
                cursor.execute("SELECT id FROM merchants LIMIT 1")
                m_row = cursor.fetchone()
                fallback_mid = m_row["id"] if m_row else "MID-DELHI-98234"
                cursor.execute("SELECT id FROM merchants WHERE id = ?", (fallback_mid,))
                if not cursor.fetchone():
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO merchants (
                            id, name, category, location, minimum_margin,
                            daily_budget, max_discount, max_campaign_frequency,
                            autonomy_level, created_at
                        ) VALUES (?, 'Simulated Merchant', 'Retail', 'Delhi NCR', 0.10, 12000.0, 100.0, 3, 'APPROVAL_REQUIRED', ?)
                        """,
                        (fallback_mid, now_iso),
                    )
                cursor.execute(
                    """
                    INSERT INTO signals (
                        id, merchant_id, signal_type, severity, metric_name,
                        baseline_value, observed_value, change_percentage,
                        decline_percentage, description, detected_at, status, context_data
                    ) VALUES (?, ?, 'GENERAL_ANOMALY', 'MEDIUM', 'metric', 0.0, 0.0, 0.0, 0.0, 'Signal', ?, 'ACTIVE', '{}')
                    """,
                    (signal_id, fallback_mid, now_iso),
                )

            if existing:
                inv_id = existing["id"]
                cursor.execute(
                    """
                    UPDATE investigations SET
                        status = ?,
                        confidence = ?,
                        finding = ?,
                        summary = ?,
                        hypotheses = ?,
                        evidence_bundle = ?,
                        evidence_ids = ?,
                        limitations = ?,
                        confidence_level = ?,
                        is_fallback = ?,
                        created_at = ?
                    WHERE id = ?
                    """,
                    (
                        status,
                        confidence,
                        finding,
                        summary,
                        hypotheses_json,
                        bundle_json,
                        evidence_ids_json,
                        limitations_json,
                        confidence_level,
                        fallback_int,
                        now_iso,
                        inv_id,
                    ),
                )
                conn.commit()
                cursor.execute("SELECT * FROM investigations WHERE id = ?", (inv_id,))
                return dict(cursor.fetchone())
            else:
                import uuid
                inv_id = investigation_id or f"inv-{uuid.uuid4().hex[:10]}"
                cursor.execute(
                    """
                    INSERT INTO investigations (
                        id, signal_id, status, confidence, finding, summary,
                        hypotheses, evidence_bundle, evidence_ids, limitations,
                        confidence_level, is_fallback, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        inv_id,
                        signal_id,
                        status,
                        confidence,
                        finding,
                        summary,
                        hypotheses_json,
                        bundle_json,
                        evidence_ids_json,
                        limitations_json,
                        confidence_level,
                        fallback_int,
                        now_iso,
                    ),
                )
                conn.commit()
                cursor.execute("SELECT * FROM investigations WHERE id = ?", (inv_id,))
                return dict(cursor.fetchone())
        finally:
            conn.close()

    @staticmethod
    def get_investigation(investigation_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM investigations WHERE id = ?", (investigation_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_investigation_by_signal(signal_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM investigations WHERE signal_id = ? ORDER BY created_at DESC LIMIT 1",
                (signal_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    get_by_signal = get_investigation_by_signal


class ActionRepository:
    """Repository for candidate action proposals and persistence."""

    @staticmethod
    def create_or_update_action_proposal(
        signal_id: str,
        investigation_id: str,
        merchant_id: str,
        action_type: str,
        action_id: Optional[str] = None,
        objective: str = "",
        target_segment: str = "repeat_customer, regular",
        target_customer_count: int = 0,
        incentive_type: str = "CASHBACK",
        incentive_value: float = 0.0,
        duration: str = "7 days",
        reason: str = "",
        supporting_evidence_ids: Optional[List[str]] = None,
        constraints: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        estimated_cost_inr: float = 0.0,
        status: str = "PROPOSED",
        is_fallback: bool = False,
    ) -> Dict[str, Any]:
        """Persists or updates an action proposal for an investigation idempotently."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now_iso = datetime.now(timezone.utc).isoformat()

            # Ensure parent merchant exists to satisfy foreign key constraint
            cursor.execute("SELECT id FROM merchants WHERE id = ?", (merchant_id,))
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO merchants (
                        id, name, category, location, minimum_margin,
                        daily_budget, max_discount, max_campaign_frequency,
                        autonomy_level, created_at
                    ) VALUES (?, 'Simulated Merchant', 'Retail', 'Delhi NCR', 0.10, 12000.0, 100.0, 3, 'APPROVAL_REQUIRED', ?)
                    """,
                    (merchant_id, now_iso),
                )

            # Ensure parent signal exists to satisfy foreign key constraint
            cursor.execute("SELECT id FROM signals WHERE id = ?", (signal_id,))
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT INTO signals (
                        id, merchant_id, signal_type, severity, metric_name,
                        baseline_value, observed_value, change_percentage,
                        decline_percentage, description, detected_at, status, context_data
                    ) VALUES (?, ?, 'GENERAL_ANOMALY', 'MEDIUM', 'metric', 0.0, 0.0, 0.0, 0.0, 'Signal', ?, 'ACTIVE', '{}')
                    """,
                    (signal_id, merchant_id, now_iso),
                )

            # Check if an action proposal already exists for this investigation_id
            cursor.execute(
                "SELECT id FROM actions WHERE investigation_id = ? ORDER BY created_at DESC LIMIT 1",
                (investigation_id,),
            )
            existing = cursor.fetchone()

            params = parameters or {}
            params_json = json.dumps(params)
            evidence_ids_json = json.dumps(supporting_evidence_ids or [])
            constraints_json = json.dumps(constraints or {})
            fallback_int = 1 if is_fallback else 0

            if existing:
                act_id = existing["id"]
                cursor.execute(
                    """
                    UPDATE actions SET
                        merchant_id = ?,
                        signal_id = ?,
                        action_type = ?,
                        parameters = ?,
                        status = ?,
                        objective = ?,
                        target_segment = ?,
                        target_customer_count = ?,
                        incentive_type = ?,
                        incentive_value = ?,
                        duration = ?,
                        reason = ?,
                        supporting_evidence_ids = ?,
                        constraints = ?,
                        estimated_cost_inr = ?,
                        is_fallback = ?,
                        created_at = ?
                    WHERE id = ?
                    """,
                    (
                        merchant_id,
                        signal_id,
                        action_type,
                        params_json,
                        status,
                        objective,
                        target_segment,
                        target_customer_count,
                        incentive_type,
                        incentive_value,
                        duration,
                        reason,
                        evidence_ids_json,
                        constraints_json,
                        estimated_cost_inr,
                        fallback_int,
                        now_iso,
                        act_id,
                    ),
                )
                conn.commit()
                cursor.execute("SELECT * FROM actions WHERE id = ?", (act_id,))
                return dict(cursor.fetchone())
            else:
                import uuid
                act_id = action_id or f"prop-{uuid.uuid4().hex[:10]}"
                cursor.execute(
                    """
                    INSERT INTO actions (
                        id, merchant_id, signal_id, action_type, parameters,
                        status, created_at, investigation_id, objective,
                        target_segment, target_customer_count, incentive_type,
                        incentive_value, duration, reason, supporting_evidence_ids,
                        constraints, estimated_cost_inr, is_fallback
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        act_id,
                        merchant_id,
                        signal_id,
                        action_type,
                        params_json,
                        status,
                        now_iso,
                        investigation_id,
                        objective,
                        target_segment,
                        target_customer_count,
                        incentive_type,
                        incentive_value,
                        duration,
                        reason,
                        evidence_ids_json,
                        constraints_json,
                        estimated_cost_inr,
                        fallback_int,
                    ),
                )
                conn.commit()
                cursor.execute("SELECT * FROM actions WHERE id = ?", (act_id,))
                return dict(cursor.fetchone())
        finally:
            conn.close()

    @staticmethod
    def get_action_proposal(action_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM actions WHERE id = ?", (action_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    # Alias for get_action_proposal
    get_action = get_action_proposal
    get_action_by_id = get_action_proposal

    @staticmethod
    def get_action_by_investigation(investigation_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM actions WHERE investigation_id = ? ORDER BY created_at DESC LIMIT 1",
                (investigation_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    get_by_investigation = get_action_by_investigation

    @staticmethod
    def get_actions_by_signal(signal_id: str) -> List[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM actions WHERE signal_id = ? ORDER BY created_at DESC",
                (signal_id,),
            )
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()


class GuardrailRepository:
    """Repository for deterministic guardrail evaluation persistence."""

    @staticmethod
    def create_or_update_evaluation(
        evaluation_id: str,
        action_id: str,
        merchant_id: str,
        overall_status: str,
        passed: bool,
        checks: List[Dict[str, Any]],
        passed_checks: List[str],
        failed_checks: List[str],
        warnings: List[str],
        modifications: Dict[str, Any],
        original_values: Dict[str, Any],
        modified_values: Dict[str, Any],
        notes: str = "",
        evaluated_at: Optional[str] = None,
        is_deterministic: bool = True,
    ) -> Dict[str, Any]:
        """Idempotently saves or updates a deterministic guardrail evaluation."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now_iso = evaluated_at or datetime.now(timezone.utc).isoformat()
            checks_json = json.dumps(checks)
            passed_checks_json = json.dumps(passed_checks)
            failed_checks_json = json.dumps(failed_checks)
            warnings_json = json.dumps(warnings)
            modifications_json = json.dumps(modifications)
            orig_json = json.dumps(original_values)
            mod_json = json.dumps(modified_values)
            passed_int = 1 if passed else 0
            det_int = 1 if is_deterministic else 0

            # Ensure parent merchant exists to satisfy foreign key constraint
            cursor.execute("SELECT id FROM merchants WHERE id = ?", (merchant_id,))
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO merchants (
                        id, name, category, location, minimum_margin,
                        daily_budget, max_discount, max_campaign_frequency,
                        autonomy_level, created_at
                    ) VALUES (?, 'Simulated Merchant', 'Retail', 'Delhi NCR', 0.10, 12000.0, 100.0, 3, 'APPROVAL_REQUIRED', ?)
                    """,
                    (merchant_id, now_iso),
                )

            # Ensure parent action exists to satisfy foreign key constraint
            cursor.execute("SELECT id FROM actions WHERE id = ?", (action_id,))
            if not cursor.fetchone():
                dummy_sig = f"sig-{action_id[:8]}"
                cursor.execute("SELECT id FROM signals WHERE id = ?", (dummy_sig,))
                if not cursor.fetchone():
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO signals (
                            id, merchant_id, signal_type, severity, metric_name,
                            baseline_value, observed_value, change_percentage,
                            decline_percentage, description, detected_at, status, context_data
                        ) VALUES (?, ?, 'GENERAL_ANOMALY', 'MEDIUM', 'metric', 0.0, 0.0, 0.0, 0.0, 'Signal', ?, 'ACTIVE', '{}')
                        """,
                        (dummy_sig, merchant_id, now_iso),
                    )
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO actions (
                        id, merchant_id, signal_id, action_type, parameters, status, created_at
                    ) VALUES (?, ?, ?, 'OFFER_CAMPAIGN', '{}', 'PROPOSED', ?)
                    """,
                    (action_id, merchant_id, dummy_sig, now_iso),
                )

            # Check if evaluation already exists for this action_id
            cursor.execute(
                "SELECT id FROM guardrail_evaluations WHERE action_id = ? LIMIT 1",
                (action_id,),
            )
            existing = cursor.fetchone()

            if existing:
                eval_id = existing["id"]
                cursor.execute(
                    """
                    UPDATE guardrail_evaluations SET
                        merchant_id = ?,
                        overall_status = ?,
                        passed = ?,
                        checks = ?,
                        passed_checks = ?,
                        failed_checks = ?,
                        warnings = ?,
                        modifications = ?,
                        original_values = ?,
                        modified_values = ?,
                        notes = ?,
                        evaluated_at = ?,
                        is_deterministic = ?,
                        rule_name = ?,
                        reason = ?
                    WHERE id = ?
                    """,
                    (
                        merchant_id,
                        overall_status,
                        passed_int,
                        checks_json,
                        passed_checks_json,
                        failed_checks_json,
                        warnings_json,
                        modifications_json,
                        orig_json,
                        mod_json,
                        notes,
                        now_iso,
                        det_int,
                        "ALL_GUARDRAILS",
                        notes,
                        eval_id,
                    ),
                )
                conn.commit()
                cursor.execute("SELECT * FROM guardrail_evaluations WHERE id = ?", (eval_id,))
                return dict(cursor.fetchone())
            else:
                eval_id = evaluation_id or f"grd-{uuid.uuid4().hex[:10]}"
                cursor.execute(
                    """
                    INSERT INTO guardrail_evaluations (
                        id, action_id, merchant_id, overall_status, passed,
                        checks, passed_checks, failed_checks, warnings,
                        modifications, original_values, modified_values,
                        notes, evaluated_at, is_deterministic,
                        rule_name, actual_value, required_value, reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        eval_id,
                        action_id,
                        merchant_id,
                        overall_status,
                        passed_int,
                        checks_json,
                        passed_checks_json,
                        failed_checks_json,
                        warnings_json,
                        modifications_json,
                        orig_json,
                        mod_json,
                        notes,
                        now_iso,
                        det_int,
                        "ALL_GUARDRAILS",
                        "",
                        "",
                        notes,
                    ),
                )
                conn.commit()
                cursor.execute("SELECT * FROM guardrail_evaluations WHERE id = ?", (eval_id,))
                return dict(cursor.fetchone())
        finally:
            conn.close()

    @staticmethod
    def get_evaluation(evaluation_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM guardrail_evaluations WHERE id = ?", (evaluation_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    get_guardrail_evaluation = get_evaluation

    @staticmethod
    def get_evaluation_by_action(action_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM guardrail_evaluations WHERE action_id = ? ORDER BY evaluated_at DESC LIMIT 1",
                (action_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    get_by_action = get_evaluation_by_action


class DecisionRepository:
    """Repository for authoritative decisions and merchant sign-off records."""

    @staticmethod
    def create_or_update_decision(
        action_id: str,
        evaluation_id: str,
        decision_state: str,
        merchant_id: str = "MID-DEMO-98234",
        reason: str = "",
        triggered_rules: Optional[List[str]] = None,
        modifications: Optional[Dict[str, Any]] = None,
        approval_required: bool = True,
        approval_status: str = "PENDING",
        proposal_hash: str = "",
        evaluation_hash: str = "",
        is_deterministic: bool = True,
        approved_action: Optional[Dict[str, Any]] = None,
        requires_human_review: bool = False,
        is_execution_eligible: bool = False,
        decided_at: Optional[str] = None,
        decided_by: str = "MITRA_DECISION_ENGINE",
        decision_id: Optional[str] = None,
        approved_at: Optional[str] = None,
        rejected_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now_iso = decided_at or datetime.now(timezone.utc).isoformat()
            rules_json = json.dumps(triggered_rules or [])
            mod_json = json.dumps(modifications or {})
            appr_act_json = json.dumps(approved_action or {})
            appr_req_int = 1 if approval_required else 0
            is_det_int = 1 if is_deterministic else 0
            req_rev_int = 1 if requires_human_review else 0
            is_exec_int = 1 if is_execution_eligible else 0

            # Ensure parent merchant exists
            cursor.execute("SELECT id FROM merchants WHERE id = ?", (merchant_id,))
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO merchants (
                        id, name, category, location, minimum_margin,
                        daily_budget, max_discount, max_campaign_frequency,
                        autonomy_level, created_at
                    ) VALUES (?, 'Simulated Merchant', 'Retail', 'Delhi NCR', 0.10, 12000.0, 100.0, 3, 'APPROVAL_REQUIRED', ?)
                    """,
                    (merchant_id, now_iso),
                )

            # Ensure parent action exists
            cursor.execute("SELECT id FROM actions WHERE id = ?", (action_id,))
            if not cursor.fetchone():
                dummy_sig = f"sig-{action_id[:8]}"
                cursor.execute("SELECT id FROM signals WHERE id = ?", (dummy_sig,))
                if not cursor.fetchone():
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO signals (
                            id, merchant_id, signal_type, severity, metric_name,
                            baseline_value, observed_value, change_percentage,
                            decline_percentage, description, detected_at, status, context_data
                        ) VALUES (?, ?, 'GENERAL_ANOMALY', 'MEDIUM', 'metric', 0.0, 0.0, 0.0, 0.0, 'Signal', ?, 'ACTIVE', '{}')
                        """,
                        (dummy_sig, merchant_id, now_iso),
                    )
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO actions (
                        id, merchant_id, signal_id, action_type, parameters, status, created_at
                    ) VALUES (?, ?, ?, 'OFFER_CAMPAIGN', '{}', 'PROPOSED', ?)
                    """,
                    (action_id, merchant_id, dummy_sig, now_iso),
                )

            # Check if decision exists for this action_id
            cursor.execute(
                "SELECT id FROM decisions WHERE action_id = ? ORDER BY decided_at DESC LIMIT 1",
                (action_id,),
            )
            existing = cursor.fetchone()

            if existing:
                dec_id = existing["id"]
                cursor.execute(
                    """
                    UPDATE decisions SET
                        evaluation_id = ?,
                        merchant_id = ?,
                        decision_state = ?,
                        state = ?,
                        reason = ?,
                        rationale = ?,
                        triggered_rules = ?,
                        modifications = ?,
                        approval_required = ?,
                        approval_status = ?,
                        decided_at = ?,
                        decided_by = ?,
                        approved_at = ?,
                        rejected_at = ?,
                        proposal_hash = ?,
                        evaluation_hash = ?,
                        is_deterministic = ?,
                        approved_action = ?,
                        requires_human_review = ?,
                        is_execution_eligible = ?
                    WHERE id = ?
                    """,
                    (
                        evaluation_id,
                        merchant_id,
                        decision_state,
                        decision_state,
                        reason,
                        reason,
                        rules_json,
                        mod_json,
                        appr_req_int,
                        approval_status,
                        now_iso,
                        decided_by,
                        approved_at,
                        rejected_at,
                        proposal_hash,
                        evaluation_hash,
                        is_det_int,
                        appr_act_json,
                        req_rev_int,
                        is_exec_int,
                        dec_id,
                    ),
                )
                conn.commit()
                cursor.execute("SELECT * FROM decisions WHERE id = ?", (dec_id,))
                return dict(cursor.fetchone())
            else:
                dec_id = decision_id or f"dec-{uuid.uuid4().hex[:10]}"
                cursor.execute(
                    """
                    INSERT INTO decisions (
                        id, action_id, evaluation_id, merchant_id, decision_state,
                        state, reason, rationale, triggered_rules, modifications,
                        approval_required, approval_status, decided_at, decided_by,
                        approved_at, rejected_at, proposal_hash, evaluation_hash,
                        is_deterministic, approved_action, requires_human_review,
                        is_execution_eligible, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        dec_id,
                        action_id,
                        evaluation_id,
                        merchant_id,
                        decision_state,
                        decision_state,
                        reason,
                        reason,
                        rules_json,
                        mod_json,
                        appr_req_int,
                        approval_status,
                        now_iso,
                        decided_by,
                        approved_at,
                        rejected_at,
                        proposal_hash,
                        evaluation_hash,
                        is_det_int,
                        appr_act_json,
                        req_rev_int,
                        is_exec_int,
                        now_iso,
                    ),
                )
                conn.commit()
                cursor.execute("SELECT * FROM decisions WHERE id = ?", (dec_id,))
                return dict(cursor.fetchone())
        finally:
            conn.close()

    @staticmethod
    def get_decision(decision_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_decision_by_action(action_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM decisions WHERE action_id = ? ORDER BY decided_at DESC LIMIT 1",
                (action_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def approve_decision(decision_id: str, approver: str = "Merchant") -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now_iso = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                """
                UPDATE decisions SET
                    approval_status = 'APPROVED',
                    approved_at = ?,
                    decided_by = ?,
                    is_execution_eligible = 1
                WHERE id = ?
                """,
                (now_iso, f"Merchant ({approver})", decision_id),
            )
            conn.commit()
            cursor.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def auto_approve_decision(decision_id: str, reason: str = "Approved by deterministic autonomy policy") -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now_iso = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                """
                UPDATE decisions SET
                    approval_status = 'APPROVED',
                    approved_at = ?,
                    decided_by = 'AUTONOMY_POLICY',
                    is_execution_eligible = 1
                WHERE id = ?
                """,
                (now_iso, decision_id),
            )
            conn.commit()
            cursor.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def reject_decision(decision_id: str, reason: str = "Rejected by merchant") -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now_iso = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                """
                UPDATE decisions SET
                    approval_status = 'REJECTED',
                    rejected_at = ?,
                    reason = CASE WHEN reason = '' THEN ? ELSE reason || ' | Rejection: ' || ? END,
                    is_execution_eligible = 0
                WHERE id = ?
                """,
                (now_iso, reason, reason, decision_id),
            )
            conn.commit()
            cursor.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


class ExecutionRepository:
    """Repository for simulated execution records and idempotency tracking."""

    @staticmethod
    def _row_to_execution(row: Any) -> Dict[str, Any]:
        d = dict(row)
        for field in ("approved_action", "result", "output"):
            if field in d and isinstance(d[field], str):
                try:
                    d[field] = json.loads(d[field])
                except Exception:
                    d[field] = {}
        return d

    @staticmethod
    def create_execution(
        execution_id: str,
        decision_id: str,
        action_id: str,
        merchant_id: str,
        action_type: str = "OFFER_CAMPAIGN",
        execution_state: str = "EXECUTING",
        execution_mode: str = "SIMULATION",
        simulated: bool = True,
        approved_action: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        executed_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now_iso = executed_at or datetime.now(timezone.utc).isoformat()
            approved_action_json = json.dumps(approved_action or {})
            result_json = json.dumps(result or {})

            # Ensure decision exists for foreign key constraint in test scenarios
            cursor.execute("SELECT id FROM decisions WHERE id = ?", (decision_id,))
            if not cursor.fetchone():
                act_fk = action_id or f"act-{decision_id}"
                cursor.execute("SELECT id FROM actions WHERE id = ?", (act_fk,))
                if not cursor.fetchone():
                    dummy_sig = f"sig-{decision_id}"
                    cursor.execute("SELECT id FROM signals WHERE id = ?", (dummy_sig,))
                    if not cursor.fetchone():
                        cursor.execute(
                            "INSERT INTO signals (id, merchant_id, signal_type, severity, metric_name, baseline_value, observed_value, change_percentage, description, status, detected_at) "
                            "VALUES (?, ?, 'TEST', 'LOW', 'test', 0, 0, 0, 'dummy', 'NEW', ?)",
                            (dummy_sig, merchant_id, now_iso),
                        )
                    cursor.execute(
                        """
                        INSERT INTO actions (
                            id, merchant_id, signal_id, action_type, parameters, status, created_at
                        ) VALUES (?, ?, ?, ?, '{}', 'PROPOSED', ?)
                        """,
                        (act_fk, merchant_id, dummy_sig, action_type, now_iso),
                    )
                cursor.execute(
                    """
                    INSERT INTO decisions (
                        id, action_id, merchant_id, decision_state, state, reason, rationale,
                        approval_required, approval_status, is_execution_eligible, created_at
                    ) VALUES (?, ?, ?, 'PASS', 'PASS', 'Test decision', 'Test decision', 0, 'APPROVED', 1, ?)
                    """,
                    (decision_id, act_fk, merchant_id, now_iso),
                )

            cursor.execute(
                """
                INSERT INTO executions (
                    id, decision_id, action_id, merchant_id, action_type,
                    execution_state, execution_mode, simulated,
                    approved_action, result, error, status, output, executed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    execution_id,
                    decision_id,
                    action_id,
                    merchant_id,
                    action_type,
                    execution_state,
                    execution_mode,
                    1 if simulated else 0,
                    approved_action_json,
                    result_json,
                    error,
                    execution_state,
                    result_json,
                    now_iso,
                ),
            )
            conn.commit()
            cursor.execute("SELECT * FROM executions WHERE id = ?", (execution_id,))
            row = cursor.fetchone()
            return ExecutionRepository._row_to_execution(row)
        finally:
            conn.close()

    @staticmethod
    def get_execution(execution_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM executions WHERE id = ?", (execution_id,))
            row = cursor.fetchone()
            return ExecutionRepository._row_to_execution(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_execution_by_decision(decision_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM executions WHERE decision_id = ? ORDER BY executed_at DESC LIMIT 1",
                (decision_id,),
            )
            row = cursor.fetchone()
            return ExecutionRepository._row_to_execution(row) if row else None
        finally:
            conn.close()

    get_by_decision = get_execution_by_decision

    @staticmethod
    def get_executions_by_merchant(merchant_id: str = "MID-DEMO-98234", limit: int = 20) -> List[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM executions WHERE merchant_id = ? ORDER BY executed_at DESC LIMIT 100",
                (merchant_id,),
            )
            rows = cursor.fetchall()
            return [ExecutionRepository._row_to_execution(r) for r in rows][:limit]
        finally:
            conn.close()

    @staticmethod
    def mark_executing(execution_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE executions SET execution_state = 'EXECUTING', status = 'EXECUTING' WHERE id = ?",
                (execution_id,),
            )
            conn.commit()
            cursor.execute("SELECT * FROM executions WHERE id = ?", (execution_id,))
            row = cursor.fetchone()
            return ExecutionRepository._row_to_execution(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def mark_completed(execution_id: str, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            result_json = json.dumps(result)
            cursor.execute(
                """
                UPDATE executions SET
                    execution_state = 'COMPLETED',
                    status = 'COMPLETED',
                    result = ?,
                    output = ?
                WHERE id = ?
                """,
                (result_json, result_json, execution_id),
            )
            conn.commit()
            cursor.execute("SELECT * FROM executions WHERE id = ?", (execution_id,))
            row = cursor.fetchone()
            return ExecutionRepository._row_to_execution(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def mark_failed(execution_id: str, error: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE executions SET
                    execution_state = 'FAILED',
                    status = 'FAILED',
                    error = ?
                WHERE id = ?
                """,
                (error, execution_id),
            )
            conn.commit()
            cursor.execute("SELECT * FROM executions WHERE id = ?", (execution_id,))
            row = cursor.fetchone()
            return ExecutionRepository._row_to_execution(row) if row else None
        finally:
            conn.close()


class OutcomeRepository:
    """Repository for post-execution simulated outcome monitoring and impact records."""

    @staticmethod
    def _row_to_outcome(row: Any) -> Dict[str, Any]:
        if not row:
            return {}
        d = dict(row)
        for json_col in ("baseline_window", "measurement_window", "baseline_metrics", "post_action_metrics", "metric_changes"):
            val = d.get(json_col)
            if isinstance(val, str):
                try:
                    d[json_col] = json.loads(val)
                except Exception:
                    d[json_col] = {}
            elif val is None:
                d[json_col] = {}
        # Ensure outcome_id alias
        if "id" in d and "outcome_id" not in d:
            d["outcome_id"] = d["id"]
        # Ensure status alias
        if "outcome_status" in d and "status" not in d:
            d["status"] = d["outcome_status"]
        elif "status" in d and "outcome_status" not in d:
            d["outcome_status"] = d["status"]
        d["simulated"] = bool(d.get("simulated", 1))
        return d

    @staticmethod
    def create_outcome(
        execution_id: str,
        decision_id: Optional[str] = None,
        action_id: Optional[str] = None,
        merchant_id: str = "MID-DEMO-98234",
        baseline_window: Optional[Dict[str, Any]] = None,
        measurement_window: Optional[Dict[str, Any]] = None,
        baseline_metrics: Optional[Dict[str, Any]] = None,
        post_action_metrics: Optional[Dict[str, Any]] = None,
        metric_changes: Optional[Dict[str, Any]] = None,
        outcome_status: str = "MEASURED",
        measurement_mode: str = "SIMULATION",
        simulated: bool = True,
        disclaimer: str = "SIMULATED - PROTOTYPE - NOT REAL PAYTM PERFORMANCE",
        measured_at: Optional[str] = None,
        outcome_id: Optional[str] = None,
        metric_name: Optional[str] = None,
        baseline_value: Optional[float] = None,
        observed_value: Optional[float] = None,
        delta_percent: Optional[float] = None,
    ) -> Dict[str, Any]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            # Check for existing outcome by execution_id (Idempotency)
            cursor.execute("SELECT * FROM outcomes WHERE execution_id = ? ORDER BY measured_at DESC LIMIT 1", (execution_id,))
            existing = cursor.fetchone()
            if existing:
                return OutcomeRepository._row_to_outcome(existing)

            oid = outcome_id or f"out-{uuid.uuid4().hex[:10]}"
            now_iso = measured_at or datetime.now(timezone.utc).isoformat()
            bw_json = json.dumps(baseline_window or {})
            mw_json = json.dumps(measurement_window or {})
            bm_json = json.dumps(baseline_metrics or {})
            pm_json = json.dumps(post_action_metrics or {})
            mc_json = json.dumps(metric_changes or {})
            sim_int = 1 if simulated else 0

            # Compatibility values
            m_name = metric_name or "evening_orders"
            b_val = baseline_value if baseline_value is not None else (baseline_metrics.get("evening_orders", 0.0) if baseline_metrics else 0.0)
            o_val = observed_value if observed_value is not None else (post_action_metrics.get("evening_orders", 0.0) if post_action_metrics else 0.0)
            d_pct = delta_percent if delta_percent is not None else (metric_changes.get("evening_orders", {}).get("percentage_change", 0.0) if metric_changes else 0.0)

            cursor.execute(
                """
                INSERT INTO outcomes (
                    id, execution_id, decision_id, action_id, merchant_id,
                    baseline_window, measurement_window, baseline_metrics,
                    post_action_metrics, metric_changes, outcome_status, status,
                    measurement_mode, simulated, disclaimer, measured_at,
                    metric_name, baseline_value, observed_value, delta_percent, verified_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    oid, execution_id, decision_id, action_id, merchant_id,
                    bw_json, mw_json, bm_json, pm_json, mc_json,
                    outcome_status, outcome_status, measurement_mode, sim_int, disclaimer,
                    now_iso, m_name, b_val, o_val, d_pct, now_iso,
                ),
            )
            conn.commit()
            cursor.execute("SELECT * FROM outcomes WHERE id = ?", (oid,))
            row = cursor.fetchone()
            return OutcomeRepository._row_to_outcome(row)
        finally:
            conn.close()

    @staticmethod
    def get_outcome(outcome_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM outcomes WHERE id = ?", (outcome_id,))
            row = cursor.fetchone()
            return OutcomeRepository._row_to_outcome(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_outcome_by_execution(execution_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM outcomes WHERE execution_id = ? ORDER BY measured_at DESC LIMIT 1", (execution_id,))
            row = cursor.fetchone()
            return OutcomeRepository._row_to_outcome(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_outcomes_by_merchant(merchant_id: str = "MID-DEMO-98234", limit: int = 20) -> List[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM outcomes WHERE merchant_id = ? ORDER BY measured_at DESC LIMIT 100", (merchant_id,))
            rows = cursor.fetchall()
            return [OutcomeRepository._row_to_outcome(r) for r in rows][:limit]
        finally:
            conn.close()

    @staticmethod
    def update_outcome(outcome_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            updates = []
            values = []
            for k, v in kwargs.items():
                if k in ("baseline_window", "measurement_window", "baseline_metrics", "post_action_metrics", "metric_changes"):
                    updates.append(f"{k} = ?")
                    values.append(json.dumps(v) if isinstance(v, (dict, list)) else str(v))
                else:
                    updates.append(f"{k} = ?")
                    values.append(v)
            if not updates:
                return OutcomeRepository.get_outcome(outcome_id)
            values.append(outcome_id)
            cursor.execute(f"UPDATE outcomes SET {', '.join(updates)} WHERE id = ?", tuple(values))
            conn.commit()
            cursor.execute("SELECT * FROM outcomes WHERE id = ?", (outcome_id,))
            row = cursor.fetchone()
            return OutcomeRepository._row_to_outcome(row) if row else None
        finally:
            conn.close()


class BusinessImpactRepository:
    """Repository for post-outcome simulated business impact and ROI analysis records."""

    @staticmethod
    def _row_to_impact(row: Any) -> Dict[str, Any]:
        if not row:
            return {}
        d = dict(row)
        if "id" in d and "impact_id" not in d:
            d["impact_id"] = d["id"]
        if "impact_status" in d and "status" not in d:
            d["status"] = d["impact_status"]
        elif "status" in d and "impact_status" not in d:
            d["impact_status"] = d["status"]
        d["simulated"] = bool(d.get("simulated", 1))
        # Ensure float conversions where appropriate
        for fld in (
            "baseline_revenue", "post_action_revenue", "incremental_revenue",
            "baseline_orders", "post_action_orders", "incremental_orders", "orders_change",
            "baseline_evening_orders", "post_action_evening_orders", "evening_orders_change",
            "campaign_cost", "gross_profit_impact", "roi", "roi_percentage",
            "cost_per_incremental_order", "revenue_per_campaign_rupee"
        ):
            if fld in d and d[fld] is not None:
                try:
                    d[fld] = float(d[fld])
                except (ValueError, TypeError):
                    pass
        return d

    @staticmethod
    def create_business_impact(
        outcome_id: str,
        execution_id: str,
        decision_id: Optional[str] = None,
        action_id: Optional[str] = None,
        merchant_id: str = "MID-DEMO-98234",
        impact_status: str = "CALCULATED",
        baseline_revenue: float = 0.0,
        post_action_revenue: float = 0.0,
        incremental_revenue: float = 0.0,
        baseline_orders: float = 0.0,
        post_action_orders: float = 0.0,
        incremental_orders: float = 0.0,
        orders_change: float = 0.0,
        baseline_evening_orders: float = 0.0,
        post_action_evening_orders: float = 0.0,
        evening_orders_change: float = 0.0,
        campaign_cost: float = 0.0,
        gross_profit_impact: Optional[float] = None,
        roi: Optional[float] = None,
        roi_percentage: Optional[float] = None,
        cost_per_incremental_order: Optional[float] = None,
        revenue_per_campaign_rupee: Optional[float] = None,
        impact_classification: str = "POSITIVE",
        measurement_mode: str = "SIMULATION",
        simulated: bool = True,
        disclaimer: str = "SIMULATED - PROTOTYPE - NOT REAL PAYTM PERFORMANCE",
        calculated_at: Optional[str] = None,
        impact_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            # Idempotency check: exactly one authoritative business impact per outcome
            cursor.execute("SELECT * FROM business_impacts WHERE outcome_id = ? LIMIT 1", (outcome_id,))
            existing = cursor.fetchone()
            if existing:
                return BusinessImpactRepository._row_to_impact(existing)

            iid = impact_id or f"imp-{uuid.uuid4().hex[:10]}"
            now_iso = calculated_at or datetime.now(timezone.utc).isoformat()
            sim_int = 1 if simulated else 0

            cursor.execute(
                """
                INSERT INTO business_impacts (
                    id, outcome_id, execution_id, decision_id, action_id, merchant_id,
                    impact_status, status, baseline_revenue, post_action_revenue, incremental_revenue,
                    baseline_orders, post_action_orders, incremental_orders, orders_change,
                    baseline_evening_orders, post_action_evening_orders, evening_orders_change,
                    campaign_cost, gross_profit_impact, roi, roi_percentage,
                    cost_per_incremental_order, revenue_per_campaign_rupee,
                    impact_classification, measurement_mode, simulated, disclaimer, calculated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    iid, outcome_id, execution_id, decision_id, action_id, merchant_id,
                    impact_status, impact_status, baseline_revenue, post_action_revenue, incremental_revenue,
                    baseline_orders, post_action_orders, incremental_orders, orders_change,
                    baseline_evening_orders, post_action_evening_orders, evening_orders_change,
                    campaign_cost, gross_profit_impact, roi, roi_percentage,
                    cost_per_incremental_order, revenue_per_campaign_rupee,
                    impact_classification, measurement_mode, sim_int, disclaimer, now_iso,
                ),
            )
            conn.commit()
            cursor.execute("SELECT * FROM business_impacts WHERE id = ?", (iid,))
            row = cursor.fetchone()
            return BusinessImpactRepository._row_to_impact(row)
        finally:
            conn.close()

    @staticmethod
    def get_business_impact(impact_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM business_impacts WHERE id = ?", (impact_id,))
            row = cursor.fetchone()
            return BusinessImpactRepository._row_to_impact(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_by_outcome(outcome_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM business_impacts WHERE outcome_id = ? LIMIT 1", (outcome_id,))
            row = cursor.fetchone()
            return BusinessImpactRepository._row_to_impact(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_by_execution(execution_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM business_impacts WHERE execution_id = ? ORDER BY calculated_at DESC LIMIT 1",
                (execution_id,),
            )
            row = cursor.fetchone()
            return BusinessImpactRepository._row_to_impact(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_by_merchant(merchant_id: str = "MID-DEMO-98234", limit: int = 20) -> List[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM business_impacts WHERE merchant_id = ? ORDER BY calculated_at DESC LIMIT 100",
                (merchant_id,),
            )
            rows = cursor.fetchall()
            return [BusinessImpactRepository._row_to_impact(r) for r in rows][:limit]
        finally:
            conn.close()

    @staticmethod
    def update_business_impact(impact_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            updates = []
            values = []
            for k, v in kwargs.items():
                updates.append(f"{k} = ?")
                values.append(v)
            if not updates:
                return BusinessImpactRepository.get_business_impact(impact_id)
            values.append(impact_id)
            cursor.execute(f"UPDATE business_impacts SET {', '.join(updates)} WHERE id = ?", tuple(values))
            conn.commit()
            cursor.execute("SELECT * FROM business_impacts WHERE id = ?", (impact_id,))
            row = cursor.fetchone()
            return BusinessImpactRepository._row_to_impact(row) if row else None
        finally:
            conn.close()


class AuditRepository:
    """Repository for tamper-evident hash-chained audit ledger (Phase 11)."""

    @staticmethod
    def _row_to_event(row: Any) -> Dict[str, Any]:
        if not row:
            return {}
        d = dict(row)
        for json_col in ("input_payload", "output_payload"):
            val = d.get(json_col)
            if isinstance(val, str):
                try:
                    d[json_col] = json.loads(val)
                except Exception:
                    d[json_col] = {}
            elif val is None:
                d[json_col] = {}

        # Sync aliases
        if "id" in d and "event_id" not in d:
            d["event_id"] = d["id"]
        elif "event_id" in d and "id" not in d:
            d["id"] = d["event_id"]

        if "integrity_hash" in d and "event_hash" not in d:
            d["event_hash"] = d["integrity_hash"]
        elif "event_hash" in d and "integrity_hash" not in d:
            d["integrity_hash"] = d["event_hash"]

        if "action_description" in d and "description" not in d:
            d["description"] = d["action_description"]
        elif "description" in d and "action_description" not in d:
            d["action_description"] = d["description"]

        d["simulated"] = bool(d.get("simulated", 1))
        return d

    @staticmethod
    def get_latest_event(correlation_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Returns the most recent audit event, optionally filtered by workflow correlation ID."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            if correlation_id:
                cursor.execute(
                    "SELECT * FROM audit_events WHERE correlation_id = ? ORDER BY timestamp DESC, rowid DESC LIMIT 1",
                    (correlation_id,),
                )
            else:
                cursor.execute("SELECT * FROM audit_events ORDER BY timestamp DESC, rowid DESC LIMIT 1")
            row = cursor.fetchone()
            return AuditRepository._row_to_event(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def record_event(
        stage: str,
        actor: str,
        action_description: str,
        input_payload: Dict[str, Any],
        output_payload: Dict[str, Any],
        integrity_hash: str,
        previous_hash: Optional[str] = None,
        correlation_id: Optional[str] = None,
        event_type: str = "WORKFLOW_STEP",
        merchant_id: str = "MID-DEMO-98234",
        signal_id: Optional[str] = None,
        investigation_id: Optional[str] = None,
        action_id: Optional[str] = None,
        decision_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        outcome_id: Optional[str] = None,
        impact_id: Optional[str] = None,
        decision: Optional[str] = None,
        reason: Optional[str] = None,
        event_id: Optional[str] = None,
        timestamp: Optional[str] = None,
        simulated: bool = True,
    ) -> Dict[str, Any]:
        """Persists a new hash-chained audit event into SQLite."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            eid = event_id or f"aud-{uuid.uuid4().hex[:10]}"
            now_iso = timestamp or datetime.now(timezone.utc).isoformat()
            sim_int = 1 if simulated else 0

            # Determine previous hash if not explicitly provided
            prev_h = previous_hash
            if prev_h is None:
                if correlation_id:
                    cursor.execute(
                        "SELECT integrity_hash FROM audit_events WHERE correlation_id = ? ORDER BY timestamp DESC, rowid DESC LIMIT 1",
                        (correlation_id,),
                    )
                else:
                    cursor.execute("SELECT integrity_hash FROM audit_events ORDER BY timestamp DESC, rowid DESC LIMIT 1")
                last_row = cursor.fetchone()
                prev_h = last_row["integrity_hash"] if last_row else "GENESIS"

            from app.engines.audit_engine.engine import sanitize_payload
            clean_in = sanitize_payload(input_payload or {})
            clean_out = sanitize_payload(output_payload or {})
            in_json = json.dumps(clean_in, sort_keys=True, default=str)
            out_json = json.dumps(clean_out, sort_keys=True, default=str)

            cursor.execute(
                """
                INSERT INTO audit_events (
                    id, event_id, timestamp, stage, actor, event_type,
                    action_description, input_payload, output_payload,
                    decision, reason, previous_hash, integrity_hash,
                    correlation_id, merchant_id, signal_id, investigation_id,
                    action_id, decision_id, execution_id, outcome_id, impact_id, simulated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    eid, eid, now_iso, stage, actor, event_type,
                    action_description, in_json, out_json,
                    decision, reason, prev_h, integrity_hash,
                    correlation_id, merchant_id, signal_id, investigation_id,
                    action_id, decision_id, execution_id, outcome_id, impact_id, sim_int,
                ),
            )
            conn.commit()
            cursor.execute("SELECT * FROM audit_events WHERE id = ?", (eid,))
            row = cursor.fetchone()
            return AuditRepository._row_to_event(row)
        finally:
            conn.close()

    @staticmethod
    def get_event(event_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves an audit event by event ID or primary key."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audit_events WHERE id = ? OR event_id = ?", (event_id, event_id))
            row = cursor.fetchone()
            return AuditRepository._row_to_event(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_events(merchant_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves recent audit events for a merchant or all merchants if None."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            if merchant_id:
                cursor.execute(
                    "SELECT * FROM audit_events WHERE merchant_id = ? ORDER BY timestamp DESC, rowid DESC LIMIT ?",
                    (merchant_id, limit),
                )
            else:
                cursor.execute(
                    "SELECT * FROM audit_events ORDER BY timestamp DESC, rowid DESC LIMIT ?",
                    (limit,),
                )
            rows = cursor.fetchall()
            return [AuditRepository._row_to_event(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_events_by_correlation_id(correlation_id: str) -> List[Dict[str, Any]]:
        """Retrieves all audit events for a workflow correlation ID in chronological order."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM audit_events WHERE correlation_id = ? ORDER BY timestamp ASC, rowid ASC",
                (correlation_id,),
            )
            rows = cursor.fetchall()
            return [AuditRepository._row_to_event(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_events_by_entity(entity_type: str, entity_id: str) -> List[Dict[str, Any]]:
        """Retrieves audit events linked to a specific entity (signal, action, decision, etc.)."""
        allowed_cols = {
            "signal": "signal_id",
            "investigation": "investigation_id",
            "action": "action_id",
            "decision": "decision_id",
            "execution": "execution_id",
            "outcome": "outcome_id",
            "impact": "impact_id",
        }
        col = allowed_cols.get(entity_type.lower())
        if not col:
            return []

        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM audit_events WHERE {col} = ? ORDER BY timestamp ASC, rowid ASC",
                (entity_id,),
            )
            rows = cursor.fetchall()
            return [AuditRepository._row_to_event(r) for r in rows]
        finally:
            conn.close()


class AutonomyRepository:
    """Repository for controlled autonomy evaluations (Phase 12)."""

    @staticmethod
    def record_evaluation(
        evaluation_id: str,
        correlation_id: str,
        merchant_id: str,
        action_id: str,
        guardrail_evaluation_id: str,
        decision_id: str,
        autonomy_mode: str,
        guardrail_status: str,
        approval_required: bool,
        auto_approval_allowed: bool,
        auto_approval_reason: str,
        approval_source: str,
        actor_type: str,
        blocked: bool,
        escalated: bool,
        approved_action: Dict[str, Any],
        evaluated_risk: float,
        policy_threshold: float,
        policy_version: str = "1.0.0",
        passed_checks: Optional[List[str]] = None,
        failed_checks: Optional[List[str]] = None,
        simulation_mode: bool = True,
        evaluated_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now_iso = evaluated_at or datetime.now(timezone.utc).isoformat()
            appr_act_json = json.dumps(approved_action or {})
            passed_checks_json = json.dumps(passed_checks or [])
            failed_checks_json = json.dumps(failed_checks or [])

            cursor.execute(
                """
                INSERT INTO autonomy_evaluations (
                    id, correlation_id, merchant_id, action_id,
                    guardrail_evaluation_id, decision_id, autonomy_mode,
                    guardrail_status, approval_required, auto_approval_allowed,
                    auto_approval_reason, approval_source, actor_type,
                    blocked, escalated, approved_action, evaluated_risk,
                    policy_threshold, policy_version, passed_checks,
                    failed_checks, simulation_mode, evaluated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(action_id) DO UPDATE SET
                    autonomy_mode = excluded.autonomy_mode,
                    guardrail_status = excluded.guardrail_status,
                    approval_required = excluded.approval_required,
                    auto_approval_allowed = excluded.auto_approval_allowed,
                    auto_approval_reason = excluded.auto_approval_reason,
                    approval_source = excluded.approval_source,
                    actor_type = excluded.actor_type,
                    blocked = excluded.blocked,
                    escalated = excluded.escalated,
                    approved_action = excluded.approved_action,
                    evaluated_risk = excluded.evaluated_risk,
                    policy_threshold = excluded.policy_threshold,
                    policy_version = excluded.policy_version,
                    passed_checks = excluded.passed_checks,
                    failed_checks = excluded.failed_checks,
                    evaluated_at = excluded.evaluated_at
                """,
                (
                    evaluation_id,
                    correlation_id,
                    merchant_id,
                    action_id,
                    guardrail_evaluation_id,
                    decision_id,
                    autonomy_mode,
                    guardrail_status,
                    1 if approval_required else 0,
                    1 if auto_approval_allowed else 0,
                    auto_approval_reason,
                    approval_source,
                    actor_type,
                    1 if blocked else 0,
                    1 if escalated else 0,
                    appr_act_json,
                    evaluated_risk,
                    policy_threshold,
                    policy_version,
                    passed_checks_json,
                    failed_checks_json,
                    1 if simulation_mode else 0,
                    now_iso,
                ),
            )
            conn.commit()
            cursor.execute("SELECT * FROM autonomy_evaluations WHERE action_id = ?", (action_id,))
            row = cursor.fetchone()
            return AutonomyRepository._row_to_dict(row)
        finally:
            conn.close()

    @staticmethod
    def get_evaluation(evaluation_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM autonomy_evaluations WHERE id = ?", (evaluation_id,))
            row = cursor.fetchone()
            return AutonomyRepository._row_to_dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_by_action(action_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM autonomy_evaluations WHERE action_id = ?", (action_id,))
            row = cursor.fetchone()
            return AutonomyRepository._row_to_dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_by_decision(decision_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM autonomy_evaluations WHERE decision_id = ?", (decision_id,))
            row = cursor.fetchone()
            return AutonomyRepository._row_to_dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_by_correlation_id(correlation_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM autonomy_evaluations WHERE correlation_id = ? ORDER BY evaluated_at DESC LIMIT 1",
                (correlation_id,),
            )
            row = cursor.fetchone()
            return AutonomyRepository._row_to_dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def _row_to_dict(row: Any) -> Dict[str, Any]:
        if not row:
            return {}
        d = dict(row)
        d["approval_required"] = bool(d.get("approval_required", 1))
        d["auto_approval_allowed"] = bool(d.get("auto_approval_allowed", 0))
        d["blocked"] = bool(d.get("blocked", 0))
        d["escalated"] = bool(d.get("escalated", 0))
        d["simulation_mode"] = bool(d.get("simulation_mode", 1))
        for json_field in ("approved_action", "passed_checks", "failed_checks"):
            if isinstance(d.get(json_field), str):
                try:
                    d[json_field] = json.loads(d[json_field])
                except Exception:
                    pass
        d["autonomy_evaluation_id"] = d.get("id")
        return d






