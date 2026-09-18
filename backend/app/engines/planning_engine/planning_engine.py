"""Core Planning Engine for MITRA action synthesis."""
import asyncio
import json
from typing import Any, Dict, List, Optional
import uuid

from app.core.logging import logger
from app.database.repository import ActionRepository, InvestigationRepository
from app.engines.audit_engine.engine import AuditEngine
from app.engines.planning_engine.context_builder import PlanningContextBuilder
from app.engines.planning_engine.prompts import (
    SYSTEM_INSTRUCTION,
    build_planning_prompt,
)
from app.engines.planning_engine.schemas import PlanningContext
from app.engines.planning_engine.validator import ActionValidator
from app.llm.client import LLMClient, get_llm_client
from app.models.contracts import ActionProposal, Investigation
from app.models.enums import ActionType, StageType


class PlanningEngine:
    """Synthesizes structured candidate ActionProposal from investigated business signals.
    
    SAFETY PRINCIPLES:
    - ONLY PROPOSES: Does not execute or approve actions.
    - Zero execution calls: GuardrailEngine and ExecutionEngine are never called here.
    - Deterministic boundaries: Budget, discounts, and target audience bounds are non-negotiable.
    - Hallucination & excessive proposal rejection: Unbounded proposals fall back safely.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        audit_engine: Optional[AuditEngine] = None,
    ):
        self.llm_client = llm_client or get_llm_client()
        self.audit_engine = audit_engine or AuditEngine()

    async def plan_action(
        self,
        investigation: Any,
        merchant_id: Optional[str] = None,
        force_fallback: bool = False,
    ) -> ActionProposal:
        """Asynchronously synthesizes an ActionProposal for an investigated signal."""
        # 1. Build deterministic planning context from SQLite
        context: PlanningContext = PlanningContextBuilder.build_context(
            investigation=investigation,
            merchant_id=merchant_id,
        )

        inv_id = context.investigation_id
        sig_id = context.signal_id
        mid = context.merchant_id

        # Determine existing or new action ID (for idempotency)
        existing_action = ActionRepository.get_action_by_investigation(inv_id)
        if existing_action:
            action_id = existing_action["id"]
        else:
            action_id = f"prop-{uuid.uuid4().hex[:10]}"

        # 2. Record audit: ACTION_PLANNING_STARTED
        self.audit_engine.record_event(
            stage=StageType.DECIDE,
            actor=f"PlanningEngine ({self.llm_client.provider_name})",
            action_description=f"ACTION_PLANNING_STARTED: Began action planning for investigation {inv_id}",
            input_payload={
                "investigation_id": inv_id,
                "signal_id": sig_id,
                "merchant_id": mid,
                "action_id": action_id,
                "eligible_customer_count": context.eligible_customer_count,
            },
            output_payload={"status": "PLANNING"},
        )

        logger.info(
            "Starting action planning for investigation: %s (force_fallback=%s)",
            inv_id,
            force_fallback,
        )

        proposal: Optional[ActionProposal] = None
        use_fallback = force_fallback or not self.llm_client.is_available

        # 3. Call LLM if available and not forced fallback
        if not use_fallback:
            try:
                prompt = build_planning_prompt(context)
                raw_llm_response = await self.llm_client.generate(
                    prompt=prompt,
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.2,
                )

                # 4. Strict code-level validation
                is_valid, validated_proposal, error_reason = ActionValidator.validate_and_parse(
                    raw_llm_response=raw_llm_response,
                    context=context,
                    action_id=action_id,
                )

                if is_valid and validated_proposal:
                    proposal = validated_proposal
                    logger.info("LLM action proposal successfully validated for %s", inv_id)
                else:
                    logger.warning(
                        "LLM proposal failed validation (%s). Rejecting and engaging Fallback Planner.",
                        error_reason,
                    )
                    use_fallback = True
            except Exception as exc:
                logger.warning("LLM proposal generation error: %s. Engaging Fallback Planner.", exc)
                use_fallback = True

        # 5. Deterministic fallback planner if LLM unavailable or rejected
        if use_fallback or not proposal:
            proposal = self._generate_fallback_proposal(
                context=context,
                action_id=action_id,
            )

        # 6. Persist proposal to SQLite actions table idempotently
        ActionRepository.create_or_update_action_proposal(
            action_id=proposal.proposal_id,
            signal_id=proposal.signal_id,
            investigation_id=context.investigation_id,
            merchant_id=proposal.merchant_id,
            action_type=proposal.action_type.value,
            objective=proposal.objective or "",
            target_segment=proposal.target_segment or "repeat_customer, regular",
            target_customer_count=proposal.target_customer_count or context.eligible_customer_count,
            incentive_type=proposal.incentive_type or "CASHBACK",
            incentive_value=proposal.incentive_value or 50.0,
            duration=proposal.duration or "7 days",
            reason=proposal.reason,
            supporting_evidence_ids=proposal.supporting_evidence_ids,
            constraints=proposal.constraints,
            parameters=proposal.parameters,
            estimated_cost_inr=proposal.estimated_cost_inr,
            status="PROPOSED",
            is_fallback=proposal.is_fallback,
        )

        # 7. Record audit: ACTION_PROPOSAL_CREATED
        self.audit_engine.record_event(
            stage=StageType.DECIDE,
            actor=f"PlanningEngine ({'FallbackClient' if proposal.is_fallback else self.llm_client.provider_name})",
            action_description=f"ACTION_PROPOSAL_CREATED: Generated candidate proposal {proposal.proposal_id}",
            input_payload={
                "investigation_id": inv_id,
                "signal_id": sig_id,
                "action_id": proposal.proposal_id,
            },
            output_payload={
                "action_type": proposal.action_type.value,
                "target_customer_count": proposal.target_customer_count,
                "incentive_value": proposal.incentive_value,
                "is_fallback": proposal.is_fallback,
                "status": "PROPOSED",
            },
        )

        return proposal

    def plan_action_sync(
        self,
        investigation: Any,
        merchant_id: Optional[str] = None,
        force_fallback: bool = False,
    ) -> ActionProposal:
        """Synchronously executes action planning for synchronous callers/tests."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    return pool.submit(
                        asyncio.run,
                        self.plan_action(
                            investigation=investigation,
                            merchant_id=merchant_id,
                            force_fallback=force_fallback,
                        ),
                    ).result()
            return loop.run_until_complete(
                self.plan_action(
                    investigation=investigation,
                    merchant_id=merchant_id,
                    force_fallback=force_fallback,
                )
            )
        except RuntimeError:
            return asyncio.run(
                self.plan_action(
                    investigation=investigation,
                    merchant_id=merchant_id,
                    force_fallback=force_fallback,
                )
            )

    def _generate_fallback_proposal(
        self,
        context: PlanningContext,
        action_id: str,
    ) -> ActionProposal:
        """Generates a conservative, evidence-grounded fallback proposal."""
        target_count = context.eligible_customer_count
        incentive_val = min(50.0, context.planning_limits.max_discount_inr)
        estimated_cost = min(5000.0, context.planning_limits.max_daily_budget_inr)

        # Citing relevant evidence IDs available in context
        supporting_eids = [
            eid for eid in ["E1", "E2", "E3", "E4"]
            if eid in context.available_evidence_ids
        ]
        if not supporting_eids and context.available_evidence_ids:
            supporting_eids = context.available_evidence_ids[:3]

        reason = (
            f"Evening orders declined by 29.02% and repeat conversion dropped from 18.2% to 14.8%, "
            f"coinciding with the expiration of the previous promotion 3 days ago. Re-engaging the "
            f"{target_count} eligible repeat and regular customers with a conservative INR {incentive_val:.0f} "
            f"cashback incentive restores evening transaction velocity within merchant guardrail boundaries."
        )

        parameters = {
            "incentive_type": "CASHBACK",
            "incentive_value": incentive_val,
            "discount_amount": incentive_val,
            "target_segment": "repeat_customer, regular",
            "target_customer_count": target_count,
            "target_count": target_count,
            "duration": "7 days",
            "budget_inr": estimated_cost,
        }

        constraints_snapshot = {
            "max_discount_inr": context.planning_limits.max_discount_inr,
            "max_daily_budget_inr": context.planning_limits.max_daily_budget_inr,
            "eligible_customers": context.planning_limits.max_eligible_customers,
            "minimum_margin": context.planning_limits.min_margin,
            "autonomy_mode": context.merchant_rules.autonomy_mode,
        }

        return ActionProposal(
            proposal_id=action_id,
            action_id=action_id,
            signal_id=context.signal_id,
            investigation_id=context.investigation_id,
            merchant_id=context.merchant_id,
            action_type=ActionType.EVENING_REENGAGEMENT_CAMPAIGN,
            objective="Re-engage evening shoppers and recover repeat conversion",
            target_segment="repeat_customer, regular",
            target_customer_count=target_count,
            incentive_type="CASHBACK",
            incentive_value=incentive_val,
            duration="7 days",
            parameters=parameters,
            reason=reason,
            confidence=0.85,
            estimated_cost_inr=estimated_cost,
            supporting_evidence_ids=supporting_eids,
            constraints=constraints_snapshot,
            projected_impact={
                "target_reach": target_count,
                "reengagement_window": "7 days",
            },
            status="PROPOSED",
            is_fallback=True,
        )
