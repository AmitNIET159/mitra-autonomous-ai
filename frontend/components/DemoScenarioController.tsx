'use client';

import React, { useState } from 'react';
import { Play, CheckCircle, AlertTriangle, ShieldAlert, Sparkles, RefreshCw, Cpu, ShieldCheck, ArrowRight, Lock } from 'lucide-react';
import { triggerDemoScenario } from '@/lib/api';
import { DemoScenarioResult } from '@/types';

interface DemoScenarioControllerProps {
  onScenarioExecuted?: (result: DemoScenarioResult) => void;
  disabled?: boolean;
}

const SCENARIOS = [
  {
    id: 'NORMAL_FLOW',
    name: 'Standard Autonomous Flow',
    subtitle: 'Normal Flow',
    badge: 'PASS',
    badgeColor: 'bg-emerald-50 text-emerald-700 border-emerald-300',
    description: 'Signal → Investigation → Proposal → Guardrails PASS → Decision PENDING sign-off.',
    icon: Play,
  },
  {
    id: 'MODIFY_FLOW',
    name: 'Guardrail Clamping',
    subtitle: 'Modify Flow',
    badge: '₹150 → ₹100',
    badgeColor: 'bg-amber-50 text-amber-800 border-amber-300 font-mono',
    description: 'Proposed ₹150 discount clamped to ₹100 safety ceiling by deterministic policy.',
    icon: RefreshCw,
  },
  {
    id: 'BLOCK_FLOW',
    name: 'Hard Safety Boundary',
    subtitle: 'Block Flow',
    badge: 'BLOCKED',
    badgeColor: 'bg-rose-50 text-rose-700 border-rose-300 font-bold',
    description: 'Unbounded 99% / ₹5,000 proposal violates margin rules; engine strictly halts execution.',
    icon: ShieldAlert,
  },
  {
    id: 'AUTO_APPROVE_FLOW',
    name: 'Safe Autonomy Policy',
    subtitle: 'Auto-Approve Flow',
    badge: 'AUTO-APPROVED',
    badgeColor: 'bg-sky-50 text-[#007EA7] border-sky-300 font-semibold',
    description: 'Low-risk campaign (0.20) evaluated under AUTO_APPROVE_SAFE; execution-eligible.',
    icon: Cpu,
  },
  {
    id: 'UNAPPROVED_FLOW',
    name: 'Human-in-the-Loop',
    subtitle: 'Unapproved Flow',
    badge: 'AWAITING APPROVAL',
    badgeColor: 'bg-indigo-50 text-indigo-700 border-indigo-300',
    description: 'Action held at review gateway; execution strictly forbidden until merchant sign-off.',
    icon: AlertTriangle,
  },
  {
    id: 'INSUFFICIENT_DATA_FLOW',
    name: 'Graceful Degradation',
    subtitle: 'Sparse Telemetry',
    badge: 'ZERO FABRICATION',
    badgeColor: 'bg-slate-100 text-slate-700 border-slate-300',
    description: 'Unmeasured sparse data scenario; zero hallucination, falls back to advisory notice.',
    icon: Sparkles,
  },
];

export const DemoScenarioController: React.FC<DemoScenarioControllerProps> = ({
  onScenarioExecuted,
  disabled = false,
}) => {
  const [selectedScenario, setSelectedScenario] = useState<string>('NORMAL_FLOW');
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [lastResult, setLastResult] = useState<DemoScenarioResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleExecute = async () => {
    setIsRunning(true);
    setError(null);
    try {
      const res = await triggerDemoScenario(selectedScenario);
      setLastResult(res);
      if (onScenarioExecuted) {
        onScenarioExecuted(res);
      }
    } catch (err: unknown) {
      console.error('Failed to trigger demo scenario:', err);
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="bg-white border border-slate-200/90 rounded-xl shadow-xs overflow-hidden">
      {/* Header */}
      <div className="bg-[#001D47] text-white px-5 py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#002E6E]">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-[#00BAF2]/20 border border-[#00BAF2]/40 flex items-center justify-center text-[#00BAF2]">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold tracking-tight">Live Scenario Controller</h2>
              <span className="bg-[#00BAF2] text-[#001D47] text-[10px] font-black px-2 py-0.5 rounded tracking-wider">
                6 SCENARIOS
              </span>
            </div>
            <p className="text-xs text-slate-300">
              Run deterministic end-to-end scenarios to test safety boundaries, clamping, and autonomy policies.
            </p>
          </div>
        </div>

        <button
          onClick={handleExecute}
          disabled={isRunning || disabled}
          className="bg-[#00BAF2] hover:bg-[#00a3d4] active:bg-[#008cb6] text-[#001D47] font-extrabold px-4 py-2 rounded-lg text-xs flex items-center justify-center gap-2 shadow-sm transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isRunning ? (
            <>
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              <span>Executing Pipeline...</span>
            </>
          ) : (
            <>
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Run Selected Scenario</span>
            </>
          )}
        </button>
      </div>

      {/* Scenario Selector Cards */}
      <div className="p-4 sm:p-5 border-b border-slate-100 bg-slate-50/50">
        <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2.5 flex items-center justify-between">
          <span>Select Operational Scenario:</span>
          <span className="text-[10px] font-mono text-slate-400 font-normal">Click a scenario card to configure</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {SCENARIOS.map((scenario, sIdx) => {
            const isSelected = selectedScenario === scenario.id;
            const Icon = scenario.icon;
            return (
              <button
                key={scenario.id}
                type="button"
                onClick={() => setSelectedScenario(scenario.id)}
                className={`text-left p-3.5 rounded-xl border transition-all cursor-pointer relative ${
                  isSelected
                    ? 'bg-white border-[#002E6E] ring-2 ring-[#002E6E]/20 shadow-xs'
                    : 'bg-white hover:bg-slate-50/80 border-slate-200/90 text-slate-700'
                }`}
              >
                <div className="flex items-start justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-2 min-w-0">
                    <div
                      className={`p-1.5 rounded-md ${
                        isSelected ? 'bg-blue-50 text-[#002E6E]' : 'bg-slate-100 text-slate-500'
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-[10px] font-mono text-slate-400 font-bold uppercase">
                        {sIdx + 1}. {scenario.subtitle}
                      </div>
                      <div className="font-bold text-xs text-slate-900 truncate">
                        {scenario.name}
                      </div>
                    </div>
                  </div>
                  <span
                    className={`shrink-0 inline-block text-[10px] font-bold px-2 py-0.5 rounded-full border ${scenario.badgeColor}`}
                  >
                    {scenario.badge}
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 line-clamp-2 leading-relaxed mt-1">
                  {scenario.description}
                </p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Result Panel */}
      {lastResult && (
        <div className="p-4 sm:p-5 bg-white border-t border-slate-100">
          <div className="border border-slate-200 rounded-xl p-4 bg-slate-50/60 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2.5 border-b border-slate-200">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
                <span className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  MITRA Action Result
                </span>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-slate-200/90 text-slate-800">
                  {lastResult.scenario}
                </span>
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                {lastResult.decision_state && (
                  <span
                    className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                      lastResult.decision_state === 'BLOCK'
                        ? 'bg-rose-100 text-rose-800 border-rose-200'
                        : lastResult.decision_state === 'MODIFY'
                        ? 'bg-amber-100 text-amber-900 border-amber-200'
                        : 'bg-emerald-100 text-emerald-800 border-emerald-200'
                    }`}
                  >
                    Decision: {lastResult.decision_state}
                  </span>
                )}
                {lastResult.is_execution_eligible !== undefined && (
                  <span
                    className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                      lastResult.is_execution_eligible
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
                        : 'bg-rose-50 text-rose-700 border-rose-300'
                    }`}
                  >
                    Execution: {lastResult.is_execution_eligible ? 'ELIGIBLE' : 'BLOCKED / GATED'}
                  </span>
                )}
              </div>
            </div>

            {/* Structured Highlights */}
            {lastResult.scenario === 'MODIFY_FLOW' && lastResult.original_discount && lastResult.clamped_discount ? (
              <div className="bg-amber-50/80 border border-amber-200 rounded-lg p-3 space-y-2">
                <div className="text-[11px] font-bold text-amber-900 uppercase tracking-wider flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-amber-700" />
                  <span>GUARDRAIL RESULT — PARAMETER CLAMPING</span>
                </div>
                <div className="flex items-center gap-3 text-xs font-mono py-1">
                  <div className="bg-white px-2.5 py-1 rounded border border-amber-200">
                    <span className="text-[10px] text-slate-500 block font-sans">Proposed</span>
                    <strong className="text-rose-600 text-sm">₹{lastResult.original_discount}</strong>
                  </div>
                  <ArrowRight className="w-4 h-4 text-amber-600" />
                  <div className="bg-white px-2.5 py-1 rounded border border-amber-200">
                    <span className="text-[10px] text-slate-500 block font-sans">Maximum Allowed</span>
                    <strong className="text-amber-800 text-sm">₹{lastResult.clamped_discount}</strong>
                  </div>
                  <ArrowRight className="w-4 h-4 text-amber-600" />
                  <div className="bg-emerald-100/90 text-emerald-800 px-2.5 py-1 rounded border border-emerald-300 font-bold flex items-center gap-1">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-700" />
                    <span>SAFETY CLAMP APPLIED</span>
                  </div>
                </div>
              </div>
            ) : lastResult.scenario === 'BLOCK_FLOW' ? (
              <div className="bg-rose-50 border border-rose-200 rounded-lg p-3 text-xs text-rose-900 space-y-1">
                <div className="font-bold flex items-center gap-1.5 text-rose-800">
                  <Lock className="w-3.5 h-3.5 text-rose-600" />
                  <span>BLOCKED BY SAFETY CONTROLS</span>
                </div>
                <p className="text-[11px] text-rose-700 leading-relaxed">
                  Severe policy boundary violation detected. Execution is strictly disallowed under all autonomy modes.
                </p>
              </div>
            ) : null}

            <p className="text-xs text-slate-600 leading-relaxed">
              {lastResult.description}
            </p>
          </div>
        </div>
      )}

      {error && (
        <div className="p-4 sm:p-5 bg-rose-50 border-t border-rose-200 text-rose-800 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>Execution failed: {error}</span>
        </div>
      )}
    </div>
  );
};
