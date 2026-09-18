'use client';

import React, { useState } from 'react';
import { Play, CheckCircle, AlertTriangle, ShieldAlert, Sparkles, RefreshCw, Cpu } from 'lucide-react';
import { triggerDemoScenario } from '@/lib/api';
import { DemoScenarioResult } from '@/types';

interface DemoScenarioControllerProps {
  onScenarioExecuted?: (result: DemoScenarioResult) => void;
  disabled?: boolean;
}

const SCENARIOS = [
  {
    id: 'NORMAL_FLOW',
    name: '1. Standard Autonomous Flow',
    badge: 'PASS (8 STAGES VERIFIED)',
    badgeColor: 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20',
    description: 'Signal -> Investigation -> Proposal -> Guardrail PASS -> Decision PENDING approval.',
    icon: Play,
  },
  {
    id: 'MODIFY_FLOW',
    name: '2. Guardrail Clamping',
    badge: '₹150 → ₹100 SAFETY CLAMP APPLIED',
    badgeColor: 'bg-amber-500/10 text-amber-600 border-amber-500/20 font-mono',
    description: 'Proposed ₹150 discount exceeds merchant policy; guardrail clamps to ₹100 safety ceiling.',
    icon: RefreshCw,
  },
  {
    id: 'BLOCK_FLOW',
    name: '3. Hard Safety Boundary',
    badge: 'BLOCKED BY SAFETY CONTROLS',
    badgeColor: 'bg-rose-500/10 text-rose-600 border-rose-500/20 font-bold',
    description: 'Unbounded 99% / ₹5,000 proposal violates margin rules; engine strictly halts execution.',
    icon: ShieldAlert,
  },
  {
    id: 'AUTO_APPROVE_FLOW',
    name: '4. Safe Autonomy Policy',
    badge: 'AUTO-APPROVED UNDER STRICT POLICY',
    badgeColor: 'bg-blue-500/10 text-blue-600 border-blue-500/20',
    description: 'Low-risk campaign (0.20) evaluated under AUTO_APPROVE_SAFE mode; automatically execution-eligible.',
    icon: Cpu,
  },
  {
    id: 'UNAPPROVED_FLOW',
    name: '5. Human-in-the-Loop Gate',
    badge: 'AWAITING MERCHANT SIGN-OFF',
    badgeColor: 'bg-indigo-500/10 text-indigo-600 border-indigo-500/20',
    description: 'Action held at review gateway; execution strictly forbidden until explicit merchant sign-off.',
    icon: AlertTriangle,
  },
  {
    id: 'INSUFFICIENT_DATA_FLOW',
    name: '6. Graceful Degradation',
    badge: 'SPARSE DATA · ZERO FABRICATION',
    badgeColor: 'bg-slate-500/10 text-slate-600 border-slate-500/20',
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
    <div className="bg-white border border-slate-200/80 rounded-xl shadow-xs overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-slate-900 via-[#002E6E] to-slate-900 text-white px-5 py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-[#00BAF2]/20 border border-[#00BAF2]/30 flex items-center justify-center text-[#00BAF2]">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold tracking-tight">Live Scenario Orchestrator</h2>
              <span className="bg-[#00BAF2] text-[#002E6E] text-[10px] font-black px-1.5 py-0.5 rounded tracking-wider">
                HACKATHON LIVE DEMO
              </span>
            </div>
            <p className="text-xs text-slate-300">
              Trigger real, deterministic backend scenarios to demonstrate MITRA&apos;s end-to-end autonomy.
            </p>
          </div>
        </div>

        <button
          onClick={handleExecute}
          disabled={isRunning || disabled}
          className="bg-[#00BAF2] hover:bg-[#00a3d4] text-[#002E6E] font-bold px-4 py-2 rounded-lg text-xs flex items-center justify-center gap-2 shadow-sm transition-colors cursor-pointer disabled:opacity-50"
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

      {/* Scenario Selector Chips */}
      <div className="p-4 sm:p-5 border-b border-slate-100 bg-slate-50/50">
        <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2.5">
          Select Presentation Scenario:
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
          {SCENARIOS.map((scenario) => {
            const isSelected = selectedScenario === scenario.id;
            const Icon = scenario.icon;
            return (
              <button
                key={scenario.id}
                type="button"
                onClick={() => setSelectedScenario(scenario.id)}
                className={`text-left p-3 rounded-lg border transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-white border-[#002E6E] ring-1 ring-[#002E6E] shadow-xs'
                    : 'bg-white hover:bg-slate-50 border-slate-200 text-slate-700'
                }`}
              >
                <div className="flex items-center justify-between gap-1.5 mb-1">
                  <div className="flex items-center gap-1.5 font-bold text-xs text-slate-900">
                    <Icon className={`w-3.5 h-3.5 ${isSelected ? 'text-[#002E6E]' : 'text-slate-400'}`} />
                    <span>{scenario.name}</span>
                  </div>
                </div>
                <span className={`inline-block text-[10px] font-semibold px-1.5 py-0.5 rounded border mb-1.5 ${scenario.badgeColor}`}>
                  {scenario.badge}
                </span>
                <p className="text-[11px] text-slate-500 line-clamp-2 leading-relaxed">
                  {scenario.description}
                </p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Execution Feedback / Telemetry */}
      {lastResult && (
        <div className="p-4 sm:p-5 bg-white">
          <div className="flex items-start gap-3 p-3.5 rounded-lg border border-slate-200 bg-slate-50">
            <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0 space-y-1.5">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-bold text-slate-900">
                  Scenario Executed: {lastResult.scenario}
                </span>
                {lastResult.decision_state && (
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-slate-200 text-slate-800">
                    Decision: {lastResult.decision_state}
                  </span>
                )}
                {lastResult.autonomy_status && (
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-blue-100 text-blue-800">
                    Autonomy: {lastResult.autonomy_status}
                  </span>
                )}
                {lastResult.is_execution_eligible !== undefined && (
                  <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                    lastResult.is_execution_eligible
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-rose-100 text-rose-800'
                  }`}>
                    Execution: {lastResult.is_execution_eligible ? 'ELIGIBLE' : 'GATED'}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-600">
                {lastResult.description}
              </p>
              {lastResult.original_discount && lastResult.clamped_discount && (
                <div className="text-[11px] font-mono text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1 mt-1">
                  Proposed Discount: ₹{lastResult.original_discount} → Clamped Safety Ceiling: ₹{lastResult.clamped_discount}
                </div>
              )}
            </div>
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
