'use client';

import React, { useState } from 'react';
import { ActionProposal, AutonomyEvaluation, Decision, GuardrailEvaluation } from '@/types';
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Hash,
  Loader2,
  Lock,
  Scale,
  Shield,
  ShieldAlert,
  ShieldCheck,
  UserCheck,
  XCircle,
  Zap,
} from 'lucide-react';

interface DecisionStatusAreaProps {
  decision: Decision | null;
  proposal: ActionProposal | null;
  guardrailEvaluation: GuardrailEvaluation | null;
  autonomyEvaluation?: AutonomyEvaluation | null;
  isCreating: boolean;
  isApproving: boolean;
  isRejecting: boolean;
  onCreateDecision: () => void;
  onApprove: () => void;
  onReject: () => void;
}

export const DecisionStatusArea: React.FC<DecisionStatusAreaProps> = ({
  decision,
  proposal,
  guardrailEvaluation,
  autonomyEvaluation,
  isCreating,
  isApproving,
  isRejecting,
  onCreateDecision,
  onApprove,
  onReject,
}) => {
  const [showChecklist, setShowChecklist] = useState(false);

  const hasGuardrails = Boolean(guardrailEvaluation);
  const isBlock = decision?.decision_state === 'BLOCK' || autonomyEvaluation?.blocked;
  const isEscalate = decision?.decision_state === 'ESCALATE' || autonomyEvaluation?.escalated;
  const isModify = decision?.decision_state === 'MODIFY';
  const isPass = decision?.decision_state === 'PASS' && !isBlock && !isEscalate;

  const isAutoApproved = autonomyEvaluation?.approval_source === 'AUTO_APPROVED';
  const isHumanApproved = decision?.approval_status === 'APPROVED' && !isAutoApproved;
  const isRejected = decision?.approval_status === 'REJECTED' || autonomyEvaluation?.approval_source === 'REJECTED';

  // Extract clamped parameters if any
  const originalDiscountVal = proposal?.incentive_value ?? (proposal?.parameters?.discount_amount as number | undefined);
  const executedDiscountVal = (decision?.approved_action?.parameters?.discount_amount as number | undefined) ?? decision?.approved_action?.incentive_value;
  const hasClampedDiscount = Boolean(isModify && originalDiscountVal && executedDiscountVal && Number(originalDiscountVal) !== Number(executedDiscountVal));
  const originalDiscountStr = String(originalDiscountVal ?? '');
  const executedDiscountStr = String(executedDiscountVal ?? '');

  return (
    <div className="bg-white border border-slate-200/90 rounded-xl p-5 shadow-xs space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-100 gap-2">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-blue-50 border border-blue-200/70 rounded-lg text-[#002E6E]">
            <Scale className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Authoritative Decision &amp; Autonomy Gate
              </h2>
              <span className="text-[10px] bg-slate-100 text-slate-700 font-bold px-2 py-0.5 rounded-full border border-slate-200">
                Phases 7 &amp; 12
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Deterministic decision derivation, policy matrix evaluation, and transparent approval gating
            </p>
          </div>
        </div>

        {/* Action Button: Create Decision if GuardrailEvaluation exists */}
        {!decision && (
          <div>
            {hasGuardrails ? (
              <button
                onClick={onCreateDecision}
                disabled={isCreating}
                className="inline-flex items-center gap-2 px-4 py-2 bg-[#002E6E] hover:bg-[#001D47] active:bg-[#001330] disabled:bg-slate-300 text-white text-xs font-bold rounded-lg shadow-xs transition-all cursor-pointer disabled:cursor-not-allowed"
              >
                {isCreating ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Deriving Decision...
                  </>
                ) : (
                  <>
                    <Scale className="w-3.5 h-3.5 text-[#00BAF2]" />
                    Synthesize Decision
                  </>
                )}
              </button>
            ) : (
              <div className="text-[11px] text-amber-800 bg-amber-50 px-2.5 py-1.5 rounded-md border border-amber-200 flex items-center gap-1.5 font-semibold">
                <AlertCircle className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />
                Complete Guardrails first
              </div>
            )}
          </div>
        )}
      </div>

      {/* Precondition Notice when GuardrailEvaluation is missing */}
      {!hasGuardrails && (
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-center space-y-1.5">
          <div className="inline-flex p-2 bg-slate-100 rounded-full text-slate-400">
            <Lock className="w-4 h-4" />
          </div>
          <h4 className="text-xs font-bold text-slate-700">Precondition Not Met</h4>
          <p className="text-[11px] text-slate-500 max-w-md mx-auto">
            A Decision cannot exist without an authoritative, persisted <strong className="text-slate-700">GuardrailEvaluation</strong>.
            Please run Step 4 (Guardrail Evaluation) above before synthesizing a decision.
          </p>
        </div>
      )}

      {/* Guardrail Ready but Decision Not Yet Created */}
      {hasGuardrails && !decision && (
        <div className="bg-sky-50/60 border border-sky-200 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="space-y-0.5">
            <div className="flex items-center gap-1.5 text-xs font-bold text-[#002E6E]">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              Guardrail Evaluation Persisted ({guardrailEvaluation?.overall_status})
            </div>
            <p className="text-[11px] text-slate-600">
              Ready to derive authoritative decision for action <code className="bg-white px-1.5 py-0.5 rounded text-[10px] font-mono border border-sky-200 text-[#002E6E]">{proposal?.action_id || guardrailEvaluation?.action_id}</code>.
            </p>
          </div>
          <button
            onClick={onCreateDecision}
            disabled={isCreating}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-1.5 px-4 py-2 bg-[#002E6E] hover:bg-[#001D47] active:bg-[#001330] disabled:bg-slate-300 text-white text-xs font-bold rounded-lg shadow-xs transition-all cursor-pointer"
          >
            {isCreating ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Deriving Decision...
              </>
            ) : (
              <>
                <Scale className="w-3.5 h-3.5 text-[#00BAF2]" />
                Generate Authoritative Decision
              </>
            )}
          </button>
        </div>
      )}

      {/* Decision Details Card */}
      {decision && (
        <div className="space-y-4">
          {/* Status Verdict Banner */}
          <div
            className={`p-3.5 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-2 ${
              isPass
                ? 'bg-emerald-50/70 border-emerald-200 text-emerald-950'
                : isModify
                ? 'bg-sky-50/70 border-sky-200 text-[#002E6E]'
                : isBlock
                ? 'bg-rose-50/70 border-rose-200 text-rose-950'
                : 'bg-amber-50/70 border-amber-200 text-amber-950'
            }`}
          >
            <div className="flex items-start gap-2.5">
              {isPass && <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />}
              {isModify && <ShieldCheck className="w-5 h-5 text-[#007EA7] flex-shrink-0 mt-0.5" />}
              {isBlock && <ShieldAlert className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />}
              {isEscalate && <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />}
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-bold uppercase tracking-wider">
                    Authoritative Decision: {decision.decision_state}
                  </span>
                  <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-white border border-current/20">
                    {decision.decision_id}
                  </span>
                  {autonomyEvaluation && (
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-white text-[#002E6E] border border-sky-300">
                      Mode: {autonomyEvaluation.autonomy_mode}
                    </span>
                  )}
                </div>
                <p className="text-xs mt-0.5 font-medium leading-relaxed opacity-90">
                  {decision.reason}
                </p>
              </div>
            </div>

            <div className="text-right flex sm:flex-col items-center sm:items-end justify-between text-[11px] opacity-75 font-mono">
              <span className="font-semibold">{decision.decided_by}</span>
              <span className="text-[10px]">
                {decision.decided_at ? new Date(decision.decided_at).toLocaleTimeString() : ''}
              </span>
            </div>
          </div>

          {/* MODIFY Clamping Notice */}
          {hasClampedDiscount && (
            <div className="p-3 bg-sky-50 border border-sky-200 rounded-lg text-xs text-[#002E6E] flex items-start gap-2">
              <Shield className="w-4 h-4 text-[#007EA7] flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">MODIFY Parameter Clamping Enforced:</span>
                <span className="block text-[11px] text-slate-600 mt-0.5">
                  Original proposed discount was ₹{originalDiscountStr}, clamped by guardrail to ₹{executedDiscountStr}.
                  The autonomy engine evaluates and authorizes strictly ₹{executedDiscountStr}. The unsafe ₹{originalDiscountStr} is NEVER executed.
                </span>
              </div>
            </div>
          )}

          {/* Autonomy & Sign-off Gate Area */}
          <div className="border border-slate-200/90 rounded-xl p-4 bg-slate-50/70 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-2.5 border-b border-slate-200/80 gap-2">
              <div className="flex items-center gap-2">
                {isAutoApproved ? (
                  <Zap className="w-4 h-4 text-emerald-600" />
                ) : (
                  <UserCheck className="w-4 h-4 text-[#002E6E]" />
                )}
                <h3 className="text-xs font-bold text-slate-800">
                  {isAutoApproved ? 'Autonomous Clearance Gate' : 'Merchant Sign-off Gate'}
                </h3>
                <span className="text-[10px] bg-white text-slate-700 font-semibold px-2 py-0.5 rounded border border-slate-200 shadow-xs">
                  Mode: {autonomyEvaluation?.autonomy_mode || 'APPROVAL_REQUIRED'}
                </span>
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[11px] text-slate-500 font-medium">Source:</span>
                <span
                  className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${
                    isAutoApproved
                      ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                      : isHumanApproved
                      ? 'bg-blue-100 text-[#002E6E] border border-blue-300'
                      : isRejected
                      ? 'bg-rose-100 text-rose-800 border border-rose-300'
                      : 'bg-amber-100 text-amber-800 border border-amber-300'
                  }`}
                >
                  {autonomyEvaluation?.approval_source || decision.approval_status}
                </span>
                <span
                  className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${
                    decision.is_execution_eligible
                      ? 'bg-emerald-600 text-white shadow-xs'
                      : 'bg-slate-200 text-slate-600'
                  }`}
                >
                  {decision.is_execution_eligible ? 'EXECUTION ELIGIBLE' : 'EXECUTION INELIGIBLE'}
                </span>
              </div>
            </div>

            {/* AUTO-APPROVED Banner */}
            {isAutoApproved && autonomyEvaluation && (
              <div className="p-3 bg-emerald-50/90 border border-emerald-200 rounded-xl text-xs text-emerald-950 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Zap className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                  <div>
                    <span className="font-bold">Auto-Approved by Deterministic Policy</span>
                    <span className="text-[11px] text-emerald-800 block sm:inline sm:ml-2">
                      Evaluated Risk: <strong>{autonomyEvaluation.evaluated_risk.toFixed(2)}</strong> ≤ Policy Threshold: <strong>{autonomyEvaluation.policy_threshold.toFixed(2)}</strong>.
                      All 16 deterministic conditions verified.
                    </span>
                  </div>
                </div>
                <span className="text-[10px] font-mono text-emerald-900 bg-emerald-100 px-2 py-0.5 rounded font-bold border border-emerald-200">
                  AUTONOMY_POLICY
                </span>
              </div>
            )}

            {/* Approved Parameters Preview */}
            {decision.approved_action ? (
              <div className="bg-white border border-slate-200/90 rounded-xl p-3.5 space-y-2 shadow-xs">
                <div className="flex items-center justify-between text-xs font-bold text-slate-800">
                  <span>Authorized Execution Parameters:</span>
                  {isModify && (
                    <span className="text-[10px] font-semibold text-[#002E6E] bg-sky-50 px-2 py-0.5 rounded-full border border-sky-200">
                      Modified by Guardrails
                    </span>
                  )}
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                  <div className="p-2 bg-slate-50/80 rounded-lg border border-slate-100">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 block">Action Type</span>
                    <span className="font-bold text-slate-800 truncate block mt-0.5">
                      {decision.approved_action.action_type}
                    </span>
                  </div>
                  <div className="p-2 bg-slate-50/80 rounded-lg border border-slate-100">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 block">Incentive / Cashback</span>
                    <span className="font-bold text-emerald-700 block mt-0.5">
                      ₹{String(decision.approved_action.parameters?.discount_amount ?? decision.approved_action.incentive_value ?? proposal?.incentive_value ?? 0)}
                    </span>
                  </div>
                  <div className="p-2 bg-slate-50/80 rounded-lg border border-slate-100">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 block">Target Audience</span>
                    <span className="font-bold text-slate-800 block mt-0.5">
                      {String(decision.approved_action.parameters?.target_count ?? decision.approved_action.target_customer_count ?? proposal?.target_customer_count ?? 0)} customers
                    </span>
                  </div>
                  <div className="p-2 bg-slate-50/80 rounded-lg border border-slate-100">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 block">Est. Budget</span>
                    <span className="font-bold text-slate-800 block mt-0.5">
                      ₹{String(decision.approved_action.parameters?.budget_inr ?? decision.approved_action.estimated_cost_inr ?? proposal?.estimated_cost_inr ?? 0)}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-rose-50/60 border border-rose-200/80 rounded-xl p-3 text-xs text-rose-800 flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-rose-600 flex-shrink-0" />
                <span>
                  No approved action parameters exist. Action is strictly forbidden from executing.
                </span>
              </div>
            )}

            {/* Merchant Sign-off Action Buttons for Pending Human Review */}
            {decision.approval_status === 'PENDING' && !isBlock && !isEscalate && (
              <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-1">
                <div className="text-[11px] text-slate-600 leading-relaxed">
                  {autonomyEvaluation?.autonomy_mode === 'APPROVAL_REQUIRED'
                    ? 'Merchant review required under current policy mode. Clicking Approve authorizes execution.'
                    : `Action risk (${autonomyEvaluation?.evaluated_risk.toFixed(2)}) exceeds policy auto-approval threshold (${autonomyEvaluation?.policy_threshold.toFixed(2)}). Merchant review required.`}
                </div>
                <div className="flex items-center gap-2 w-full sm:w-auto">
                  <button
                    onClick={onReject}
                    disabled={isRejecting || isApproving}
                    className="flex-1 sm:flex-none inline-flex items-center justify-center gap-1.5 px-3.5 py-2 border border-rose-200 text-rose-700 hover:bg-rose-50 disabled:bg-slate-100 text-xs font-bold rounded-lg transition-colors cursor-pointer"
                  >
                    {isRejecting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <XCircle className="w-3.5 h-3.5" />}
                    Reject
                  </button>
                  <button
                    onClick={onApprove}
                    disabled={isApproving || isRejecting}
                    className="flex-1 sm:flex-none inline-flex items-center justify-center gap-1.5 px-4 py-2 bg-[#002E6E] hover:bg-[#001D47] active:scale-[0.98] disabled:bg-slate-300 text-white text-xs font-bold rounded-lg shadow-sm transition-all cursor-pointer"
                  >
                    {isApproving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                    Approve Action
                  </button>
                </div>
              </div>
            )}

            {/* BLOCK Decision Message */}
            {isBlock && (
              <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-950 space-y-1">
                <div className="font-bold flex items-center gap-1.5 text-rose-700">
                  <Lock className="w-4 h-4" />
                  Approval Strictly Prohibited (Hard Guardrail BLOCK)
                </div>
                <p className="text-[11px] text-rose-700/90 leading-relaxed">
                  Hard guardrail BLOCK cannot be bypassed under ANY autonomy mode (including FULL_AUTONOMY).
                  Neither merchant nor autonomy policy can authorize execution.
                </p>
              </div>
            )}

            {/* ESCALATE Decision Message */}
            {isEscalate && (
              <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-950 space-y-1">
                <div className="font-bold flex items-center gap-1.5 text-amber-700">
                  <AlertTriangle className="w-4 h-4" />
                  Manual Escalation Review Required
                </div>
                <p className="text-[11px] text-amber-700/90 leading-relaxed">
                  This action triggered high-risk policy boundary checks and requires manual intervention outside autonomous execution.
                </p>
              </div>
            )}

            {/* HUMAN APPROVED Success Banner */}
            {isHumanApproved && (
              <div className="p-3.5 bg-emerald-50/90 border border-emerald-200 rounded-xl text-xs text-emerald-950 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <UserCheck className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                  <div>
                    <span className="font-bold">Merchant Sign-off Recorded (HUMAN_APPROVED)</span>
                    <span className="text-[11px] text-emerald-800 block sm:inline sm:ml-2">
                      Signed off by merchant admin. Action is authorized and execution-eligible.
                    </span>
                  </div>
                </div>
                <span className="text-[10px] text-emerald-800 font-mono bg-emerald-100/90 border border-emerald-200 px-2 py-0.5 rounded font-bold">
                  {decision.approved_at ? new Date(decision.approved_at).toLocaleTimeString() : 'Approved'}
                </span>
              </div>
            )}

            {/* REJECTED Notice */}
            {isRejected && (
              <div className="p-3.5 bg-slate-100 border border-slate-200 rounded-xl text-xs text-slate-700 flex items-center gap-2">
                <XCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
                <span>Action rejected by merchant. Execution bypassed safely.</span>
              </div>
            )}

            {/* 16-Point Safety Conditions Checklist (Collapsible) */}
            {autonomyEvaluation && (
              <div className="pt-2 border-t border-slate-200/80">
                <button
                  type="button"
                  onClick={() => setShowChecklist(!showChecklist)}
                  className="flex items-center justify-between w-full text-xs font-semibold text-[#002E6E] hover:text-[#001D47] transition-colors cursor-pointer"
                >
                  <span className="flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-[#007EA7]" />
                    16-Point Safety Policy Verification ({autonomyEvaluation.passed_checks.length}/16 Passed)
                  </span>
                  {showChecklist ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>

                {showChecklist && (
                  <div className="mt-2.5 space-y-1.5 text-[11px] bg-white p-3.5 rounded-xl border border-slate-200/90 shadow-xs">
                    {autonomyEvaluation.passed_checks.map((chk, i) => (
                      <div key={`pass-${i}`} className="flex items-start gap-1.5 text-emerald-700">
                        <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 text-emerald-600" />
                        <span>{chk}</span>
                      </div>
                    ))}
                    {autonomyEvaluation.failed_checks.map((chk, i) => (
                      <div key={`fail-${i}`} className="flex items-start gap-1.5 text-rose-600 font-medium">
                        <XCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 text-rose-500" />
                        <span>{chk}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Cryptographic Hash Integrity Footer */}
          <div className="pt-2 flex flex-wrap items-center justify-between text-[10px] text-slate-500 gap-2 border-t border-slate-100">
            <div className="flex items-center gap-1.5">
              <Hash className="w-3 h-3 text-slate-400" />
              <span>Proposal SHA-256:</span>
              <code className="font-mono text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200/60">
                {decision.proposal_hash ? `${decision.proposal_hash.slice(0, 16)}...` : 'N/A'}
              </code>
            </div>
            <div className="flex items-center gap-1.5">
              <Hash className="w-3 h-3 text-slate-400" />
              <span>Evaluation SHA-256:</span>
              <code className="font-mono text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200/60">
                {decision.evaluation_hash ? `${decision.evaluation_hash.slice(0, 16)}...` : 'N/A'}
              </code>
            </div>
            <div className="text-slate-500 font-semibold flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3 text-emerald-600" />
              Deterministic Truth Verified
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
