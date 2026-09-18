'use client';

import React from 'react';
import { ActionProposal, GuardrailEvaluation, InvestigationResult } from '@/types';
import { Bot, ShieldCheck, Radio, Search, CheckCircle2, Sliders, ShieldAlert } from 'lucide-react';

interface MitraActivityAreaProps {
  investigation?: InvestigationResult | null;
  actionProposal?: ActionProposal | null;
  guardrailEvaluation?: GuardrailEvaluation | null;
  isInvestigating?: boolean;
  isPlanning?: boolean;
  isEvaluatingGuardrails?: boolean;
}

export const MitraActivityArea: React.FC<MitraActivityAreaProps> = ({
  investigation,
  actionProposal,
  guardrailEvaluation,
  isInvestigating = false,
  isPlanning = false,
  isEvaluatingGuardrails = false,
}) => {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-md bg-blue-100 text-[#002E6E]">
              <Bot className="w-4 h-4" />
            </div>
            <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">MITRA Teammate Activity</h2>
          </div>
          <span className="text-xs text-[#007EA7] font-semibold flex items-center gap-1">
            <Radio className="w-3.5 h-3.5 text-blue-600 animate-pulse" /> Live Telemetry
          </span>
        </div>

        <div className="space-y-3">
          {/* Step 1: Deterministic Signal Detection */}
          <div className="p-3 bg-blue-50/50 border-l-4 border-l-blue-600 border-r border-t border-b border-blue-200/80 rounded-r-lg">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-blue-950 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-blue-600" />
                1. DETERMINISTIC SIGNAL DETECTION COMPLETE
              </span>
              <span className="text-[10px] text-blue-700 font-mono font-medium">PHASE 3 VERIFIED</span>
            </div>
            <p className="text-xs text-slate-700 mt-1">
              5 deterministic detectors evaluated against SQLite digital twin. Detected <strong>EVENING_ORDER_DECLINE</strong> (-29.02% from 410 baseline to 291 observed orders) at <strong>HIGH</strong> severity. Facts verified mathematically.
            </p>
          </div>

          {/* Step 2: Phase 4 Root-Cause Investigation */}
          <div
            className={`p-3 border-l-4 border-r border-t border-b rounded-r-lg transition-colors ${
              investigation
                ? 'bg-indigo-50/40 border-l-indigo-600 border-indigo-200/80'
                : isInvestigating
                ? 'bg-blue-50/60 border-l-blue-500 border-blue-200'
                : 'bg-slate-50 border-l-amber-500 border-slate-200/80'
            }`}
          >
            <div className="flex items-center justify-between">
              <span
                className={`text-xs font-bold flex items-center gap-1.5 ${
                  investigation
                    ? 'text-indigo-950'
                    : isInvestigating
                    ? 'text-blue-950'
                    : 'text-amber-950'
                }`}
              >
                {investigation ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-indigo-600" />
                ) : (
                  <Search className={`w-3.5 h-3.5 ${isInvestigating ? 'animate-spin text-blue-600' : 'text-amber-600'}`} />
                )}
                2. EVIDENCE-BACKED INVESTIGATION
              </span>
              <span
                className={`text-[10px] font-mono font-medium ${
                  investigation
                    ? 'text-indigo-700'
                    : isInvestigating
                    ? 'text-blue-700'
                    : 'text-slate-400'
                }`}
              >
                {investigation ? 'PHASE 4 ACTIVE' : isInvestigating ? 'INVESTIGATING...' : 'READY'}
              </span>
            </div>
            <p className="text-xs text-slate-600 mt-1">
              {investigation ? (
                <>
                  Deterministic evidence bundle assembled (<strong>E1–E5</strong>). Generated{' '}
                  <strong className="text-indigo-950 font-bold">{investigation.hypotheses.length} validated hypotheses</strong> with{' '}
                  <strong className="text-indigo-950 font-bold">{investigation.confidence}</strong> confidence. Hallucination check passed; non-causal language preserved.
                </>
              ) : isInvestigating ? (
                <>
                  Synthesizing customer behavior telemetry (repeat conversion 18.2% &rarr; 14.8%) and campaign expiration history...
                </>
              ) : (
                <>
                  LLM investigation synthesizes customer segment history (486 target customers) and expiring campaign telemetry to determine associative factors and draft hypotheses.
                </>
              )}
            </p>
          </div>

          {/* Step 3: Phase 5 Candidate Action Proposal */}
          <div
            className={`p-3 border-l-4 border-r border-t border-b rounded-r-lg transition-colors ${
              actionProposal
                ? 'bg-emerald-50/40 border-l-emerald-600 border-emerald-200/80'
                : isPlanning
                ? 'bg-blue-50/60 border-l-blue-500 border-blue-200'
                : 'bg-slate-50 border-l-slate-400 border-slate-200/80'
            }`}
          >
            <div className="flex items-center justify-between">
              <span
                className={`text-xs font-bold flex items-center gap-1.5 ${
                  actionProposal
                    ? 'text-emerald-950'
                    : isPlanning
                    ? 'text-blue-950'
                    : 'text-slate-700'
                }`}
              >
                {actionProposal ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                ) : (
                  <Sliders className={`w-3.5 h-3.5 ${isPlanning ? 'animate-spin text-blue-600' : 'text-slate-400'}`} />
                )}
                3. CANDIDATE ACTION PROPOSAL
              </span>
              <span
                className={`text-[10px] font-mono font-medium ${
                  actionProposal
                    ? 'text-emerald-700'
                    : isPlanning
                    ? 'text-blue-700'
                    : 'text-slate-400'
                }`}
              >
                {actionProposal ? 'PHASE 5 PROPOSED' : isPlanning ? 'PLANNING...' : investigation ? 'READY TO PLAN' : 'AWAITING STEP 2'}
              </span>
            </div>
            <p className="text-xs text-slate-600 mt-1">
              {actionProposal ? (
                <>
                  Synthesized candidate <strong className="text-emerald-950 font-bold">{actionProposal.action_type}</strong> targeting{' '}
                  <strong className="text-emerald-950 font-bold">{actionProposal.target_customer_count ?? 486} customers</strong> with{' '}
                  <strong className="text-emerald-950 font-bold">₹{actionProposal.incentive_value?.toFixed(0) ?? '50'} cashback</strong>. Status: <strong className="text-amber-800 font-bold">PROPOSED</strong> (Safety Barrier engaged).
                </>
              ) : isPlanning ? (
                <>
                  Formulating bounded candidate action respecting merchant margin &ge; 10%, daily budget &le; ₹12,000, max discount &le; ₹100...
                </>
              ) : (
                <>
                  Candidate action synthesis will formulate targeted, evidence-backed campaigns within strict merchant constraints without premature execution.
                </>
              )}
            </p>
          </div>

          {/* Step 4: Deterministic Guardrails */}
          <div
            className={`p-3 border-l-4 border-r border-t border-b rounded-r-lg transition-colors ${
              guardrailEvaluation
                ? guardrailEvaluation.overall_status === 'PASS'
                  ? 'bg-emerald-50/50 border-l-emerald-600 border-emerald-200'
                  : guardrailEvaluation.overall_status === 'MODIFY'
                  ? 'bg-amber-50/50 border-l-amber-600 border-amber-200'
                  : 'bg-rose-50/50 border-l-rose-600 border-rose-200'
                : isEvaluatingGuardrails
                ? 'bg-blue-50/50 border-l-blue-500 border-blue-200'
                : 'bg-slate-50 border-l-amber-500 border-slate-200/80'
            }`}
          >
            <div className="flex items-center justify-between">
              <span
                className={`text-xs font-bold flex items-center gap-1.5 ${
                  guardrailEvaluation
                    ? guardrailEvaluation.overall_status === 'PASS'
                      ? 'text-emerald-950'
                      : guardrailEvaluation.overall_status === 'MODIFY'
                      ? 'text-amber-950'
                      : 'text-rose-950'
                    : 'text-amber-950'
                }`}
              >
                {guardrailEvaluation ? (
                  guardrailEvaluation.overall_status === 'PASS' ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  ) : guardrailEvaluation.overall_status === 'MODIFY' ? (
                    <Sliders className="w-3.5 h-3.5 text-amber-600" />
                  ) : (
                    <ShieldAlert className="w-3.5 h-3.5 text-rose-600" />
                  )
                ) : (
                  <ShieldCheck className="w-3.5 h-3.5 text-amber-600" />
                )}
                4. DETERMINISTIC GUARDRAILS
              </span>
              <span
                className={`text-[10px] font-mono font-medium ${
                  guardrailEvaluation
                    ? guardrailEvaluation.overall_status === 'PASS'
                      ? 'text-emerald-700'
                      : guardrailEvaluation.overall_status === 'MODIFY'
                      ? 'text-amber-700'
                      : 'text-rose-700'
                    : 'text-amber-700'
                }`}
              >
                {guardrailEvaluation
                  ? `PHASE 6 ${guardrailEvaluation.overall_status}`
                  : isEvaluatingGuardrails
                  ? 'EVALUATING...'
                  : actionProposal
                  ? 'READY TO EVALUATE'
                  : 'ARMED'}
              </span>
            </div>
            <p className="text-xs text-slate-600 mt-1">
              {guardrailEvaluation ? (
                <>
                  Executed 10 deterministic checks against SQLite constraints:{' '}
                  <strong className="text-slate-900 font-bold">{guardrailEvaluation.passed_checks.length} passed</strong>,{' '}
                  <strong className="text-slate-900 font-bold">{guardrailEvaluation.failed_checks.length} failed</strong>.{' '}
                  {guardrailEvaluation.notes || 'Status evaluated deterministically without LLM intervention.'}
                </>
              ) : (
                <>
                  Deterministic hard boundaries ready: Margin &ge; 10%, Daily budget &le; ₹12,000, Max discount &le; ₹100, Frequency &le; 3. Non-negotiable code safety barrier active.
                </>
              )}
            </p>
          </div>
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
        <span>Core Principle: Deterministic systems calculate truth; LLM interprets.</span>
        <span className="font-semibold text-[#002E6E]">
          {guardrailEvaluation
            ? `Phase 6 Evaluated (${guardrailEvaluation.overall_status})`
            : actionProposal
            ? 'Phase 5 Proposed'
            : investigation
            ? 'Phase 4 Grounded'
            : 'Phase 3 Verified'}
        </span>
      </div>
    </div>
  );
};


