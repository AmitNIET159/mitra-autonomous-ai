from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import logger
from app.database.connection import init_db
from app.database.repository import MerchantRepository
from app.database.seed import seed_digital_twin

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("Starting MITRA Backend (%s)", settings.APP_VERSION)
    logger.info("Environment: %s | Simulation Mode: %s", settings.APP_ENV, settings.SIMULATION_MODE)
    init_db()
    # Auto-seed digital twin if unseeded
    if not MerchantRepository.get_merchant("MID-DEMO-98234"):
        logger.info("Database empty on startup. Auto-seeding deterministic digital twin...")
        seed_digital_twin()
    yield
    logger.info("Shutting down MITRA Backend.")


app = FastAPI(
    title="MITRA — Autonomous AI Teammate for Paytm Merchants",
    description=(
        "Backend engine for MITRA: DETECT → INVESTIGATE → DECIDE → GUARD → ACT → LEARN. "
        "Deterministic Guardrails + LLM Reasoner."
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS middleware for frontend communication (local dev, Vercel, Render)
cors_origins_str = settings.CORS_ORIGINS.strip()
if cors_origins_str == "*":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    origins = [o.strip() for o in cors_origins_str.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API Router
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
