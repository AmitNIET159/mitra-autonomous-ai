'use client';

import React from 'react';
import { WorkflowStage } from '@/types';
import { Radio, Search, Sliders, Shield, Scale, UserCheck, Zap, TrendingUp, HelpCircle, Check } from 'lucide-react';

const stages: { id: WorkflowStage; label: string; desc: string; icon: React.ElementType }[] = [
  { id: 'DETECT', label: '1. DETECT', desc: 'Signals & anomalies', icon: Radio },
  { id: 'INVESTIGATE', label: '2. INVESTIGATE', desc: 'Evidence reasoning', icon: Search },
  { id: 'PLAN', label: '3. PLAN', desc: 'Candidate proposal', icon: Sliders },
  { id: 'GUARD', label: '4. GUARD', desc: '10 hard guardrails', icon: Shield },
  { id: 'DECIDE', label: '5. DECIDE', desc: 'Authoritative decision', icon: Scale },
  { id: 'APPROVE', label: '6. APPROVE', desc: 'Merchant sign-off gate', icon: UserCheck },
  { id: 'ACT', label: '7. ACT', desc: 'Execution barrier', icon: Zap },
  { id: 'LEARN', label: '8. LEARN', desc: 'Measured outcome lift', icon: TrendingUp },
];

export const WorkflowRibbon: React.FC<{
  activeStage?: WorkflowStage;
  onOpenExplainability?: () => void;
}> = ({ activeStage = 'DETECT', onOpenExplainability }) => {
  const activeIndex = stages.findIndex((s) => s.id === activeStage);

  return (
    <div className="bg-white border border-slate-200/90 rounded-xl p-4 shadow-xs">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 mb-3 border-b border-slate-100 gap-2">
        <div className="flex items-center gap-2">
          <div className="h-6 w-1 rounded bg-[#00BAF2]" />
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold tracking-wider text-[#002E6E] uppercase">Autonomous Teammate Pipeline</span>
              <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                8-STAGE CONTRACT
              </span>
            </div>
            <h3 className="text-xs font-medium text-slate-600">
              Deterministic truth calculation with bounded autonomous interpretation
            </h3>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-xs text-slate-500 font-medium hidden md:block">
            Ledger: <span className="text-[#002E6E] font-semibold font-mono">SHA-256 Chained</span>
          </div>
          {onOpenExplainability && (
            <button
              onClick={onOpenExplainability}
              className="flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 bg-[#002E6E] hover:bg-[#001D47] active:bg-[#001330] text-white rounded-lg shadow-xs transition-all cursor-pointer shrink-0"
            >
              <HelpCircle className="w-3.5 h-3.5 text-[#00BAF2]" />
              <span>Why MITRA? (Explain)</span>
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
        {stages.map((stage, idx) => {
          const Icon = stage.icon;
          const isActive = activeStage === stage.id;
          const isCompleted = activeIndex !== -1 && idx < activeIndex;

          return (
            <div
              key={stage.id}
              className={`p-2.5 rounded-lg border transition-all flex flex-col justify-between ${
                isActive
                  ? 'bg-sky-50/80 border-[#00BAF2] ring-1 ring-[#00BAF2]/40 shadow-xs'
                  : isCompleted
                  ? 'bg-slate-50/60 border-emerald-200 text-slate-700'
                  : 'bg-slate-50/40 border-slate-200/70 text-slate-500'
              }`}
            >
              <div className="flex items-center justify-between gap-1 mb-1">
                <div className="flex items-center gap-1.5 min-w-0">
                  <Icon
                    className={`w-3.5 h-3.5 shrink-0 ${
                      isActive ? 'text-[#002E6E]' : isCompleted ? 'text-emerald-600' : 'text-slate-400'
                    }`}
                  />
                  <span
                    className={`text-[11px] font-bold truncate ${
                      isActive ? 'text-[#002E6E]' : isCompleted ? 'text-slate-900' : 'text-slate-600'
                    }`}
                  >
                    {stage.label}
                  </span>
                </div>
                {isCompleted ? (
                  <Check className="w-3 h-3 text-emerald-600 shrink-0" />
                ) : isActive ? (
                  <span className="w-2 h-2 rounded-full bg-[#00BAF2] animate-pulse shrink-0" />
                ) : null}
              </div>
              <div className="text-[10px] text-slate-500 leading-tight truncate">{stage.desc}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
