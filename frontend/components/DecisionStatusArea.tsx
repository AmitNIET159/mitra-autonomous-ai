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
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800 gap-2">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-indigo-50 dark:bg-indigo-950/60 rounded-lg text-indigo-700 dark:text-indigo-400">
            <Scale className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Authoritative Decision & Autonomy Gate
              </h2>
              <span className="text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold px-2 py-0.5 rounded-full border border-slate-200 dark:border-slate-700">
                Phases 7 & 12
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
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
                className="inline-flex items-center gap-2 px-3.5 py-2 bg-[#002E6E] hover:bg-[#001f4d] disabled:bg-slate-300 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors cursor-pointer"
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
              <div className="text-[11px] text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/40 px-2.5 py-1.5 rounded-md border border-amber-200 dark:border-amber-800 flex items-center gap-1.5 font-medium">
                <AlertCircle className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />
                Complete Guardrails first
              </div>
            )}
          </div>
        )}
      </div>

      {/* Precondition Notice when GuardrailEvaluation is missing */}
      {!hasGuardrails && (
        <div className="bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 rounded-lg p-4 text-center space-y-1.5">
          <div className="inline-flex p-2 bg-slate-100 dark:bg-slate-800 rounded-full text-slate-400">
            <Lock className="w-4 h-4" />
          </div>
          <h4 className="text-xs font-semibold text-slate-700 dark:text-slate-300">Precondition Not Met</h4>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 max-w-md mx-auto">
            A Decision cannot exist without an authoritative, persisted <strong className="text-slate-700 dark:text-slate-300">GuardrailEvaluation</strong>.
            Please run Step 4 (Guardrail Evaluation) above before synthesizing a decision.
          </p>
        </div>
      )}

      {/* Guardrail Ready but Decision Not Yet Created */}
      {hasGuardrails && !decision && (
        <div className="bg-blue-50/50 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-900/40 rounded-lg p-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="space-y-0.5">
            <div className="flex items-center gap-1.5 text-xs font-bold text-blue-900 dark:text-blue-300">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              Guardrail Evaluation Persisted ({guardrailEvaluation?.overall_status})
            </div>
            <p className="text-[11px] text-blue-700 dark:text-blue-400">
              Ready to derive authoritative decision for action <code className="bg-blue-100/60 dark:bg-blue-900/60 px-1 py-0.5 rounded text-[10px]">{proposal?.action_id || guardrailEvaluation?.action_id}</code>.
            </p>
          </div>
          <button
            onClick={onCreateDecision}
            disabled={isCreating}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-1.5 px-4 py-2 bg-[#002E6E] hover:bg-[#001f4d] disabled:bg-slate-300 text-white text-xs font-bold rounded-lg shadow-sm transition-colors cursor-pointer"
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
            className={`p-3.5 rounded-lg border flex flex-col sm:flex-row sm:items-center justify-between gap-2 ${
              isPass
                ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200'
                : isModify
                ? 'bg-blue-50 dark:bg-blue-950/40 border-blue-200 dark:border-blue-800 text-blue-900 dark:text-blue-200'
                : isBlock
                ? 'bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-800 text-rose-900 dark:text-rose-200'
                : 'bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-800 text-amber-900 dark:text-amber-200'
            }`}
          >
            <div className="flex items-start gap-2.5">
              {isPass && <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />}
              {isModify && <ShieldCheck className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />}
              {isBlock && <ShieldAlert className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />}
              {isEscalate && <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />}
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-bold uppercase tracking-wider">
                    Authoritative Decision: {decision.decision_state}
                  </span>
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-white/70 dark:bg-black/30 border border-current/20">
                    {decision.decision_id}
                  </span>
                  {autonomyEvaluation && (
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-100 dark:bg-indigo-900/60 text-indigo-800 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-700">
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
              <span>{decision.decided_by}</span>
              <span className="text-[10px]">
                {decision.decided_at ? new Date(decision.decided_at).toLocaleTimeString() : ''}
              </span>
            </div>
          </div>

          {/* MODIFY Clamping Notice */}
          {hasClampedDiscount && (
            <div className="p-3 bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800 rounded-lg text-xs text-blue-900 dark:text-blue-200 flex items-start gap-2">
              <Shield className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">MODIFY Parameter Clamping Enforced:</span>
                <span className="block text-[11px] text-blue-700 dark:text-blue-300 mt-0.5">
                  Original proposed discount was ₹{originalDiscountStr}, clamped by guardrail to ₹{executedDiscountStr}.
                  The autonomy engine evaluates and authorizes strictly ₹{executedDiscountStr}. The unsafe ₹{originalDiscountStr} is NEVER executed.
                </span>
              </div>
            </div>
          )}

          {/* Autonomy & Sign-off Gate Area */}
          <div className="border border-slate-200 dark:border-slate-800 rounded-lg p-4 bg-slate-50/50 dark:bg-slate-800/40 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-2 border-b border-slate-200/80 dark:border-slate-700 gap-1.5">
              <div className="flex items-center gap-2">
                {isAutoApproved ? (
                  <Zap className="w-4 h-4 text-emerald-600" />
                ) : (
                  <UserCheck className="w-4 h-4 text-[#002E6E] dark:text-blue-400" />
                )}
                <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200">
                  {isAutoApproved ? 'Autonomous Clearance Gate' : 'Merchant Sign-off Gate'}
                </h3>
                <span className="text-[10px] bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 font-semibold px-1.5 py-0.5 rounded">
                  Mode: {autonomyEvaluation?.autonomy_mode || 'APPROVAL_REQUIRED'}
                </span>
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">Source:</span>
                <span
                  className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${
                    isAutoApproved
                      ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800'
                      : isHumanApproved
                      ? 'bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300 border border-blue-300 dark:border-blue-800'
                      : isRejected
                      ? 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300 border border-rose-300 dark:border-rose-800'
                      : 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-300 dark:border-amber-800'
                  }`}
                >
                  {autonomyEvaluation?.approval_source || decision.approval_status}
                </span>
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                    decision.is_execution_eligible
                      ? 'bg-emerald-600 text-white'
                      : 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400'
                  }`}
                >
                  {decision.is_execution_eligible ? 'EXECUTION ELIGIBLE' : 'EXECUTION INELIGIBLE'}
                </span>
              </div>
            </div>

            {/* AUTO-APPROVED Banner */}
            {isAutoApproved && autonomyEvaluation && (
              <div className="p-3 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 rounded-lg text-xs text-emerald-900 dark:text-emerald-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Zap className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                  <div>
                    <span className="font-bold">Auto-Approved by Deterministic Policy</span>
                    <span className="text-[11px] text-emerald-700 dark:text-emerald-300 block sm:inline sm:ml-2">
                      Evaluated Risk: <strong>{autonomyEvaluation.evaluated_risk.toFixed(2)}</strong> ≤ Policy Threshold: <strong>{autonomyEvaluation.policy_threshold.toFixed(2)}</strong>.
                      All 16 deterministic conditions verified.
                    </span>
                  </div>
                </div>
                <span className="text-[10px] font-mono text-emerald-800 dark:text-emerald-300 bg-emerald-100/80 dark:bg-emerald-900/60 px-2 py-0.5 rounded font-bold">
                  AUTONOMY_POLICY
                </span>
              </div>
            )}

            {/* Approved Parameters Preview */}
            {decision.approved_action ? (
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-md p-3 space-y-1.5">
                <div className="flex items-center justify-between text-xs font-bold text-slate-800 dark:text-slate-200">
                  <span>Authorized Execution Parameters:</span>
                  {isModify && (
                    <span className="text-[10px] text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40 px-2 py-0.5 rounded border border-blue-200 dark:border-blue-800">
                      Modified by Guardrails
                    </span>
                  )}
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                  <div className="p-1.5 bg-slate-50 dark:bg-slate-800/60 rounded border border-slate-100 dark:border-slate-800">
                    <span className="text-[10px] text-slate-400 block">Action Type</span>
                    <span className="font-semibold text-slate-700 dark:text-slate-300 truncate block">
                      {decision.approved_action.action_type}
                    </span>
                  </div>
                  <div className="p-1.5 bg-slate-50 dark:bg-slate-800/60 rounded border border-slate-100 dark:border-slate-800">
                    <span className="text-[10px] text-slate-400 block">Incentive / Cashback</span>
                    <span className="font-bold text-emerald-700 dark:text-emerald-400 block">
                      ₹{String(decision.approved_action.parameters?.discount_amount ?? decision.approved_action.incentive_value ?? proposal?.incentive_value ?? 0)}
                    </span>
                  </div>
                  <div className="p-1.5 bg-slate-50 dark:bg-slate-800/60 rounded border border-slate-100 dark:border-slate-800">
                    <span className="text-[10px] text-slate-400 block">Target Audience</span>
                    <span className="font-semibold text-slate-700 dark:text-slate-300 block">
                      {String(decision.approved_action.parameters?.target_count ?? decision.approved_action.target_customer_count ?? proposal?.target_customer_count ?? 0)} customers
                    </span>
                  </div>
                  <div className="p-1.5 bg-slate-50 dark:bg-slate-800/60 rounded border border-slate-100 dark:border-slate-800">
                    <span className="text-[10px] text-slate-400 block">Est. Budget</span>
                    <span className="font-semibold text-slate-700 dark:text-slate-300 block">
                      ₹{String(decision.approved_action.parameters?.budget_inr ?? decision.approved_action.estimated_cost_inr ?? proposal?.estimated_cost_inr ?? 0)}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-rose-50/50 dark:bg-rose-950/20 border border-rose-200/60 dark:border-rose-900/40 rounded-md p-3 text-xs text-rose-800 dark:text-rose-300 flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-rose-600 flex-shrink-0" />
                <span>
                  No approved action parameters exist. Action is strictly forbidden from executing.
                </span>
              </div>
            )}

            {/* Merchant Sign-off Action Buttons for Pending Human Review */}
            {decision.approval_status === 'PENDING' && !isBlock && !isEscalate && (
              <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-1">
                <div className="text-[11px] text-slate-500 dark:text-slate-400">
                  {autonomyEvaluation?.autonomy_mode === 'APPROVAL_REQUIRED'
                    ? 'Merchant review required under current policy mode. Clicking Approve authorizes execution.'
                    : `Action risk (${autonomyEvaluation?.evaluated_risk.toFixed(2)}) exceeds policy auto-approval threshold (${autonomyEvaluation?.policy_threshold.toFixed(2)}). Merchant review required.`}
                </div>
                <div className="flex items-center gap-2 w-full sm:w-auto">
                  <button
                    onClick={onReject}
                    disabled={isRejecting || isApproving}
                    className="flex-1 sm:flex-none inline-flex items-center justify-center gap-1 px-3.5 py-1.5 border border-rose-300 dark:border-rose-800 text-rose-700 dark:text-rose-300 hover:bg-rose-50 dark:hover:bg-rose-950/40 disabled:bg-slate-100 text-xs font-bold rounded-lg transition-colors cursor-pointer"
                  >
                    {isRejecting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <XCircle className="w-3.5 h-3.5" />}
                    Reject
                  </button>
                  <button
                    onClick={onApprove}
                    disabled={isApproving || isRejecting}
                    className="flex-1 sm:flex-none inline-flex items-center justify-center gap-1.5 px-4 py-1.5 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white text-xs font-bold rounded-lg shadow-sm transition-colors cursor-pointer"
                  >
                    {isApproving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                    Approve Action
                  </button>
                </div>
              </div>
            )}

            {/* BLOCK Decision Message */}
            {isBlock && (
              <div className="p-3 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 rounded-lg text-xs text-rose-900 dark:text-rose-200 space-y-1">
                <div className="font-bold flex items-center gap-1.5 text-rose-700 dark:text-rose-300">
                  <Lock className="w-4 h-4" />
                  Approval Strictly Prohibited (Hard Guardrail BLOCK)
                </div>
                <p className="text-[11px] text-rose-700/90 dark:text-rose-300/90 leading-relaxed">
                  Hard guardrail BLOCK cannot be bypassed under ANY autonomy mode (including FULL_AUTONOMY).
                  Neither merchant nor autonomy policy can authorize execution.
                </p>
              </div>
            )}

            {/* ESCALATE Decision Message */}
            {isEscalate && (
              <div className="p-3 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 rounded-lg text-xs text-amber-900 dark:text-amber-200 space-y-1">
                <div className="font-bold flex items-center gap-1.5 text-amber-700 dark:text-amber-300">
                  <AlertTriangle className="w-4 h-4" />
                  Manual Escalation Review Required
                </div>
                <p className="text-[11px] text-amber-700/90 dark:text-amber-300/90 leading-relaxed">
                  This action triggered high-risk policy boundary checks and requires manual intervention outside autonomous execution.
                </p>
              </div>
            )}

            {/* HUMAN APPROVED Success Banner */}
            {isHumanApproved && (
              <div className="p-3 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 rounded-lg text-xs text-emerald-900 dark:text-emerald-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <UserCheck className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                  <div>
                    <span className="font-bold">Merchant Sign-off Recorded (HUMAN_APPROVED)</span>
                    <span className="text-[11px] text-emerald-700 dark:text-emerald-300 block sm:inline sm:ml-2">
                      Signed off by merchant admin. Action is authorized and execution-eligible.
                    </span>
                  </div>
                </div>
                <span className="text-[10px] text-emerald-700 dark:text-emerald-300 font-mono bg-emerald-100/80 dark:bg-emerald-900/60 px-2 py-0.5 rounded">
                  {decision.approved_at ? new Date(decision.approved_at).toLocaleTimeString() : 'Approved'}
                </span>
              </div>
            )}

            {/* REJECTED Notice */}
            {isRejected && (
              <div className="p-3 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs text-slate-700 dark:text-slate-300 flex items-center gap-2">
                <XCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
                <span>Action rejected by merchant. Execution bypassed safely.</span>
              </div>
            )}

            {/* 16-Point Safety Conditions Checklist (Collapsible) */}
            {autonomyEvaluation && (
              <div className="pt-2 border-t border-slate-200 dark:border-slate-700">
                <button
                  type="button"
                  onClick={() => setShowChecklist(!showChecklist)}
                  className="flex items-center justify-between w-full text-xs font-semibold text-slate-700 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
                >
                  <span className="flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-indigo-500" />
                    16-Point Safety Policy Verification ({autonomyEvaluation.passed_checks.length}/16 Passed)
                  </span>
                  {showChecklist ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>

                {showChecklist && (
                  <div className="mt-2.5 space-y-1.5 text-[11px] bg-white dark:bg-slate-900 p-3 rounded-lg border border-slate-200 dark:border-slate-700">
                    {autonomyEvaluation.passed_checks.map((chk, i) => (
                      <div key={`pass-${i}`} className="flex items-start gap-1.5 text-emerald-700 dark:text-emerald-400">
                        <CheckCircle2 className="w-3 h-3 flex-shrink-0 mt-0.5" />
                        <span>{chk}</span>
                      </div>
                    ))}
                    {autonomyEvaluation.failed_checks.map((chk, i) => (
                      <div key={`fail-${i}`} className="flex items-start gap-1.5 text-rose-600 dark:text-rose-400 font-medium">
                        <XCircle className="w-3 h-3 flex-shrink-0 mt-0.5" />
                        <span>{chk}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Cryptographic Hash Integrity Footer */}
          <div className="pt-1 flex flex-wrap items-center justify-between text-[10px] text-slate-400 gap-2 border-t border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-1">
              <Hash className="w-3 h-3 text-slate-400" />
              <span>Proposal SHA-256:</span>
              <code className="font-mono text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded">
                {decision.proposal_hash ? `${decision.proposal_hash.slice(0, 16)}...` : 'N/A'}
              </code>
            </div>
            <div className="flex items-center gap-1">
              <Hash className="w-3 h-3 text-slate-400" />
              <span>Evaluation SHA-256:</span>
              <code className="font-mono text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded">
                {decision.evaluation_hash ? `${decision.evaluation_hash.slice(0, 16)}...` : 'N/A'}
              </code>
            </div>
            <div className="text-slate-400 font-medium">
              Deterministic Truth Verified
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
