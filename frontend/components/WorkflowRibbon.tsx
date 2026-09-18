'use client';

import React from 'react';
import { WorkflowStage } from '@/types';
import { Radio, Search, Sliders, Shield, Scale, UserCheck, Zap, TrendingUp, HelpCircle } from 'lucide-react';

const stages: { id: WorkflowStage; label: string; desc: string; icon: React.ElementType }[] = [
  { id: 'DETECT', label: '1. DETECT', desc: 'Business signals & anomalies', icon: Radio },
  { id: 'INVESTIGATE', label: '2. INVESTIGATE', desc: 'Evidence reasoning', icon: Search },
  { id: 'PLAN', label: '3. PLAN', desc: 'Candidate action synthesis', icon: Sliders },
  { id: 'GUARD', label: '4. GUARD', desc: 'Deterministic hard guardrails', icon: Shield },
  { id: 'DECIDE', label: '5. DECIDE', desc: 'Authoritative decision', icon: Scale },
  { id: 'APPROVE', label: '6. APPROVE', desc: 'Merchant sign-off gateway', icon: UserCheck },
  { id: 'ACT', label: '7. ACT', desc: 'Safe execution barrier', icon: Zap },
  { id: 'LEARN', label: '8. LEARN', desc: 'Impact measurement', icon: TrendingUp },
];

export const WorkflowRibbon: React.FC<{
  activeStage?: WorkflowStage;
  onOpenExplainability?: () => void;
}> = ({ activeStage = 'DETECT', onOpenExplainability }) => {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 mb-3 border-b border-slate-100 gap-2">
        <div>
          <span className="text-xs font-bold tracking-wider text-[#002E6E] uppercase">Autonomous Teammate Pipeline</span>
          <h3 className="text-sm font-semibold text-slate-800">
            &ldquo;Deterministic systems calculate truth; the LLM interprets it.&rdquo;
          </h3>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-xs text-slate-500 font-medium hidden md:block">
            Workflow Contract: <span className="text-[#002E6E] font-semibold">End-to-End Auditable</span>
          </div>
          {onOpenExplainability && (
            <button
              onClick={onOpenExplainability}
              className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 bg-[#002E6E] hover:bg-[#001D47] text-white rounded-lg shadow-sm transition-colors shrink-0"
            >
              <HelpCircle className="w-3.5 h-3.5 text-[#00BAF2]" />
              <span>Why MITRA? (Explain)</span>
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
        {stages.map((stage) => {
          const Icon = stage.icon;
          const isActive = activeStage === stage.id;
          return (
            <div
              key={stage.id}
              className={`p-2 rounded-lg border transition-colors ${
                isActive
                  ? 'bg-blue-50/70 border-[#00BAF2] text-[#002E6E]'
                  : 'bg-slate-50/70 border-slate-200/80 text-slate-600'
              }`}
            >
              <div className="flex items-center gap-1.5 mb-1">
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-[#00BAF2]' : 'text-slate-500'}`} />
                <span className="text-[11px] font-bold truncate">{stage.label}</span>
              </div>
              <div className="text-[10px] text-slate-500 leading-tight truncate">{stage.desc}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
