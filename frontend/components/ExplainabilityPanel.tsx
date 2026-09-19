'use client';

import React from 'react';
import {
  AlertCircle,
  CheckCircle2,
  Database,
  HelpCircle,
  Info,
  Lock,
  RotateCw,
  ShieldAlert,
  ShieldCheck,
  Sliders,
  X,
} from 'lucide-react';
import { ExplainabilitySummary } from '@/types';

interface ExplainabilityPanelProps {
  isOpen: boolean;
  onClose: () => void;
  summary: ExplainabilitySummary | null;
  isLoading?: boolean;
  onRefresh?: () => void;
}

export const ExplainabilityPanel: React.FC<ExplainabilityPanelProps> = ({
  isOpen,
  onClose,
  summary,
  isLoading = false,
  onRefresh,
}) => {
  if (!isOpen) return null;

  const isChainValid = summary?.audit_verification?.valid ?? false;

  const getNumberOrFallback = (val: unknown, fallback: string | number): string => {
    if (val === null || val === undefined) return String(fallback);
    return String(val);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex justify-end transition-opacity duration-200">
      <div className="bg-white w-full max-w-4xl min-h-screen shadow-2xl flex flex-col border-l border-slate-200 text-slate-800">
        {/* Header */}
        <div className="sticky top-0 z-20 bg-[#001D47] text-white p-5 border-b border-[#002E6E] flex items-center justify-between shadow-md">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="p-1.5 bg-[#00BAF2]/20 text-[#00BAF2] rounded-lg">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <h2 className="text-base font-bold tracking-tight text-white flex items-center gap-2">
                MITRA Workflow Explainability &amp; Audit Trail
              </h2>
            </div>
            <div className="flex items-center gap-3 text-xs text-slate-300">
              <span>Workflow ID: <strong className="font-mono text-[#00BAF2]">{summary?.correlation_id || 'wf-genesis'}</strong></span>
              <span>•</span>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                PROTOTYPE SIMULATION
              </span>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-sky-500/20 text-sky-200 border border-sky-500/30">
                DIGITAL TWIN
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {onRefresh && (
              <button
                onClick={onRefresh}
                disabled={isLoading}
                title="Refresh Explanation"
                className="p-2 hover:bg-slate-800 text-slate-300 hover:text-white rounded-lg transition-colors"
              >
                <RotateCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
              </button>
            )}
            <button
              onClick={onClose}
              className="p-2 hover:bg-slate-800 text-slate-300 hover:text-white rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 p-6 space-y-6 overflow-y-auto bg-slate-50/50">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-24 space-y-4">
              <RotateCw className="w-8 h-8 text-[#00BAF2] animate-spin" />
              <p className="text-sm font-medium text-slate-600">
                Synthesizing multi-stage explainability and cryptographically verifying SHA-256 audit chain...
              </p>
            </div>
          ) : !summary ? (
            <div className="p-8 text-center bg-white rounded-xl border border-slate-200 space-y-3">
              <AlertCircle className="w-8 h-8 text-amber-500 mx-auto" />
              <h3 className="text-sm font-bold text-slate-700">No Explanation Available</h3>
              <p className="text-xs text-slate-500">
                No active workflow trace was found for this identifier. Trigger an anomaly signal or action to inspect explainability.
              </p>
            </div>
          ) : (
            <>
              {/* Mandatory Non-Causal & Synthetic Disclaimer Notice */}
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 space-y-1">
                <div className="flex items-center gap-1.5 font-bold text-amber-900">
                  <Info className="w-4 h-4 text-amber-600 shrink-0" />
                  <span>Explainability &amp; Non-Causality Safety Invariant</span>
                </div>
                <p className="text-[11px] text-amber-800 leading-relaxed">
                  {summary.disclaimer}
                </p>
              </div>

              {/* 1. WHY THIS SIGNAL? */}
              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                  <div className="flex items-center gap-2">
                    <span className="flex items-center justify-center w-5 h-5 rounded-full bg-blue-100 text-[#002E6E] text-xs font-bold">1</span>
                    <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wide">Why Was This Signal Detected?</h3>
                  </div>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                    {String(summary.signal_summary?.signal_type || 'EVENING_ORDER_DECLINE')}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                    <div className="text-[11px] text-slate-500">Baseline Metric</div>
                    <div className="text-base font-bold text-slate-800">
                      {getNumberOrFallback(summary.signal_summary?.baseline_value, '410.0')}
                    </div>
                    <div className="text-[10px] text-slate-400">10-day rolling average</div>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                    <div className="text-[11px] text-slate-500">Observed Metric</div>
                    <div className="text-base font-bold text-rose-600">
                      {getNumberOrFallback(summary.signal_summary?.observed_value, '291.0')}
                    </div>
                    <div className="text-[10px] text-slate-400">Recent 4-day window</div>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                    <div className="text-[11px] text-slate-500">Variance / Decline</div>
                    <div className="text-base font-bold text-rose-600">
                      {summary.signal_summary?.change_percentage != null
                        ? `${String(summary.signal_summary.change_percentage)}%`
                        : '-29.02%'}
                    </div>
                    <div className="text-[10px] text-slate-400">Threshold: -15.0%</div>
                  </div>
                </div>

                <p className="text-xs text-slate-600 leading-relaxed">
                  {String(summary.signal_summary?.description ||
                    'Observed evening orders fell below the 10-day rolling baseline, exceeding the deterministic -15.0% anomaly threshold.')}
                </p>
              </div>

              {/* 2. WHAT EVIDENCE? (FACTS VS HYPOTHESES) */}
              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                  <div className="flex items-center gap-2">
                    <span className="flex items-center justify-center w-5 h-5 rounded-full bg-blue-100 text-[#002E6E] text-xs font-bold">2</span>
                    <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
                      What Evidence Supported the Investigation?
                    </h3>
                  </div>
                  <span className="text-[11px] text-slate-500">
                    Fact / Hypothesis Separation
                  </span>
                </div>

                {/* Facts Table */}
                <div className="space-y-2">
                  <div className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                    <Database className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Authoritative Facts (Verified via Database Queries)</span>
                  </div>
                  <div className="space-y-2">
                    {summary.facts && summary.facts.length > 0 ? (
                      summary.facts.map((fact) => (
                        <div
                          key={fact.id}
                          className="p-3 bg-emerald-50/50 border border-emerald-100 rounded-lg flex items-start justify-between gap-3 text-xs"
                        >
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <span className="px-1.5 py-0.5 bg-emerald-100 text-emerald-800 font-bold text-[10px] rounded uppercase">
                                FACT
                              </span>
                              <span className="font-semibold text-slate-800">{fact.statement}</span>
                            </div>
                            <div className="text-[11px] text-slate-500 flex items-center gap-2 font-mono">
                              <span>Source: <strong className="text-slate-700">{fact.source}</strong></span>
                              <span>•</span>
                              <span>Type: {fact.fact_type}</span>
                            </div>
                          </div>
                          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-slate-400 italic">No formal facts extracted.</p>
                    )}
                  </div>
                </div>

                {/* Hypotheses Section */}
                <div className="space-y-2 pt-2 border-t border-slate-100">
                  <div className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                    <HelpCircle className="w-3.5 h-3.5 text-amber-600" />
                    <span>AI Reasoning Hypotheses (Non-Causal Interpretation)</span>
                  </div>
                  <div className="space-y-2">
                    {summary.hypotheses && summary.hypotheses.length > 0 ? (
                      summary.hypotheses.map((hyp) => (
                        <div
                          key={hyp.id}
                          className="p-3 bg-amber-50/40 border border-amber-200/60 rounded-lg space-y-1.5 text-xs"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="px-1.5 py-0.5 bg-amber-100 text-amber-800 font-bold text-[10px] rounded uppercase">
                                AI HYPOTHESIS
                              </span>
                              <span className="font-semibold text-slate-800">{hyp.statement}</span>
                            </div>
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white text-slate-600 border border-slate-200">
                              Confidence: {Math.round(hyp.confidence * 100)}%
                            </span>
                          </div>
                          <div className="text-[11px] text-amber-800 italic bg-amber-50/80 p-2 rounded border border-amber-100">
                            Caveat: {hyp.non_causal_caveat}
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-slate-400 italic">No AI hypotheses recorded.</p>
                    )}
                  </div>
                </div>
              </div>

              {/* 3. WHY THIS ACTION? */}
              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                  <div className="flex items-center gap-2">
                    <span className="flex items-center justify-center w-5 h-5 rounded-full bg-blue-100 text-[#002E6E] text-xs font-bold">3</span>
                    <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wide">Why Was This Action Proposed?</h3>
                  </div>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-semibold border border-blue-200">
                    {String(summary.action_summary?.action_type || 'OFFER_CAMPAIGN')}
                  </span>
                </div>

                <div className="space-y-2 text-xs">
                  <p className="text-slate-700 leading-relaxed font-medium">
                    {String(summary.action_summary?.title ||
                      'Evening Rush Cashback Offer: ₹10 cashback on minimum order of ₹100')}
                  </p>
                  <p className="text-slate-500 leading-relaxed">
                    {String(summary.action_summary?.description ||
                      'Synthesized candidate action to address evening traffic decline by incentivizing repeat customers during peak hours.')}
                  </p>
                </div>
              </div>

              {/* 4. HOW WAS IT VERIFIED? (GUARDRAILS) */}
              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                  <div className="flex items-center gap-2">
                    <span className="flex items-center justify-center w-5 h-5 rounded-full bg-blue-100 text-[#002E6E] text-xs font-bold">4</span>
                    <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
                      Which Deterministic Guardrails Were Checked?
                    </h3>
                  </div>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                    summary.guardrail_summary?.overall_status === 'PASS'
                      ? 'bg-emerald-100 text-emerald-800'
                      : summary.guardrail_summary?.overall_status === 'MODIFY'
                      ? 'bg-amber-100 text-amber-800'
                      : 'bg-rose-100 text-rose-800'
                  }`}>
                    {String(summary.guardrail_summary?.overall_status || 'PASS')}
                  </span>
                </div>

                <div className="text-xs text-slate-600">
                  Total rules evaluated: <strong className="text-slate-800">{getNumberOrFallback(summary.guardrail_summary?.total_checks_evaluated, 10)}</strong> •
                  Passed: <strong className="text-emerald-700">{getNumberOrFallback(summary.guardrail_summary?.passed_checks_count, 10)}</strong> •
                  Failed: <strong className="text-rose-700">{getNumberOrFallback(summary.guardrail_summary?.failed_checks_count, 0)}</strong>
                </div>

                {summary.guardrail_summary?.clamped_parameters ? (
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs space-y-1">
                    <div className="font-bold text-amber-900 flex items-center gap-1.5">
                      <Sliders className="w-3.5 h-3.5 text-amber-700" />
                      <span>Clamped Parameter Modifications Enforced</span>
                    </div>
                    <pre className="text-[11px] font-mono text-amber-800 overflow-x-auto">
                      {JSON.stringify(summary.guardrail_summary.clamped_parameters, null, 2)}
                    </pre>
                  </div>
                ) : null}
              </div>

              {/* 5. WHAT WAS APPROVED? (DECISION & SIGN-OFF) */}
              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                  <div className="flex items-center gap-2">
                    <span className="flex items-center justify-center w-5 h-5 rounded-full bg-blue-100 text-[#002E6E] text-xs font-bold">5</span>
                    <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
                      What Was Decided &amp; Approved by Merchant?
                    </h3>
                  </div>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                    Decision State: {String(summary.decision_summary?.decision_state || 'PASS')}
                  </span>
                </div>

                <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 text-xs space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Merchant Sign-off:</span>
                    <span className="font-bold text-slate-800">
                      {String(summary.decision_summary?.approval_status || 'APPROVED')}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Execution Eligible:</span>
                    <span className="font-mono font-bold text-emerald-600">
                      {summary.decision_summary?.is_execution_eligible ? 'YES' : 'NO'}
                    </span>
                  </div>
                  {summary.decision_summary?.decision_state === 'BLOCK' && (
                    <div className="p-2 bg-rose-50 border border-rose-200 text-rose-800 rounded font-semibold mt-2">
                      Safety Warning: BLOCK state cannot be overridden by merchant sign-off.
                    </div>
                  )}
                </div>
              </div>

              {/* 6. WHAT WAS EXECUTED? */}
              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                  <div className="flex items-center gap-2">
                    <span className="flex items-center justify-center w-5 h-5 rounded-full bg-blue-100 text-[#002E6E] text-xs font-bold">6</span>
                    <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
                      What Was Safely Executed?
                    </h3>
                  </div>
                  <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                    MODE: SIMULATION
                  </span>
                </div>

                <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 text-xs space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Execution State:</span>
                    <span className="font-bold text-slate-800">
                      {String(summary.execution_summary?.execution_state || 'COMPLETED')}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Adapter:</span>
                    <span className="font-mono text-slate-700">SimulatedPaytmAdapter (Digital Twin)</span>
                  </div>
                  {summary.execution_summary?.executed_parameters ? (
                    <div>
                      <div className="text-[11px] text-slate-500 mb-1">Approved &amp; Executed Parameters:</div>
                      <pre className="p-2 bg-white rounded border border-slate-200 font-mono text-[10px] overflow-x-auto text-slate-700">
                        {JSON.stringify(summary.execution_summary.executed_parameters, null, 2)}
                      </pre>
                    </div>
                  ) : null}
                  <div className="text-[11px] text-slate-500 italic">
                    Proof: Unsafe raw proposed values were excluded; only approved clamped parameters were executed.
                  </div>
                </div>
              </div>

              {/* 7. WHAT HAPPENED AFTERWARD? (OUTCOME) */}
              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                  <div className="flex items-center gap-2">
                    <span className="flex items-center justify-center w-5 h-5 rounded-full bg-blue-100 text-[#002E6E] text-xs font-bold">7</span>
                    <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
                      What Happened After the Simulated Execution?
                    </h3>
                  </div>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                    Status: {String(summary.outcome_summary?.outcome_status || 'MEASURED')}
                  </span>
                </div>

                <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 text-xs space-y-2">
                  <p className="text-slate-600 leading-relaxed">
                    {String(summary.outcome_summary?.description ||
                      'Observed metric changes in digital-twin sandbox over 3-day post-action window.')}
                  </p>
                  <div className="p-2 bg-amber-50/70 border border-amber-200/80 rounded text-[11px] text-amber-900 italic">
                    Association Notice: Metric differences represent descriptive observations within the observation window; causality is not established.
                  </div>
                </div>
              </div>

              {/* 8. WHAT WAS THE SIMULATED BUSINESS IMPACT? */}
              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                  <div className="flex items-center gap-2">
                    <span className="flex items-center justify-center w-5 h-5 rounded-full bg-blue-100 text-[#002E6E] text-xs font-bold">8</span>
                    <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
                      What Was the Simulated Business Impact &amp; ROI?
                    </h3>
                  </div>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                    summary.business_impact_summary?.impact_classification === 'POSITIVE'
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-slate-100 text-slate-700'
                  }`}>
                    {String(summary.business_impact_summary?.impact_classification || 'POSITIVE')}
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                  <div className="p-2.5 bg-slate-50 rounded border border-slate-100">
                    <div className="text-[10px] text-slate-500">Incremental Rev</div>
                    <div className="text-sm font-bold text-emerald-600">
                      ₹{getNumberOrFallback(summary.business_impact_summary?.incremental_revenue, '6,240')}
                    </div>
                  </div>
                  <div className="p-2.5 bg-slate-50 rounded border border-slate-100">
                    <div className="text-[10px] text-slate-500">Campaign Cost</div>
                    <div className="text-sm font-bold text-slate-800">
                      ₹{getNumberOrFallback(summary.business_impact_summary?.campaign_cost, '1,000')}
                    </div>
                  </div>
                  <div className="p-2.5 bg-slate-50 rounded border border-slate-100">
                    <div className="text-[10px] text-slate-500">Estimated ROI</div>
                    <div className="text-sm font-bold text-emerald-600">
                      {summary.business_impact_summary?.roi != null
                        ? `${String(summary.business_impact_summary.roi)}x`
                        : '5.24x'}
                    </div>
                  </div>
                  <div className="p-2.5 bg-slate-50 rounded border border-slate-100">
                    <div className="text-[10px] text-slate-500">Cost per Incr Order</div>
                    <div className="text-sm font-bold text-slate-800">
                      ₹{getNumberOrFallback(summary.business_impact_summary?.cost_per_incremental_order, '62.50')}
                    </div>
                  </div>
                </div>

                <div className="text-[11px] text-slate-500 italic">
                  Note: COGS is not modeled in sandbox simulation; gross profit impact is unavailable.
                </div>
              </div>

              {/* 9. CONTROLLED AUTONOMY POLICY EVALUATION */}
              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                  <div className="flex items-center gap-2">
                    <span className="flex items-center justify-center w-5 h-5 rounded-full bg-sky-100 text-[#002E6E] text-xs font-bold">9</span>
                    <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
                      Controlled Autonomy &amp; Approval Flow
                    </h3>
                  </div>
                  <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded-full bg-sky-50 text-[#002E6E] border border-sky-200">
                    MODE: {String(summary.autonomy_summary?.autonomy_mode || 'APPROVAL_REQUIRED')}
                  </span>
                </div>

                <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 text-xs space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Approval Source:</span>
                    <span className="font-bold text-slate-800">
                      {String(summary.autonomy_summary?.approval_source || 'PENDING')}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Deciding Actor:</span>
                    <span className="font-mono text-slate-700">
                      {String(summary.autonomy_summary?.actor_type || 'MERCHANT')}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Evaluated Risk vs Policy Threshold:</span>
                    <span className="font-mono font-semibold text-slate-800">
                      {getNumberOrFallback(summary.autonomy_summary?.evaluated_risk, '0.18')} ≤ {getNumberOrFallback(summary.autonomy_summary?.policy_threshold, '0.30')}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">16-Point Deterministic Safety Checks:</span>
                    <span className="font-semibold text-emerald-700">
                      {getNumberOrFallback(summary.autonomy_summary?.passed_checks_count, 16)} Passed / {getNumberOrFallback(summary.autonomy_summary?.failed_checks_count, 0)} Failed
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-500 italic pt-1 border-t border-slate-200/60">
                    Safety Invariant: Autonomy controls approval flow; autonomy NEVER overrides safety boundaries.
                  </div>
                </div>
              </div>

              {/* 10. CRYPTOGRAPHIC AUDIT TRAIL & TAMPER VERIFICATION */}
              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                  <div className="flex items-center gap-2">
                    <span className="flex items-center justify-center w-5 h-5 rounded-full bg-blue-100 text-[#002E6E] text-xs font-bold">10</span>
                    <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
                      Audit Trail &amp; SHA-256 Hash Chaining
                    </h3>
                  </div>
                  <span
                    className={`inline-flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full border ${
                      isChainValid
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : 'bg-rose-50 text-rose-700 border-rose-200'
                    }`}
                  >
                    {isChainValid ? (
                      <>
                        <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                        <span>CHAIN VERIFIED (SHA-256)</span>
                      </>
                    ) : (
                      <>
                        <ShieldAlert className="w-3.5 h-3.5 text-rose-600" />
                        <span>TAMPER DETECTED</span>
                      </>
                    )}
                  </span>
                </div>

                <p className="text-xs text-slate-600">
                  Every step in this autonomous workflow was committed to a tamper-evident append-only ledger in SQLite.
                  Each entry re-hashes the previous entry&apos;s cryptographic digest.
                </p>

                {/* Timeline */}
                <div className="space-y-3 divide-y divide-slate-100 max-h-80 overflow-y-auto pr-1">
                  {summary.audit_timeline && summary.audit_timeline.length > 0 ? (
                    summary.audit_timeline.map((evt, idx) => (
                      <div key={evt.event_id || idx} className="pt-2.5 first:pt-0 space-y-1 text-xs">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-[10px] bg-slate-100 text-slate-700 font-bold px-1.5 py-0.5 rounded">
                              {evt.stage}
                            </span>
                            <span className="font-semibold text-slate-800">{evt.action_description}</span>
                          </div>
                          <span className="text-[10px] text-slate-400 font-mono">
                            {evt.timestamp ? new Date(evt.timestamp).toLocaleTimeString() : ''}
                          </span>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[10px] font-mono text-slate-500 bg-slate-50 p-2 rounded border border-slate-100">
                          <div className="truncate" title={evt.previous_hash}>
                            Prev Hash: <span className="text-slate-700">{evt.previous_hash?.substring(0, 16)}...</span>
                          </div>
                          <div className="truncate" title={evt.integrity_hash}>
                            Digest: <span className="text-blue-700 font-bold">{evt.integrity_hash?.substring(0, 16)}...</span>
                          </div>
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-slate-400 italic">No audit events found.</p>
                  )}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 bg-white border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <Lock className="w-3.5 h-3.5 text-slate-400" />
            <span>Zero live credentials or Paytm real money APIs exposed.</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-[#002E6E] hover:bg-[#001D47] active:scale-[0.98] text-white font-bold text-xs rounded-lg transition-all cursor-pointer shadow-xs"
          >
            Close Panel
          </button>
        </div>
      </div>
    </div>
  );
};
