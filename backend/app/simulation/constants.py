"""Simulation constants and merchant digital-twin definitions.

IMPORTANT:
All merchant metrics, transaction volumes, campaigns, and outcomes are
simulated synthetic data for the prototype and hackathon demonstration.
No real Paytm production API or private merchant data is accessed or represented.
"""

SIMULATION_DISCLAIMER = (
    "PROTOTYPE SIMULATION NOTICE: All merchant data, transaction signals, "
    "Paytm Soundbox/POS telemetry, and projected financial outcomes are synthetic simulations "
    "running in a digital-twin sandbox for the Paytm Build for India Hackathon."
)

DEFAULT_MERCHANT_PROFILE = {
    "merchant_id": "MID-DELHI-98234",
    "business_name": "Sharma Kirana & General Store",
    "category": "Grocery & Daily Essentials",
    "location": "Lajpat Nagar IV, New Delhi",
    "tier": "Tier-1 Metro Retail",
    "paytm_products": [
        {"name": "Paytm Soundbox 4.0", "status": "ONLINE", "battery_pct": 89},
        {"name": "Paytm All-In-One QR", "status": "ACTIVE", "placement": "Front Counter"},
        {"name": "Paytm Card Machine", "status": "STANDBY"},
    ],
    "average_daily_gmv_inr": 18500.0,
    "average_daily_txns": 142,
}
