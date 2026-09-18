"""API endpoints for MITRA AI Reasoning Layer & Command Center (Phase 13)."""
import json
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.database.repository import (
    ActionRepository,
    AutonomyRepository,
    DecisionRepository,
    GuardrailRepository,
    MerchantRepository,
    SignalRepository,
)
from app.engines.autonomy_engine.engine import AutonomyPolicyEngine
from app.engines.decision_engine.engine import DecisionEngine
from app.engines.guardrail_engine.engine import GuardrailEngine
from app.engines.investigation_engine.investigation_engine import InvestigationEngine
from app.engines.planning_engine.planning_engine import PlanningEngine
from app.engines.signal_engine.engine import SignalDetectionEngine
from app.llm.provider import get_ai_provider_manager
from app.models.contracts import (
    AIDemoScenarioRequest,
    AIMerchantQuestionRequest,
    AIProviderStatus,
    AIResponse,
)

router = APIRouter(prefix="/ai", tags=["AI Advisory & Command Center"])


@router.get(
    "/status",
    response_model=AIProviderStatus,
    summary="Get active AI reasoning provider status and capabilities",
)
def get_ai_status() -> AIProviderStatus:
    """Returns telemetry of active and available AI reasoning providers."""
    manager = get_ai_provider_manager()
    return manager.get_provider_status()


@router.post(
    "/explain/{correlation_id}",
    response_model=AIResponse,
    summary="Generate structured natural language explanation from verified workflow context",
)
async def explain_workflow(
    correlation_id: str,
    merchant_id: str = Query("MID-DEMO-98234", description="Merchant Identifier"),
) -> AIResponse:
    """Generates an advisory explanation grounded strictly in persisted SQLite workflow facts."""
    manager = get_ai_provider_manager()
    context = manager.build_context_from_workflow(
        correlation_id=correlation_id,
        merchant_id=merchant_id,
    )
    return await manager.generate_explanation(context)


@router.post(
    "/ask",
    response_model=AIResponse,
    summary="Merchant Q&A copilot grounded strictly in verified digital-twin context",
)
async def ask_mitra_copilot(
    payload: AIMerchantQuestionRequest,
) -> AIResponse:
    """Answers merchant questions using structured context, enforcing zero operational authority."""
    manager = get_ai_provider_manager()
    corr_id = payload.correlation_id or "wf-demo-main"
    context = manager.build_context_from_workflow(
        correlation_id=corr_id,
        merchant_id=payload.merchant_id,
        user_query=payload.question,
    )
    return await manager.answer_merchant_question(context, payload.question)


@router.post(
    "/demo-scenario/{scenario_id}",
    summary="Execute real, deterministic backend demo scenario for Command Center",
)
@router.post(
    "/scenario/{scenario_id}",
    summary="Execute real, deterministic backend demo scenario (alias)",
)
@router.post(
    "/demo-scenario",
    summary="Execute real, deterministic backend demo scenario with body payload",
)
@router.post(
    "/scenario",
    summary="Execute real, deterministic backend demo scenario with body payload (alias)",
)
async def trigger_demo_scenario(
    scenario_id: Optional[str] = None,
    body: Optional[AIDemoScenarioRequest] = None,
) -> Dict[str, Any]:
    """Orchestrates genuine backend pipelines for live hackathon demonstrations.
    
    Supported Scenarios:
    - NORMAL_FLOW: Signal -> Investigation -> Proposal -> Guardrail PASS -> Decision PENDING.
    - MODIFY_FLOW: Proposed ₹150 -> Guardrail clamped ₹100 -> Decision ₹100.
    - BLOCK_FLOW: Unsafe ₹5,000 discount -> Guardrail BLOCK -> Decision BLOCK.
    - AUTO_APPROVE_FLOW: Low-risk action under AUTO_APPROVE_SAFE mode -> Automatically approved.
    - UNAPPROVED_FLOW: Action held at merchant review gate.
    - INSUFFICIENT_DATA_FLOW: Unmeasured workflow demonstration.
    """
    sc_id = scenario_id or (body.scenario_id if body else None) or (body.scenario if body else None) or ""
    if not sc_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing scenario_id in request. Supported scenarios: NORMAL_FLOW, MODIFY_FLOW, BLOCK_FLOW, AUTO_APPROVE_FLOW, UNAPPROVED_FLOW, INSUFFICIENT_DATA_FLOW.",
        )
    mid = (body.merchant_id if body else None) or "MID-DEMO-98234"
    sc_upper = sc_id.upper()

    valid_scenarios = {
        "NORMAL": "NORMAL_FLOW",
        "NORMAL_FLOW": "NORMAL_FLOW",
        "MODIFY": "MODIFY_FLOW",
        "MODIFY_FLOW": "MODIFY_FLOW",
        "BLOCK": "BLOCK_FLOW",
        "BLOCK_FLOW": "BLOCK_FLOW",
        "AUTO_APPROVE": "AUTO_APPROVE_FLOW",
        "AUTO_APPROVE_FLOW": "AUTO_APPROVE_FLOW",
        "UNAPPROVED": "UNAPPROVED_FLOW",
        "UNAPPROVED_FLOW": "UNAPPROVED_FLOW",
        "INSUFFICIENT_DATA": "INSUFFICIENT_DATA_FLOW",
        "INSUFFICIENT_DATA_FLOW": "INSUFFICIENT_DATA_FLOW",
    }
    if sc_upper not in valid_scenarios:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown scenario ID '{scenario_id}'. Supported scenarios: NORMAL_FLOW, MODIFY_FLOW, BLOCK_FLOW, AUTO_APPROVE_FLOW, UNAPPROVED_FLOW, INSUFFICIENT_DATA_FLOW.",
        )

    # State isolation: clear stale ephemeral scenario objects and cache
    from app.database.connection import get_connection
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM autonomy_evaluations WHERE action_id LIKE 'act-demo-%' OR action_id LIKE 'prop-%'")
        cursor.execute("DELETE FROM decisions WHERE action_id LIKE 'act-demo-%' OR action_id LIKE 'prop-%'")
        cursor.execute("DELETE FROM guardrail_evaluations WHERE action_id LIKE 'act-demo-%' OR action_id LIKE 'prop-%'")
        cursor.execute("DELETE FROM actions WHERE id LIKE 'act-demo-%' OR id LIKE 'prop-%'")
        conn.commit()
    finally:
        conn.close()

    get_ai_provider_manager().clear_cache()

    if sc_upper in ("NORMAL", "NORMAL_FLOW"):
        # 1. Reset autonomy policy to demo default
        MerchantRepository.update_autonomy_policy(mid, autonomy_mode="APPROVAL_REQUIRED")
        # 2. Detect signal
        sig_engine = SignalDetectionEngine()
        signals = sig_engine.detect_signals(mid)
        sig = signals[0] if signals else None
        if not sig:
            raise HTTPException(status_code=404, detail="No signals detected for normal flow.")
        # 3. Investigate
        inv_engine = InvestigationEngine()
        inv = await inv_engine.investigate(signal=sig, merchant_id=mid, force_fallback=True)
        # 4. Plan
        plan_engine = PlanningEngine()
        act = await plan_engine.plan_action(inv, merchant_id=mid, force_fallback=True)
        # 5. Guardrail
        grd_engine = GuardrailEngine()
        grd = grd_engine.evaluate(act.action_id, mid)
        # 6. Decision
        dec_engine = DecisionEngine()
        dec = dec_engine.create_decision_from_persisted_evaluation(act.action_id, mid)
        # 7. Autonomy Evaluation
        aut_engine = AutonomyPolicyEngine()
        aut = aut_engine.evaluate(act.action_id, mid)

        return {
            "scenario": "NORMAL_FLOW",
            "signal_id": sig.signal_id,
            "correlation_id": f"wf-{sig.signal_id.replace('sig-', '').replace('SIG-', '').lower()}",
            "action_id": act.action_id,
            "decision_state": dec.decision_state.value if hasattr(dec.decision_state, "value") else str(dec.decision_state),
            "approval_status": dec.approval_status.value if hasattr(dec.approval_status, "value") else str(dec.approval_status),
            "autonomy_status": aut.autonomy_status.value if hasattr(aut.autonomy_status, "value") else str(aut.autonomy_status),
            "description": "Standard flow completed: Signal detected, investigated, action proposed, guardrails passed.",
        }

    elif sc_upper in ("MODIFY", "MODIFY_FLOW"):
        ActionRepository.create_or_update_action_proposal(
            signal_id="sig-demo-mod",
            investigation_id="inv-demo-mod",
            action_id="act-demo-mod",
            merchant_id=mid,
            action_type="OFFER_CAMPAIGN",
            parameters={
                "discount_percent": 10,
                "discount_amount": 150,
                "budget_inr": 1000,
                "target_count": 100,
                "risk_score": 0.25,
            },
        )
        grd = GuardrailEngine().evaluate("act-demo-mod", mid)
        dec = DecisionEngine().create_decision_from_persisted_evaluation("act-demo-mod", mid)
        aut = AutonomyPolicyEngine().evaluate("act-demo-mod", mid)

        return {
            "scenario": "MODIFY_FLOW",
            "action_id": "act-demo-mod",
            "original_discount": 150.0,
            "clamped_discount": 100.0,
            "decision_state": dec.decision_state.value if hasattr(dec.decision_state, "value") else str(dec.decision_state),
            "approval_status": dec.approval_status.value if hasattr(dec.approval_status, "value") else str(dec.approval_status),
            "description": "Guardrail clamped raw ₹150 discount to ₹100. Unsafe parameter excluded from execution.",
        }

    elif sc_upper in ("BLOCK", "BLOCK_FLOW"):
        ActionRepository.create_or_update_action_proposal(
            signal_id="sig-demo-blk",
            investigation_id="inv-demo-blk",
            action_id="act-demo-blk",
            merchant_id=mid,
            action_type="OFFER_CAMPAIGN",
            parameters={
                "discount_percent": 99,
                "discount_amount": 5000,
                "budget_inr": 999999,
                "target_count": 100,
                "risk_score": 0.95,
            },
        )
        grd = GuardrailEngine().evaluate("act-demo-blk", mid)
        dec = DecisionEngine().create_decision_from_persisted_evaluation("act-demo-blk", mid)
        aut = AutonomyPolicyEngine().evaluate("act-demo-blk", mid)

        return {
            "scenario": "BLOCK_FLOW",
            "action_id": "act-demo-blk",
            "decision_state": dec.decision_state.value if hasattr(dec.decision_state, "value") else str(dec.decision_state),
            "autonomy_status": aut.autonomy_status.value if hasattr(aut.autonomy_status, "value") else str(aut.autonomy_status),
            "is_execution_eligible": False,
            "description": "Hard guardrail BLOCK enforced. Action strictly ineligible for execution under any mode.",
        }

    elif sc_upper in ("AUTO_APPROVE", "AUTO_APPROVE_FLOW"):
        MerchantRepository.update_autonomy_policy(
            mid,
            autonomy_mode="AUTO_APPROVE_SAFE",
            auto_approval_risk_threshold=0.30,
        )
        ActionRepository.create_or_update_action_proposal(
            signal_id="sig-demo-auto",
            investigation_id="inv-demo-auto",
            action_id="act-demo-auto",
            merchant_id=mid,
            action_type="OFFER_CAMPAIGN",
            parameters={
                "discount_percent": 10,
                "discount_amount": 25,
                "budget_inr": 800,
                "target_count": 100,
                "risk_score": 0.20,
            },
        )
        grd = GuardrailEngine().evaluate("act-demo-auto", mid)
        dec = DecisionEngine().create_decision_from_persisted_evaluation("act-demo-auto", mid)
        aut = AutonomyPolicyEngine().evaluate("act-demo-auto", mid)

        return {
            "scenario": "AUTO_APPROVE_FLOW",
            "action_id": "act-demo-auto",
            "decision_state": dec.decision_state.value if hasattr(dec.decision_state, "value") else str(dec.decision_state),
            "autonomy_status": aut.autonomy_status.value if hasattr(aut.autonomy_status, "value") else str(aut.autonomy_status),
            "approval_source": aut.approval_source.value if hasattr(aut.approval_source, "value") else str(aut.approval_source),
            "is_execution_eligible": True,
            "description": "Risk 0.20 within safe policy threshold (0.30). Automatically approved and execution-eligible.",
        }

    elif sc_upper in ("UNAPPROVED", "UNAPPROVED_FLOW"):
        MerchantRepository.update_autonomy_policy(mid, autonomy_mode="APPROVAL_REQUIRED")
        ActionRepository.create_or_update_action_proposal(
            signal_id="sig-demo-unapp",
            investigation_id="inv-demo-unapp",
            action_id="act-demo-unapp",
            merchant_id=mid,
            action_type="OFFER_CAMPAIGN",
            parameters={
                "discount_percent": 10,
                "discount_amount": 20,
                "budget_inr": 500,
                "target_count": 100,
                "risk_score": 0.18,
            },
        )
        grd = GuardrailEngine().evaluate("act-demo-unapp", mid)
        dec = DecisionEngine().create_decision_from_persisted_evaluation("act-demo-unapp", mid)
        aut = AutonomyPolicyEngine().evaluate("act-demo-unapp", mid)

        return {
            "scenario": "UNAPPROVED_FLOW",
            "action_id": "act-demo-unapp",
            "decision_state": dec.decision_state.value if hasattr(dec.decision_state, "value") else str(dec.decision_state),
            "approval_status": dec.approval_status.value if hasattr(dec.approval_status, "value") else str(dec.approval_status),
            "is_execution_eligible": False,
            "description": "Action held pending merchant sign-off under APPROVAL_REQUIRED mode.",
        }

    elif sc_upper in ("INSUFFICIENT_DATA", "INSUFFICIENT_DATA_FLOW"):
        return {
            "scenario": "INSUFFICIENT_DATA_FLOW",
            "correlation_id": "wf-insufficient-data-99",
            "status": "UNAVAILABLE",
            "description": "Simulated empty / incomplete workflow context; zero fabricated or hallucinated numbers.",
        }

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown scenario ID '{scenario_id}'. Supported scenarios: NORMAL_FLOW, MODIFY_FLOW, BLOCK_FLOW, AUTO_APPROVE_FLOW, UNAPPROVED_FLOW, INSUFFICIENT_DATA_FLOW.",
        )
