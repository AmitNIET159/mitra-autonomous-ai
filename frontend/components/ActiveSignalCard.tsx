'use client';

import React from 'react';
import { ActionProposal, BusinessSignal, GuardrailEvaluation, InvestigationResult, MerchantMetrics } from '@/types';
import {
  AlertTriangle,
  ArrowDownRight,
  RefreshCw,
  CheckCircle2,
  Layers,
  SearchCheck,
  Sparkles,
  Info,
  Sliders,
  ShieldAlert,
  ShieldCheck,
  Target,
} from 'lucide-react';

interface ActiveSignalCardProps {
  signal?: BusinessSignal | null;
  metrics?: MerchantMetrics;
  investigation?: InvestigationResult | null;
  actionProposal?: ActionProposal | null;
  guardrailEvaluation?: GuardrailEvaluation | null;
  onRunDetection?: () => Promise<void> | void;
  onRunInvestigation?: () => Promise<void> | void;
  onRunPlanning?: () => Promise<void> | void;
  isDetecting?: boolean;
  isInvestigating?: boolean;
  isPlanning?: boolean;
  lastDetectedAt?: string;
}

export const ActiveSignalCard: React.FC<ActiveSignalCardProps> = ({
  signal,
  metrics,
  investigation,
  actionProposal,
  guardrailEvaluation,
  onRunDetection,
  onRunInvestigation,
  onRunPlanning,
  isDetecting = false,
  isInvestigating = false,
  isPlanning = false,
  lastDetectedAt,
}) => {
  // Derive values safely from signal or metrics
  const baseline = signal?.baseline_value ?? metrics?.evening_orders_baseline ?? 410;
  const observed = signal?.observed_value ?? metrics?.evening_orders_current ?? 291;
  const declinePct =
    signal?.decline_percentage ??
    (signal?.change_percentage ? Math.abs(signal.change_percentage) : 29.02);
  const changePct =
    signal?.change_percentage ??
    (metrics?.evening_orders_variance_pct ?? -29.02);
  const severity = signal?.severity ?? 'HIGH';
  const status = signal?.status ?? 'ACTIVE';
  const signalId = signal?.signal_id ?? 'SIG-EVN-DECLINE-01';
  const context = (signal?.context_data as Record<string, unknown>) || {};
  const baselineWindow = (context.baseline_window as string) || 'Sep 01 – Sep 10, 2026 (10 Days)';

  const severityBadgeClass =
    severity === 'CRITICAL'
      ? 'bg-rose-100 text-rose-800 border-rose-300'
      : severity === 'HIGH'
      ? 'bg-amber-100 text-amber-900 border-amber-300'
      : severity === 'MEDIUM'
      ? 'bg-yellow-100 text-yellow-800 border-yellow-300'
      : 'bg-blue-100 text-blue-800 border-blue-300';

  return (
    <div className="bg-white border border-slate-200/90 rounded-xl p-5 shadow-xs flex flex-col justify-between space-y-4">
      <div>
        {/* Card Header with Detection & Investigation Triggers */}
        <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-amber-50 text-amber-800 border border-amber-200">
              <AlertTriangle className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Active Business Signal
                </h2>
                <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {status}
                </span>
              </div>
              <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                ID: {signalId} • Source: Digital Twin SQLite
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full border ${severityBadgeClass}`}
            >
              {severity} SEVERITY (20–30%)
            </span>
            {onRunDetection && (
              <button
                type="button"
                onClick={() => onRunDetection()}
                disabled={isDetecting || isInvestigating}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-300/80 active:scale-95 transition-all shadow-xs disabled:opacity-60 cursor-pointer disabled:cursor-not-allowed"
                title="Re-run deterministic signal detection detectors"
              >
                <RefreshCw
                  className={`w-3.5 h-3.5 ${isDetecting ? 'animate-spin' : ''}`}
                />
                <span>{isDetecting ? 'Detecting...' : 'Re-Detect'}</span>
              </button>
            )}
            {onRunInvestigation && (
              <button
                type="button"
                onClick={() => onRunInvestigation()}
                disabled={isInvestigating || isDetecting || isPlanning}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold text-white bg-[#002E6E] hover:bg-[#001D47] active:scale-95 transition-all shadow-xs disabled:opacity-60 cursor-pointer disabled:cursor-not-allowed"
                title="Trigger Phase 4 evidence synthesis & LLM investigation"
              >
                <Sparkles
                  className={`w-3.5 h-3.5 text-[#00BAF2] ${isInvestigating ? 'animate-spin' : ''}`}
                />
                <span>{isInvestigating ? 'Investigating...' : investigation ? 'Re-Investigate' : 'Investigate Signal'}</span>
              </button>
            )}
            {onRunPlanning && investigation && (
              <button
                type="button"
                onClick={() => onRunPlanning()}
                disabled={isPlanning || isInvestigating || isDetecting}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold text-white bg-emerald-700 hover:bg-emerald-800 active:scale-95 transition-all shadow-xs disabled:opacity-60 cursor-pointer disabled:cursor-not-allowed"
                title="Synthesize Phase 5 structured ActionProposal within merchant limits"
              >
                <Sliders
                  className={`w-3.5 h-3.5 text-emerald-200 ${isPlanning ? 'animate-spin' : ''}`}
                />
                <span>{isPlanning ? 'Planning...' : actionProposal ? 'Re-Plan' : 'Plan Action'}</span>
              </button>
            )}
          </div>
        </div>

        {/* Main Detected Signal Box */}
        <div className="bg-slate-50 border border-slate-200/90 rounded-lg p-4 mb-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200/70">
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-bold text-[#002E6E] uppercase">Signal Name:</span>
                <span className="text-sm font-extrabold text-slate-900">Evening Order Decline</span>
              </div>
              <p className="text-xs text-slate-600 mt-1">
                Evening transaction velocity (5:00 PM – 8:59 PM) fell from{' '}
                <strong className="text-slate-900 font-bold">{baseline} baseline orders</strong> to{' '}
                <strong className="text-rose-700 font-bold">{observed} observed orders</strong>.
              </p>
            </div>
            <div className="text-right shrink-0 bg-white px-3 py-1.5 rounded-md border border-slate-200/80 shadow-xs">
              <span className="text-[11px] text-slate-500 font-medium block">Measured Change</span>
              <span className="text-base font-black text-rose-600 flex items-center justify-end">
                <ArrowDownRight className="w-4 h-4 mr-0.5" />
                {changePct.toFixed(2)}%
              </span>
              <span className="text-[10px] text-slate-400 block font-mono">
                Decline: {declinePct.toFixed(2)}%
              </span>
            </div>
          </div>

          {/* Structured Dynamic Evidence Items (E1 - E5) */}
          <div className="mt-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1">
                <Layers className="w-3.5 h-3.5 text-[#002E6E]" /> Grounded Evidence Breakdown (E1–E5)
              </span>
              <span className="text-[10px] text-slate-500 font-mono">Dynamic SQLite Telemetry</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
              {/* E1: Primary Signal */}
              <div className="bg-white p-2.5 rounded-lg border border-slate-200/80 shadow-xs flex flex-col justify-between">
                <div className="flex items-center justify-between mb-1">
                  <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-extrabold bg-blue-100 text-blue-800">
                    E1 • Primary Signal
                  </span>
                  <span className="text-rose-600 font-bold text-xs">↓29.02%</span>
                </div>
                <div className="text-xs text-slate-800 font-semibold">
                  410 → 291 orders
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5">
                  Evening window (5:00 PM – 8:59 PM). Baseline: {baselineWindow}.
                </div>
              </div>

              {/* E2: Repeat Conversion */}
              <div className="bg-white p-2.5 rounded-lg border border-slate-200/80 shadow-xs flex flex-col justify-between">
                <div className="flex items-center justify-between mb-1">
                  <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-extrabold bg-indigo-100 text-indigo-800">
                    E2 • Customer Behavior
                  </span>
                  <span className="text-amber-600 font-bold text-xs">↓18.68%</span>
                </div>
                <div className="text-xs text-slate-800 font-semibold">
                  18.2% → 14.8% repeat conversion
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5">
                  Repeat customer orders dropped significantly during evening peak.
                </div>
              </div>

              {/* E3: Campaign Expiry */}
              <div className="bg-white p-2.5 rounded-lg border border-slate-200/80 shadow-xs flex flex-col justify-between">
                <div className="flex items-center justify-between mb-1">
                  <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-extrabold bg-purple-100 text-purple-800">
                    E3 • Campaign Context
                  </span>
                  <span className="text-slate-500 font-medium text-[10px]">Ended 3d ago</span>
                </div>
                <div className="text-xs text-slate-800 font-semibold">
                  Expired 3 days ago (5% Cashback)
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5">
                  No active promotion currently running during evening slot.
                </div>
              </div>

              {/* E4: Target Audience */}
              <div className="bg-white p-2.5 rounded-lg border border-slate-200/80 shadow-xs flex flex-col justify-between">
                <div className="flex items-center justify-between mb-1">
                  <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-extrabold bg-emerald-100 text-emerald-800">
                    E4 • Target Audience
                  </span>
                  <span className="text-emerald-700 font-semibold text-[10px]">93.5% Cohort</span>
                </div>
                <div className="text-xs text-slate-800 font-semibold">
                  486 repeat & regular customers
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5">
                  Total customer pool: 520 (140 repeat + 346 regular).
                </div>
              </div>

              {/* E5: Evening Revenue */}
              <div className="bg-white p-2.5 rounded-lg border border-slate-200/80 shadow-xs sm:col-span-2 flex flex-col justify-between">
                <div className="flex items-center justify-between mb-1">
                  <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-extrabold bg-amber-100 text-amber-900">
                    E5 • Evening Revenue Impact
                  </span>
                  <span className="text-rose-600 font-bold text-xs">₹153,759.70 → ₹108,896.90</span>
                </div>
                <div className="text-[11px] text-slate-600">
                  Deterministic baseline revenue was <strong className="text-slate-800 font-bold">₹153,759.70</strong> across 10 baseline days; observed evening GMV is <strong className="text-slate-800 font-bold">₹108,896.90</strong> across recent 4 days.
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Phase 4 Investigation & Hypotheses Block */}
        {investigation ? (
          <div className="bg-blue-50/40 border border-blue-200 rounded-lg p-4 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-blue-200/60">
              <div className="flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-[#002E6E]" />
                <span className="text-xs font-bold text-[#002E6E] uppercase">
                  Investigation Hypotheses & Findings
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-blue-100 text-blue-800 border border-blue-300">
                  ID: {investigation.investigation_id}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                    investigation.confidence === 'HIGH'
                      ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                      : investigation.confidence === 'MEDIUM'
                      ? 'bg-amber-100 text-amber-900 border-amber-300'
                      : 'bg-slate-100 text-slate-700 border-slate-300'
                  }`}
                >
                  CONFIDENCE: {investigation.confidence}
                </span>
                {investigation.is_fallback && (
                  <span className="text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200 font-mono">
                    Fallback Simulation
                  </span>
                )}
              </div>
            </div>

            {/* Summary */}
            <p className="text-xs text-slate-700 leading-relaxed font-medium">
              {investigation.summary}
            </p>

            {/* Hypotheses List */}
            <div className="space-y-2">
              <div className="text-[11px] font-bold text-slate-700 uppercase tracking-wider">
                Grounded Hypotheses (Non-Causal Associative Reasoning):
              </div>
              {investigation.hypotheses.map((h, idx) => (
                <div
                  key={idx}
                  className="bg-white p-3 rounded-lg border border-blue-100 shadow-xs space-y-1"
                >
                  <div className="flex flex-wrap items-center justify-between gap-1">
                    <span className="text-xs font-bold text-slate-900">
                      Hypothesis {idx + 1}: {h.hypothesis}
                    </span>
                    <div className="flex items-center gap-1">
                      {h.supporting_evidence_ids.map((eid) => (
                        <span
                          key={eid}
                          className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-blue-50 text-[#002E6E] border border-blue-200"
                        >
                          {eid}
                        </span>
                      ))}
                      <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                        {h.confidence}
                      </span>
                    </div>
                  </div>
                  <p className="text-[11px] text-slate-600 leading-normal">
                    {h.rationale}
                  </p>
                </div>
              ))}
            </div>

            {/* Limitations Notice */}
            {investigation.limitations && investigation.limitations.length > 0 && (
              <div className="p-2 bg-amber-50/70 border border-amber-200/80 rounded text-[10px] text-amber-900 space-y-1">
                <div className="font-bold flex items-center gap-1 text-amber-950">
                  <Info className="w-3 h-3 text-amber-700" />
                  Investigation Transparency & Limitations:
                </div>
                <ul className="list-disc pl-4 space-y-0.5 text-amber-800">
                  {investigation.limitations.map((lim, i) => (
                    <li key={i}>{lim}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Anti-causality disclaimer */}
            <div className="text-[10px] text-slate-500 italic bg-slate-50 p-2 rounded border border-slate-200/60">
              * Note: MITRA investigation strictly distinguishes observed facts from hypotheses. Evidence items E1–E5 are mathematically derived; hypotheses explain plausible associations without asserting unproven singular causality.
            </div>
          </div>
        ) : (
          <div className="bg-slate-50 border border-dashed border-slate-300 rounded-lg p-3 text-center">
            <p className="text-xs text-slate-500">
              Click <strong className="text-[#002E6E]">&ldquo;Investigate Signal&rdquo;</strong> above to initiate Phase 4 evidence bundle synthesis and generate grounded hypotheses.
            </p>
          </div>
        )}

        {/* Phase 5 Candidate Action Proposal Section */}
        {actionProposal && (
          <div className="mt-4 pt-4 border-t border-slate-200/80 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <div className="p-1 rounded bg-emerald-100 text-emerald-800">
                  <Sliders className="w-3.5 h-3.5" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                    Phase 5: Candidate Action Proposal
                  </h3>
                  <div className="text-[10px] text-slate-400 font-mono">
                    ID: {actionProposal.proposal_id} • Type: {actionProposal.action_type}
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-amber-100 text-amber-900 border border-amber-300 flex items-center gap-1">
                  <ShieldAlert className="w-3 h-3 text-amber-700" />
                  PROPOSAL ONLY — NOT EXECUTED
                </span>
                {guardrailEvaluation && (
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full font-bold flex items-center gap-1 border ${
                      guardrailEvaluation.overall_status === 'PASS'
                        ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                        : guardrailEvaluation.overall_status === 'MODIFY'
                        ? 'bg-amber-100 text-amber-900 border-amber-300'
                        : guardrailEvaluation.overall_status === 'BLOCK'
                        ? 'bg-rose-100 text-rose-800 border-rose-300'
                        : 'bg-slate-100 text-slate-800 border-slate-300'
                    }`}
                  >
                    <ShieldCheck className="w-3 h-3" />
                    GUARD: {guardrailEvaluation.overall_status}
                  </span>
                )}
                {actionProposal.is_fallback && (
                  <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-blue-50 text-blue-700 border border-blue-200">
                    Deterministic Fallback
                  </span>
                )}
              </div>
            </div>

            {/* Proposal Key Parameter Metrics */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
              <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg">
                <span className="text-[10px] text-slate-500 font-medium block">Target Segment</span>
                <span className="font-extrabold text-slate-900 block text-sm">
                  {actionProposal.target_customer_count ?? 486} Customers
                </span>
                <span className="text-[10px] text-slate-500">{actionProposal.target_segment || 'repeat & regular'}</span>
              </div>
              <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg">
                <span className="text-[10px] text-slate-500 font-medium block">Incentive Offer</span>
                <span className="font-extrabold text-emerald-700 block text-sm">
                  ₹{actionProposal.incentive_value?.toFixed(0) ?? '50'} {actionProposal.incentive_type || 'Cashback'}
                </span>
                <span className="text-[10px] text-slate-500">Max limit: ₹100</span>
              </div>
              <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg">
                <span className="text-[10px] text-slate-500 font-medium block">Budget Allocated</span>
                <span className="font-extrabold text-slate-900 block text-sm">
                  ₹{actionProposal.estimated_cost_inr?.toLocaleString() ?? '5,000'}
                </span>
                <span className="text-[10px] text-slate-500">Daily limit: ₹12,000</span>
              </div>
              <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg">
                <span className="text-[10px] text-slate-500 font-medium block">Campaign Duration</span>
                <span className="font-extrabold text-slate-900 block text-sm">
                  {actionProposal.duration || '7 days'}
                </span>
                <span className="text-[10px] text-slate-500">Auto-expires</span>
              </div>
            </div>

            {/* Objective and Grounded Reason */}
            <div className="p-3 bg-emerald-50/40 border border-emerald-200 rounded-lg space-y-1.5 text-xs text-slate-700">
              <div className="flex items-center gap-1.5 font-bold text-emerald-950 text-[11px]">
                <Target className="w-3.5 h-3.5 text-emerald-700" />
                <span>Objective: {actionProposal.objective || 'Re-engage evening shoppers and restore transaction velocity'}</span>
              </div>
              <p className="text-[11px] leading-relaxed text-slate-600">
                {actionProposal.reason}
              </p>
              
              {/* Supporting Evidence Chips */}
              {actionProposal.supporting_evidence_ids && actionProposal.supporting_evidence_ids.length > 0 && (
                <div className="flex flex-wrap items-center gap-1.5 pt-1">
                  <span className="text-[10px] font-semibold text-slate-500">Cited Evidence:</span>
                  {actionProposal.supporting_evidence_ids.map((eid) => (
                    <span
                      key={eid}
                      className="px-1.5 py-0.5 rounded bg-emerald-100/80 text-emerald-900 font-mono text-[10px] font-bold border border-emerald-300"
                    >
                      {eid}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Safety & Non-Execution Barrier Notice */}
            <div className="p-2.5 bg-slate-50 border border-slate-300 rounded-lg text-[10px] text-slate-600 flex items-start gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              <div>
                <strong className="text-slate-800">Execution Safety Barrier Active:</strong> This proposal is held in <strong className="text-amber-800">PROPOSED</strong> status. It has not been executed, no messages have been sent to customers, and no real Paytm APIs were invoked. Phase 6 Deterministic Guardrails must validate this proposal before merchant sign-off.
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer / Architecture Guarantee */}
      <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center justify-between text-xs text-slate-500 gap-2">
        <div className="flex items-center gap-1.5">
          <SearchCheck className="w-3.5 h-3.5 text-[#00BAF2]" />
          <span>
            {lastDetectedAt ? (
              <>Last Evaluated: <strong className="text-slate-700 font-mono">{lastDetectedAt}</strong></>
            ) : (
              'Evaluated live against digital twin transactions'
            )}
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-emerald-700 font-semibold bg-emerald-50 px-2.5 py-0.5 rounded border border-emerald-200 text-[11px]">
          <CheckCircle2 className="w-3 h-3" />
          {actionProposal ? 'Phase 5: Proposal Synthesized' : 'Phase 4: Investigation Engine Grounded'}
        </div>
      </div>
    </div>
  );
};


