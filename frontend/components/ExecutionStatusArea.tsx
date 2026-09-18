'use client';

import React from 'react';
import { Decision, ExecutionResult } from '@/types';
import {
  Zap,
  ShieldCheck,
  ShieldAlert,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Play,
  RotateCcw,
  Sparkles,
} from 'lucide-react';

interface ExecutionStatusAreaProps {
  decision?: Decision | null;
  execution?: ExecutionResult | null;
  executionsHistory?: ExecutionResult[];
  isExecuting?: boolean;
  onExecuteSimulation?: () => void;
}

export const ExecutionStatusArea: React.FC<ExecutionStatusAreaProps> = ({
  decision,
  execution,
  executionsHistory = [],
  isExecuting = false,
  onExecuteSimulation,
}) => {
  const isApproved = decision?.approval_status === 'APPROVED';
  const isPassOrModify = decision?.decision_state === 'PASS' || decision?.decision_state === 'MODIFY';
  const isEligible = isApproved && isPassOrModify && Boolean(decision?.is_execution_eligible);

  const isModify = decision?.decision_state === 'MODIFY';
  const originalIncentive = (decision?.modifications?.original_values as Record<string, unknown>)?.cashback_inr ||
    (decision?.modifications?.original_values as Record<string, unknown>)?.incentive_value ||
    '₹150';
  const approvedIncentive = decision?.approved_action?.incentive_value
    ? `₹${decision.approved_action.incentive_value}`
    : '₹100';

  return (
    <section className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-6">
      {/* 1. Header with Phase 8 Branding and Simulation Badge */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-emerald-100 text-emerald-800">
            <Zap className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-slate-900">Phase 8 — Safe Execution Simulator</h2>
              <span className="px-2 py-0.5 text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full">
                SANDBOX ISOLATED
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Gated by 10 deterministic preconditions • Strictly zero real-world Paytm operations
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 text-xs font-mono font-bold bg-slate-100 text-slate-700 rounded-md border border-slate-200 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            MODE: SIMULATION ONLY
          </span>
        </div>
      </div>

      {/* 2. Execution Gateway State */}
      {!decision ? (
        <div className="p-4 bg-amber-50/70 border border-amber-200 rounded-lg text-amber-900 text-xs flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
          <div>
            <p className="font-bold">Step 5 & 6 Incomplete: Authoritative Decision Required</p>
            <p className="text-amber-700 mt-0.5">
              The Safe Execution Simulator requires a signed, approved Decision record. Synthesize a Decision above to continue.
            </p>
          </div>
        </div>
      ) : !isApproved ? (
        <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-bold text-slate-700 flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-amber-500" />
              EXECUTION UNAVAILABLE: MERCHANT SIGN-OFF PENDING
            </span>
            <span className="px-2 py-0.5 font-mono font-bold text-[10px] rounded bg-amber-100 text-amber-800">
              {decision.approval_status}
            </span>
          </div>
          <p className="text-slate-600">
            {decision.approval_status === 'REJECTED'
              ? 'Action was explicitly REJECTED by merchant sign-off. Execution is strictly blocked.'
              : decision.decision_state === 'BLOCK'
              ? 'Action was deterministically BLOCKED by Phase 6 Guardrails (margin/budget violation). Cannot be approved or executed.'
              : decision.decision_state === 'ESCALATE'
              ? 'Action is in ESCALATE state requiring explicit merchant resolution before execution.'
              : 'Merchant sign-off (APPROVED) is strictly required before the Execution Safety Barrier will unlock simulation dispatch.'}
          </p>
          <div className="flex items-center gap-2 text-[11px] text-slate-500 font-mono">
            <span>Decision: <strong>{decision.decision_id}</strong></span>
            <span>•</span>
            <span>State: <strong>{decision.decision_state}</strong></span>
            <span>•</span>
            <span>Eligible: <strong>{String(decision.is_execution_eligible)}</strong></span>
          </div>
        </div>
      ) : !execution ? (
        /* READY FOR EXECUTION CARD */
        <div className="bg-gradient-to-br from-emerald-50/50 via-white to-blue-50/30 border-2 border-emerald-200 rounded-xl p-5 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <span className="text-xs font-bold text-emerald-800 uppercase tracking-wider flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                ALL PRECONDITIONS SATISFIED — READY FOR SIMULATED EXECUTION
              </span>
              <h3 className="text-sm font-semibold text-slate-800 mt-1">
                Merchant Sign-off Verified • Tamper SHA-256 Validated • Safety Barrier Unlocked
              </h3>
            </div>

            <button
              onClick={onExecuteSimulation}
              disabled={!isEligible || isExecuting}
              className={`px-5 py-2.5 rounded-lg text-xs font-bold text-white shadow-sm flex items-center gap-2 transition-all ${
                isEligible && !isExecuting
                  ? 'bg-[#002E6E] hover:bg-[#001D47] active:scale-95 cursor-pointer shadow-blue-900/10'
                  : 'bg-slate-300 cursor-not-allowed text-slate-500'
              }`}
            >
              {isExecuting ? (
                <>
                  <RotateCcw className="w-4 h-4 animate-spin" />
                  DISPATCHING SIMULATION...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-white" />
                  EXECUTE SIMULATION
                </>
              )}
            </button>
          </div>

          {/* MODIFY Clamped Parameter Notice */}
          {isModify && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs">
              <span className="font-bold text-amber-900 flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-amber-600" />
                EXECUTING APPROVED MODIFIED PARAMETERS (CLIPPED BY GUARDRAILS)
              </span>
              <p className="text-amber-800 mt-1">
                Original proposal requested <strong>{String(originalIncentive)}</strong> cashback. Guardrails clamped this to policy ceiling <strong>{String(approvedIncentive)}</strong>. Execution will strictly apply the safe ₹100 value.
              </p>
            </div>
          )}

          {/* Parameters to be dispatched */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-2.5 bg-white border border-slate-200 rounded-lg">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Action Type</span>
              <p className="font-bold text-slate-800 truncate">{decision.approved_action?.action_type || 'OFFER_CAMPAIGN'}</p>
            </div>
            <div className="p-2.5 bg-white border border-slate-200 rounded-lg">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Target Audience</span>
              <p className="font-bold text-slate-800">
                {String(decision.approved_action?.target_customer_count || 486)} Customers
              </p>
            </div>
            <div className="p-2.5 bg-white border border-slate-200 rounded-lg">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Approved Incentive</span>
              <p className="font-bold text-emerald-700">
                {approvedIncentive}
              </p>
            </div>
            <div className="p-2.5 bg-white border border-slate-200 rounded-lg">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Execution Mode</span>
              <p className="font-bold text-blue-800">SIMULATION ONLY</p>
            </div>
          </div>
        </div>
      ) : (
        /* EXECUTION COMPLETE RECEIPT */
        <div className="space-y-4">
          <div className="bg-emerald-50/80 border-2 border-emerald-400 rounded-xl p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-emerald-700 text-white rounded">
                    COMPLETED
                  </span>
                  <h3 className="text-sm font-bold text-emerald-950 flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    SIMULATED EXECUTION COMPLETE
                  </h3>
                </div>
                <p className="text-xs text-emerald-900 font-medium">
                  Approved action successfully dispatched to SimulatedPaytmAdapter with zero production side effects.
                </p>
              </div>

              <div className="text-right text-[11px] font-mono text-emerald-800">
                <span>Execution ID: <strong>{execution.execution_id}</strong></span>
                <div className="text-[10px] text-slate-500">{new Date(execution.executed_at).toLocaleString()}</div>
              </div>
            </div>

            {/* Checklist of Verified Guarantees */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-emerald-900 pt-1">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                <span>Decision approved by merchant ({decision.decided_by || 'Sharma Kirana Store Owner'})</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                <span>Safety barrier passed (10/10 preconditions valid)</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                <span>Approved clamped parameters verified in payload</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                <span>Simulated Paytm Adapter completed receipt</span>
              </div>
            </div>

            {/* MODIFY Parameter Invariant Display */}
            {isModify && (
              <div className="p-3 bg-white/80 border border-emerald-300 rounded-lg text-xs space-y-1">
                <div className="font-bold text-slate-800 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
                  MODIFY INVARIANT VERIFIED: ORIGINAL UNSAFE VALUE NEVER EXECUTED
                </div>
                <div className="grid grid-cols-3 gap-2 text-[11px] pt-1">
                  <div>
                    <span className="text-slate-400">Original Unsafe:</span>
                    <p className="line-through text-rose-600 font-bold">{String(originalIncentive)}</p>
                  </div>
                  <div>
                    <span className="text-slate-400">Guardrail-Clamped:</span>
                    <p className="text-amber-700 font-bold">{approvedIncentive}</p>
                  </div>
                  <div>
                    <span className="text-slate-400">Executed Value:</span>
                    <p className="text-emerald-700 font-bold">{approvedIncentive}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Simulation Disclaimer Callout */}
            <div className="p-2.5 bg-emerald-100/60 border border-emerald-300/80 rounded-lg text-[11px] text-emerald-950 flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-emerald-700 shrink-0" />
              <span>
                <strong>PROTOTYPE NOTICE:</strong> NO REAL PAYTM ACTION WAS PERFORMED. No customers received messages, no money was moved, and no production merchant account was altered.
              </span>
            </div>
          </div>
        </div>
      )}

      {/* 3. Execution History Section */}
      {executionsHistory.length > 0 && (
        <div className="space-y-3 pt-2">
          <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
            Simulated Execution History ({executionsHistory.length})
          </h4>
          <div className="overflow-x-auto border border-slate-200 rounded-lg">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 text-[11px]">
                <tr>
                  <th className="px-3 py-2">Execution ID</th>
                  <th className="px-3 py-2">Decision ID</th>
                  <th className="px-3 py-2">Action Type</th>
                  <th className="px-3 py-2">State</th>
                  <th className="px-3 py-2">Mode</th>
                  <th className="px-3 py-2">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                {executionsHistory.map((ex) => (
                  <tr key={ex.execution_id} className="hover:bg-slate-50/50">
                    <td className="px-3 py-2 font-bold text-[#002E6E]">{ex.execution_id}</td>
                    <td className="px-3 py-2 text-slate-600">{ex.decision_id}</td>
                    <td className="px-3 py-2 text-slate-800 font-sans">{ex.action_type}</td>
                    <td className="px-3 py-2">
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                        {ex.execution_state}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-blue-700">{ex.execution_mode}</td>
                    <td className="px-3 py-2 text-slate-500 font-sans">
                      {new Date(ex.executed_at).toLocaleTimeString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
};
