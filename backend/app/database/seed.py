"""Deterministic Seed Data Generator for MITRA Digital Twin.

Provides realistic synthetic data for:
- Merchant: Sharma Kirana & General Store (MID-DEMO-98234)
- 520 customers across segments
- 1,284 orders totaling ~₹4.82L GMV
- Anomaly scenario: Evening orders dropped from baseline 410 to 291 (-29.0%)
- Root cause context: Repeat-customer conversion dropped from 18.2% to 14.8%
- Previous campaign: "Evening Rush Cashback" (Expired)
"""

from datetime import datetime, timedelta, timezone
import json
import random
from typing import Any, Dict, List, Tuple
from app.core.logging import logger
from app.database.connection import get_connection, init_db

# Constants
MERCHANT_ID = "MID-DEMO-98234"
MERCHANT_NAME = "Sharma Kirana & General Store"
CATEGORY = "Retail / Grocery"
LOCATION = "Delhi NCR"
MINIMUM_MARGIN = 0.10
DAILY_BUDGET = 12000.0
MAX_DISCOUNT = 100.0
MAX_CAMPAIGN_FREQUENCY = 3
AUTONOMY_LEVEL = "APPROVAL_REQUIRED"

# Reference timestamp (UTC)
NOW = datetime(2026, 9, 17, 21, 0, 0, tzinfo=timezone.utc)


def seed_digital_twin(preserve_audit: bool = False) -> Dict[str, Any]:
    """Generates deterministic digital-twin simulation data."""
    logger.info("Initializing database schema...")
    init_db()

    conn = get_connection()
    cursor = conn.cursor()

    # Clear previous demo data
    logger.info("Purging old demo data for %s (preserve_audit=%s)...", MERCHANT_ID, preserve_audit)
    if not preserve_audit:
        cursor.execute("DELETE FROM audit_events")
    cursor.execute("DELETE FROM autonomy_evaluations")
    cursor.execute("DELETE FROM business_impacts")
    cursor.execute("DELETE FROM outcomes")
    cursor.execute("DELETE FROM executions")
    cursor.execute("DELETE FROM decisions")
    cursor.execute("DELETE FROM guardrail_evaluations")
    cursor.execute("DELETE FROM actions")
    cursor.execute("DELETE FROM investigations")
    cursor.execute("DELETE FROM signals")
    cursor.execute("DELETE FROM business_metrics")
    cursor.execute("DELETE FROM campaigns")
    cursor.execute("DELETE FROM transactions")
    cursor.execute("DELETE FROM customers")
    cursor.execute("DELETE FROM merchants")

    # 1. Insert Merchant
    logger.info("Seeding primary merchant %s...", MERCHANT_NAME)
    cursor.execute(
        """
        INSERT INTO merchants (
            id, name, category, location, minimum_margin, daily_budget,
            max_discount, max_campaign_frequency, autonomy_level, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            MERCHANT_ID,
            MERCHANT_NAME,
            CATEGORY,
            LOCATION,
            MINIMUM_MARGIN,
            DAILY_BUDGET,
            MAX_DISCOUNT,
            MAX_CAMPAIGN_FREQUENCY,
            AUTONOMY_LEVEL,
            (NOW - timedelta(days=90)).isoformat(),
        ),
    )

    # 2. Seed 520 Customers
    # Segment targets:
    # 216 repeat_customer
    # 240 regular
    # 40 inactive (30 with engagement >= 0.2)
    # 24 new_customer
    # Target re-engagement campaign size: 216 + 240 + 30 = exactly 486 customers!
    rng = random.Random(42)
    customers_data = []

    cust_id_counter = 1

    # Repeat customers (216)
    for _ in range(216):
        c_id = f"CUST-REP-{cust_id_counter:04d}"
        orders = rng.randint(5, 24)
        last_order = NOW - timedelta(days=rng.uniform(0.5, 6))
        eng = round(rng.uniform(0.70, 0.95), 2)
        customers_data.append((c_id, MERCHANT_ID, "repeat_customer", orders, last_order.isoformat(), eng, 1, (NOW - timedelta(days=60)).isoformat()))
        cust_id_counter += 1

    # Regular customers (240)
    for _ in range(240):
        c_id = f"CUST-REG-{cust_id_counter:04d}"
        orders = rng.randint(2, 4)
        last_order = NOW - timedelta(days=rng.uniform(1, 14))
        eng = round(rng.uniform(0.45, 0.70), 2)
        customers_data.append((c_id, MERCHANT_ID, "regular", orders, last_order.isoformat(), eng, 1, (NOW - timedelta(days=45)).isoformat()))
        cust_id_counter += 1

    # Inactive customers (40) -> 30 engaged (eng >= 0.2), 10 unengaged (eng < 0.2)
    for i in range(40):
        c_id = f"CUST-INA-{cust_id_counter:04d}"
        orders = rng.randint(1, 3)
        last_order = NOW - timedelta(days=rng.uniform(30, 75))
        eng = round(rng.uniform(0.25, 0.40), 2) if i < 30 else round(rng.uniform(0.05, 0.15), 2)
        customers_data.append((c_id, MERCHANT_ID, "inactive", orders, last_order.isoformat(), eng, 3, (NOW - timedelta(days=80)).isoformat()))
        cust_id_counter += 1

    # New customers (24)
    for _ in range(24):
        c_id = f"CUST-NEW-{cust_id_counter:04d}"
        orders = 1
        last_order = NOW - timedelta(days=rng.uniform(0.2, 5))
        eng = round(rng.uniform(0.30, 0.60), 2)
        customers_data.append((c_id, MERCHANT_ID, "new_customer", orders, last_order.isoformat(), eng, 0, (NOW - timedelta(days=5)).isoformat()))
        cust_id_counter += 1

    cursor.executemany(
        """
        INSERT INTO customers (
            id, merchant_id, segment, orders_count, last_order_at,
            engagement_score, notification_count, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        customers_data,
    )
    logger.info("Seeded %d customers.", len(customers_data))

    # 3. Seed Campaigns
    # Previous campaign: Evening Rush Cashback (Expired 3 days ago)
    campaigns_data = [
        (
            "CAMP-2026-EVN-01",
            MERCHANT_ID,
            "Evening Rush Cashback (Expired)",
            "CASHBACK_OFFER",
            50.0,
            10.0,
            6000.0,
            486,
            (NOW - timedelta(days=17)).isoformat(),
            (NOW - timedelta(days=3)).isoformat(),
            "EXPIRED",
        ),
        (
            "CAMP-2026-WKND-02",
            MERCHANT_ID,
            "Weekend Kirana Specials",
            "DISCOUNT_VOUCHER",
            30.0,
            5.0,
            3000.0,
            240,
            (NOW - timedelta(days=35)).isoformat(),
            (NOW - timedelta(days=28)).isoformat(),
            "EXPIRED",
        ),
    ]
    cursor.executemany(
        """
        INSERT INTO campaigns (
            id, merchant_id, name, campaign_type, discount_amount,
            discount_percent, budget, target_customer_count, started_at,
            ended_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        campaigns_data,
    )

    # 4. Generate 14-day Transactions
    # Target totals for evaluation window:
    # Total Orders: exactly 1,284
    # Total GMV: ~₹481,500 to ₹482,000 (~₹4.82L)
    # Evening Orders in evaluation window: exactly 291
    # Historical Evening Baseline: 410
    # Repeat-customer conversion: 18.2% historical -> 14.8% current
    repeat_customer_ids = [c[0] for c in customers_data if c[2] == "repeat_customer"]
    regular_customer_ids = [c[0] for c in customers_data if c[2] == "regular"]
    all_customer_ids = [c[0] for c in customers_data]

    transactions = []
    txn_id_counter = 1

    # Target counts breakdown:
    # 10 baseline days (Days -14 to -5): 780 orders (410 evening orders + 370 morning/afternoon)
    # 4 recent days (Days -4 to -1): 504 orders (291 evening orders + 213 morning/afternoon)
    # Total = 780 + 504 = 1,284 orders!
    
    # 4A. Baseline Period: Days -14 to -5 (10 days)
    # Total evening orders target = 410 (avg 41/day)
    # Total day/morning/afternoon orders = 370
    daily_evening_baseline = [40, 42, 41, 39, 43, 40, 42, 41, 40, 42]  # sum = 410
    daily_day_baseline = [36, 38, 37, 35, 39, 36, 38, 37, 36, 38]       # sum = 370

    for day_idx in range(10):
        day_date = NOW - timedelta(days=(13 - day_idx))

        # Day orders (9:00 AM to 4:59 PM)
        for _ in range(daily_day_baseline[day_idx]):
            hour = rng.choice([9, 10, 11, 12, 13, 14, 15, 16])
            minute = rng.randint(0, 59)
            ts = day_date.replace(hour=hour, minute=minute, second=rng.randint(0, 59))
            cust = rng.choice(all_customer_ids)
            amount = round(rng.gauss(375.0, 65.0), 2)
            channel = rng.choice(["SOUNDBOX_UPI", "SOUNDBOX_UPI", "QR_UPI", "CARD_MACHINE"])
            transactions.append((f"TXN-{txn_id_counter:06d}", MERCHANT_ID, cust, amount, "SALE", channel, ts.isoformat()))
            txn_id_counter += 1

        # Evening orders (5:00 PM to 8:59 PM) -> Historical active campaign period
        for _ in range(daily_evening_baseline[day_idx]):
            hour = rng.choice([17, 18, 19, 20])
            minute = rng.randint(0, 59)
            ts = day_date.replace(hour=hour, minute=minute, second=rng.randint(0, 59))
            # 18.2% repeat customer conversion during baseline
            if rng.random() < 0.182:
                cust = rng.choice(repeat_customer_ids)
            else:
                cust = rng.choice(regular_customer_ids)
            amount = round(rng.gauss(375.0, 60.0), 2)
            channel = rng.choice(["SOUNDBOX_UPI", "SOUNDBOX_UPI", "QR_UPI"])
            transactions.append((f"TXN-{txn_id_counter:06d}", MERCHANT_ID, cust, amount, "SALE", channel, ts.isoformat()))
            txn_id_counter += 1

    # 4B. Current Period: Days -3 to 0 (4 days) - AFTER EVENING CAMPAIGN EXPIRED
    # Evening orders target = exactly 291
    # Day orders target = 213
    # Total = 504 orders
    daily_evening_current = [72, 74, 71, 74]  # sum = 291
    daily_day_current = [53, 54, 52, 54]      # sum = 213

    for day_idx in range(4):
        day_date = NOW - timedelta(days=(3 - day_idx))

        # Day orders (Morning / Afternoon stable)
        for _ in range(daily_day_current[day_idx]):
            hour = rng.choice([9, 10, 11, 12, 13, 14, 15, 16])
            minute = rng.randint(0, 59)
            ts = day_date.replace(hour=hour, minute=minute, second=rng.randint(0, 59))
            cust = rng.choice(all_customer_ids)
            amount = round(rng.gauss(375.0, 65.0), 2)
            channel = rng.choice(["SOUNDBOX_UPI", "SOUNDBOX_UPI", "QR_UPI"])
            transactions.append((f"TXN-{txn_id_counter:06d}", MERCHANT_ID, cust, amount, "SALE", channel, ts.isoformat()))
            txn_id_counter += 1

        # Evening orders (Drop occurred: repeat conversion fell to 14.8%)
        for _ in range(daily_evening_current[day_idx]):
            hour = rng.choice([17, 18, 19, 20])
            minute = rng.randint(0, 59)
            ts = day_date.replace(hour=hour, minute=minute, second=rng.randint(0, 59))
            # 14.8% repeat conversion
            if rng.random() < 0.148:
                cust = rng.choice(repeat_customer_ids)
            else:
                cust = rng.choice(regular_customer_ids)
            amount = round(rng.gauss(375.0, 55.0), 2)
            channel = rng.choice(["SOUNDBOX_UPI", "SOUNDBOX_UPI", "QR_UPI"])
            transactions.append((f"TXN-{txn_id_counter:06d}", MERCHANT_ID, cust, amount, "SALE", channel, ts.isoformat()))
            txn_id_counter += 1

    # Adjust sum to exactly ~₹4.82L (₹481,850.00)
    total_amount = sum(t[3] for t in transactions)
    scale_factor = 481850.0 / total_amount
    calibrated_transactions = [
        (t[0], t[1], t[2], round(t[3] * scale_factor, 2), t[4], t[5], t[6])
        for t in transactions
    ]

    cursor.executemany(
        """
        INSERT INTO transactions (
            id, merchant_id, customer_id, amount, transaction_type,
            channel, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        calibrated_transactions,
    )
    logger.info("Seeded %d transactions totaling INR %.2f.", len(calibrated_transactions), sum(t[3] for t in calibrated_transactions))

    # 5. Seed Pre-Computed Business Metrics
    # Supporting the scenario:
    # Evening Orders Baseline: 410
    # Current Evening Orders: 291 (-29.02%)
    # Historical Repeat Conversion: 0.182 (18.2%)
    # Current Repeat Conversion: 0.148 (14.8%)
    # Total Window Orders: 1284
    # Total Window Revenue: 481850.0
    # Average Basket Size: ~375.27
    metrics = [
        ("evening_orders_baseline", 410.0),
        ("evening_orders_observed", 291.0),
        ("evening_orders_variance_pct", -29.02),
        ("repeat_conversion_baseline", 0.182),
        ("repeat_conversion_observed", 0.148),
        ("total_window_orders", 1284.0),
        ("total_window_revenue_inr", 481850.0),
        ("avg_basket_size_inr", round(481850.0 / 1284.0, 2)),
        ("target_campaign_customer_count", 486.0),
    ]

    for metric_name, val in metrics:
        cursor.execute(
            """
            INSERT INTO business_metrics (id, merchant_id, metric_name, metric_value, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (f"METRIC-{metric_name}", MERCHANT_ID, metric_name, val, NOW.isoformat()),
        )

    # 6. Seed Signal
    # Main demo scenario signal
    cursor.execute(
        """
        INSERT INTO signals (
            id, merchant_id, signal_type, severity, metric_name,
            baseline_value, observed_value, description, detected_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "SIG-EVN-DECLINE-01",
            MERCHANT_ID,
            "EVENING_ORDERS_DECLINE",
            "MEDIUM",
            "evening_orders",
            410.0,
            291.0,
            "Evening orders declined by 29.0% from baseline of 410 to 291 following expiration of Evening Rush Cashback.",
            NOW.isoformat(),
            "NEW",
        ),
    )

    # 7. Seed Initial Audit Record (if missing)
    cursor.execute("SELECT id FROM audit_events WHERE id = 'AUDIT-INIT-001'")
    if not cursor.fetchone():
        cursor.execute(
            """
            INSERT INTO audit_events (
                id, event_id, timestamp, stage, actor, event_type, input_payload,
                output_payload, decision, reason, previous_hash, integrity_hash,
                correlation_id, merchant_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "AUDIT-INIT-001",
                "AUDIT-INIT-001",
                NOW.isoformat(),
                "INITIALIZE",
                "DigitalTwinSeeder",
                "SIMULATION_INITIALIZED",
                json.dumps({"merchant_id": MERCHANT_ID, "customers": len(customers_data), "orders": len(calibrated_transactions)}),
                json.dumps({"status": "SUCCESS", "scenario": "EVENING_ORDERS_DECLINE", "variance_pct": -29.02}),
                "PASS",
                "Deterministic digital twin seeded for Track 3 demonstration",
                "GENESIS",
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "wf-seed-genesis",
                MERCHANT_ID,
            ),
        )

    conn.commit()
    conn.close()

    summary = {
        "merchants": 1,
        "customers": len(customers_data),
        "transactions": len(calibrated_transactions),
        "campaigns": len(campaigns_data),
        "total_revenue_inr": round(sum(t[3] for t in calibrated_transactions), 2),
        "evening_orders_current": 291,
        "evening_orders_baseline": 410,
        "target_campaign_customers": 486,
    }
    logger.info("Seed complete: %s", summary)
    return summary


if __name__ == "__main__":
    print("Executing MITRA Digital Twin Seeder...")
    result = seed_digital_twin()
    print("Deterministic Seed Result:", json.dumps(result, indent=2))
