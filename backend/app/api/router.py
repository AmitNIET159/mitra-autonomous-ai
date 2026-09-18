from fastapi import APIRouter
from app.api.actions import router as actions_router
from app.api.ai import router as ai_router
from app.api.audit import router as audit_router
from app.api.autonomy import merchants_autonomy_router, router as autonomy_router
from app.api.business_impact import router as business_impact_router
from app.api.decisions import router as decisions_router
from app.api.demo import router as demo_router
from app.api.executions import router as executions_router
from app.api.explainability import router as explainability_router
from app.api.guardrails import router as guardrails_router
from app.api.health import router as health_router
from app.api.investigations import router as investigations_router
from app.api.merchant import router as merchant_router
from app.api.outcomes import router as outcomes_router
from app.api.signals import router as signals_router
from app.api.simulation import router as simulation_router
from app.api.system import router as system_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router)
api_router.include_router(system_router)
api_router.include_router(merchant_router)
api_router.include_router(merchants_autonomy_router)
api_router.include_router(signals_router)
api_router.include_router(investigations_router)
api_router.include_router(actions_router)
api_router.include_router(guardrails_router)
api_router.include_router(decisions_router)
api_router.include_router(autonomy_router)
api_router.include_router(executions_router)
api_router.include_router(outcomes_router)
api_router.include_router(business_impact_router)
api_router.include_router(audit_router)
api_router.include_router(explainability_router)
api_router.include_router(simulation_router)
api_router.include_router(ai_router)
api_router.include_router(demo_router)



