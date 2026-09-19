'use client';

import React from 'react';
import { ActionProposal, DecisionState, GuardrailEvaluation } from '@/types';
import {
  Shield,
  CheckCircle,
  Sliders,
  XCircle,
  AlertOctagon,
  Lock,
  ArrowRight,
  Sparkles,
  ShieldCheck,
  ShieldAlert,
} from 'lucide-react';

interface GuardrailStatusAreaProps {
  evaluation?: GuardrailEvaluation | null;
  proposal?: ActionProposal | null;
  isEvaluating?: boolean;
  onEvaluate?: () => Promise<void> | void;
}

const decisionStates: {
  state: DecisionState;
  label: string;
  badgeClass: string;
  desc: string;
  icon: React.ElementType;
}[] = [
  {
    state: 'PASS',
    label: 'PASS',
    badgeClass: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    desc: 'All constraints met. Action dispatched safely.',
    icon: CheckCircle,
  },
  {
    state: 'MODIFY',
    label: 'MODIFY',
    badgeClass: 'bg-amber-100 text-amber-900 border-amber-300',
    desc: 'Minor limits exceeded. Parameters auto-clamped to policy thresholds.',
    icon: Sliders,
  },
  {
    state: 'BLOCK',
    label: 'BLOCK',
    badgeClass: 'bg-rose-100 text-rose-800 border-rose-300',
    desc: 'Severe violation or high risk. Execution strictly prevented.',
    icon: XCircle,
  },
  {
    state: 'ESCALATE',
    label: 'ESCALATE',
    badgeClass: 'bg-amber-100 text-amber-800 border-amber-300',
    desc: 'High financial impact or uncertainty. Held for merchant manual review.',
    icon: AlertOctagon,
  },
];

export const GuardrailStatusArea: React.FC<GuardrailStatusAreaProps> = ({
  evaluation,
  proposal,
  isEvaluating = false,
  onEvaluate,
}) => {
  return (
    <div className="bg-white border border-slate-200/90 rounded-xl p-5 shadow-xs space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200">
            <Shield className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Deterministic Guardrail Engine
              </h2>
              {evaluation && (
                <span
                  className={`text-[10px] px-2 py-0.5 rounded-full font-bold border ${
                    evaluation.overall_status === 'PASS'
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      : evaluation.overall_status === 'MODIFY'
                      ? 'bg-amber-50 text-amber-800 border-amber-200'
                      : evaluation.overall_status === 'BLOCK'
                      ? 'bg-rose-50 text-rose-700 border-rose-200'
                      : 'bg-slate-100 text-slate-700 border-slate-200'
                  }`}
                >
                  {evaluation.overall_status}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500">
              Deterministic systems calculate truth; the LLM interprets it.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1 text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
            <Lock className="w-3 h-3" /> Hard Safety Barrier
          </span>

          {proposal && !evaluation && onEvaluate && (
            <button
              onClick={onEvaluate}
              disabled={isEvaluating}
              className="px-3 py-1.5 bg-emerald-700 hover:bg-emerald-800 active:bg-emerald-900 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-xs transition-all cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isEvaluating ? (
                <>
                  <Shield className="w-3.5 h-3.5 animate-spin" /> Evaluating 10 Rules...
                </>
              ) : (
                <>
                  <ShieldCheck className="w-3.5 h-3.5" /> Evaluate Guardrails
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Safety Notice Banner */}
      <div className="bg-[#001D47] text-slate-100 rounded-lg p-2.5 px-3 flex flex-wrap items-center justify-between gap-2 text-xs border border-[#002E6E]">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
          <span className="font-bold text-slate-100">
            100% Deterministic Code Verification
          </span>
          <span className="text-slate-400 hidden sm:inline">•</span>
          <span className="text-slate-300 text-[11px]">
            Zero LLM authority over safety thresholds or execution dispatch
          </span>
        </div>
        <span className="font-mono text-[10px] text-cyan-300 uppercase tracking-wide font-bold">
          Zero Hallucination Tolerance
        </span>
      </div>

      {evaluation ? (
        <div className="space-y-4">
          {/* Status Details Box */}
          {evaluation.overall_status === 'BLOCK' && (
            <div className="p-3 bg-rose-50 border border-rose-300 rounded-lg text-xs text-rose-900 flex items-start gap-2.5">
              <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <strong className="font-bold">CRITICAL SAFETY BOUNDARY TRIGGERED (ACTION BLOCKED):</strong>
                <p className="text-[11px] leading-relaxed text-rose-800">
                  {evaluation.notes || 'Proposal violated non-negotiable merchant constraints. Action prevented from reaching merchant execution.'}
                </p>
              </div>
            </div>
          )}

          {evaluation.overall_status === 'MODIFY' && (
            <div className="p-3 bg-amber-50 border border-amber-300 rounded-lg text-xs text-amber-900 space-y-2">
              <div className="flex items-center gap-2 font-bold">
                <Sliders className="w-4 h-4 text-amber-700" />
                <span>Deterministic Parameter Clamping Applied (MODIFY):</span>
              </div>
              <p className="text-[11px] text-amber-800">
                {evaluation.notes || 'Minor policy boundary exceeded. Parameters automatically clamped to policy ceiling.'}
              </p>
              {Object.keys(evaluation.modifications).length > 0 && (
                <div className="bg-white/80 rounded p-2 border border-amber-200 text-[11px] font-mono space-y-1">
                  {Object.entries(evaluation.modifications).map(([key, val]) => (
                    <div key={key} className="flex items-center gap-2">
                      <span className="text-slate-500">{key}:</span>
                      <span className="text-rose-600 line-through">
                        {String(evaluation.original_values[key] ?? 'N/A')}
                      </span>
                      <ArrowRight className="w-3 h-3 text-slate-400" />
                      <span className="text-emerald-700 font-bold">{String(val)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {evaluation.overall_status === 'PASS' && (
            <div className="p-3 bg-emerald-50 border border-emerald-300 rounded-lg text-xs text-emerald-900 flex items-center justify-between">
              <div className="flex items-center gap-2 font-medium">
                <CheckCircle className="w-4 h-4 text-emerald-600" />
                <span>All 10 deterministic guardrail rules satisfied. Proposal cleared for merchant approval workflow.</span>
              </div>
              <span className="font-mono text-[10px] text-emerald-700 font-bold bg-emerald-100 px-2 py-0.5 rounded">
                10 / 10 CHECKS PASSED
              </span>
            </div>
          )}

          {/* 10-Point Deterministic Guardrail Check Table */}
          <div className="border border-slate-200 rounded-lg overflow-hidden">
            <div className="bg-slate-50 px-3 py-2 border-b border-slate-200 flex items-center justify-between text-xs font-bold text-slate-700">
              <span>10-Point Deterministic Verification Matrix</span>
              <span className="font-mono text-[10px] text-slate-500 font-normal">
                Eval ID: {evaluation.evaluation_id}
              </span>
            </div>

            <div className="divide-y divide-slate-100 max-h-72 overflow-y-auto">
              {evaluation.checks.map((chk) => {
                const isPass = chk.status === 'PASS';
                const isFail = chk.status === 'FAIL';
                const isModified = chk.status === 'MODIFIED';

                return (
                  <div
                    key={chk.check_id}
                    className={`p-2.5 flex flex-wrap sm:flex-nowrap items-start justify-between gap-2 text-xs ${
                      isFail
                        ? 'bg-rose-50/50'
                        : isModified
                        ? 'bg-amber-50/40'
                        : 'hover:bg-slate-50/80'
                    }`}
                  >
                    <div className="flex items-start gap-2 min-w-[120px]">
                      {isPass ? (
                        <CheckCircle className="w-3.5 h-3.5 text-emerald-600 mt-0.5 shrink-0" />
                      ) : isModified ? (
                        <Sliders className="w-3.5 h-3.5 text-amber-600 mt-0.5 shrink-0" />
                      ) : (
                        <XCircle className="w-3.5 h-3.5 text-rose-600 mt-0.5 shrink-0" />
                      )}
                      <div>
                        <div className="font-bold text-slate-900 flex items-center gap-1 font-mono text-[11px]">
                          <span>{chk.check_id}</span>
                          <span className="text-slate-400">•</span>
                          <span className="text-slate-700 font-sans font-medium">{chk.check_type}</span>
                        </div>
                        <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                          Rule: {chk.rule}
                        </div>
                      </div>
                    </div>

                    <div className="flex-1 px-2 text-[11px] text-slate-600">
                      <p className="leading-snug">{chk.message}</p>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded font-mono ${
                          isPass
                            ? 'bg-emerald-100 text-emerald-800'
                            : isModified
                            ? 'bg-amber-100 text-amber-900'
                            : 'bg-rose-100 text-rose-800'
                        }`}
                      >
                        {chk.status}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      ) : (
        /* Standby / Initial State */
        <div className="space-y-4">
          {proposal ? (
            <div className="bg-emerald-50/60 border border-emerald-200 rounded-lg p-3 text-xs text-slate-700 flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-emerald-600 shrink-0" />
                <div>
                  <strong>Candidate Proposal Ready for Verification:</strong> {proposal.action_type} (
                  {proposal.target_customer_count ?? 486} customers, ₹{proposal.incentive_value} cashback).
                </div>
              </div>
              {onEvaluate && (
                <button
                  onClick={onEvaluate}
                  disabled={isEvaluating}
                  className="px-3 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded font-bold text-xs flex items-center gap-1 shadow-sm transition-all"
                >
                  {isEvaluating ? 'Evaluating...' : 'Run 10-Point Guardrails'}
                </button>
              )}
            </div>
          ) : (
            <div className="bg-slate-50 border border-dashed border-slate-300 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500">
                Awaiting Step 3 candidate proposal. Once planned, deterministic guardrails will execute 10 non-negotiable checks.
              </p>
            </div>
          )}

          {/* 4 Primary Decision States */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {decisionStates.map((ds) => {
              const Icon = ds.icon;
              return (
                <div key={ds.state} className="p-3 rounded-lg border border-slate-200/80 bg-slate-50/70">
                  <div className="flex items-center justify-between mb-1">
                    <span className={`text-xs font-bold px-2 py-0.5 rounded border ${ds.badgeClass} flex items-center gap-1`}>
                      <Icon className="w-3 h-3" />
                      {ds.label}
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono">Contract Enforced</span>
                  </div>
                  <p className="text-xs text-slate-600 mt-1">{ds.desc}</p>
                </div>
              );
            })}
          </div>

          {/* Enforced Thresholds */}
          <div className="bg-slate-50 rounded-lg p-3 border border-slate-200/70 text-xs">
            <div className="font-semibold text-slate-700 mb-1.5">Enforced Policy Thresholds (Configured in Digital Twin):</div>
            <div className="grid grid-cols-3 gap-2 text-slate-600">
              <div>
                <span className="text-slate-400 block text-[10px]">Max Daily Budget</span>
                <span className="font-bold text-slate-800">₹12,000 / day</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px]">Max Incentive Ceiling</span>
                <span className="font-bold text-slate-800">₹100 / customer</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px]">Minimum Margin</span>
                <span className="font-bold text-slate-800">10.0%</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
