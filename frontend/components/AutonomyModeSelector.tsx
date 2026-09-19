'use client';

import React, { useState } from 'react';
import { Shield, Lock, Zap, Sliders, CheckCircle2, AlertTriangle, Info } from 'lucide-react';
import { AutonomyMode, MerchantAutonomyPolicy } from '@/types';
import { updateMerchantAutonomyPolicy } from '@/lib/api';

interface AutonomyModeSelectorProps {
  policy: MerchantAutonomyPolicy | null;
  onPolicyChange: (policy: MerchantAutonomyPolicy) => void;
  disabled?: boolean;
}

export const AutonomyModeSelector: React.FC<AutonomyModeSelectorProps> = ({
  policy,
  onPolicyChange,
  disabled = false,
}) => {
  const [isUpdating, setIsUpdating] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const currentMode: AutonomyMode = policy?.autonomy_mode || 'APPROVAL_REQUIRED';

  const handleModeSelect = async (mode: AutonomyMode) => {
    if (disabled || isUpdating || mode === currentMode) return;
    setIsUpdating(true);
    setErrorMsg(null);
    try {
      const updated = await updateMerchantAutonomyPolicy('MID-DEMO-98234', {
        autonomy_mode: mode,
      });
      onPolicyChange(updated);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to update autonomy policy';
      setErrorMsg(message);
    } finally {
      setIsUpdating(false);
    }
  };

  const modeDescriptions: Record<AutonomyMode, { title: string; badge: string; desc: string; icon: React.ReactNode; color: string }> = {
    APPROVAL_REQUIRED: {
      title: 'Approval Required',
      badge: 'DEFAULT / SAFE',
      desc: 'All candidate actions require explicit human sign-off before simulation execution.',
      icon: <Lock className="w-4 h-4 text-[#002E6E]" />,
      color: 'border-[#002E6E] bg-sky-50/60 text-[#002E6E] ring-1 ring-[#002E6E]/20',
    },
    AUTO_APPROVE_SAFE: {
      title: 'Auto-Approve Safe',
      badge: 'RISK ≤ 0.30',
      desc: 'Deterministic auto-approval for low-risk actions passing all 16 safety checks.',
      icon: <Zap className="w-4 h-4 text-emerald-600" />,
      color: 'border-emerald-500 bg-emerald-50/60 text-emerald-950 ring-1 ring-emerald-500/20',
    },
    FULL_AUTONOMY: {
      title: 'Full Autonomy',
      badge: 'RISK ≤ 0.50',
      desc: 'Broader deterministic auto-approval. Hard guardrail BLOCK still halts execution.',
      icon: <Shield className="w-4 h-4 text-amber-600" />,
      color: 'border-amber-500 bg-amber-50/60 text-amber-950 ring-1 ring-amber-500/20',
    },
  };

  return (
    <div className="bg-white border border-slate-200/90 rounded-xl p-5 shadow-xs space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 bg-blue-50 text-[#002E6E] rounded-lg border border-blue-200/60">
            <Sliders className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="font-bold text-slate-900 text-sm sm:text-base">
                Controlled Autonomy Engine
              </h3>
              <span className="px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                Phase 12
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Autonomous execution bounded by strict deterministic safety rules. Autonomy never overrides safety.
            </p>
          </div>
        </div>

        {/* Prototype boundary badge */}
        <div className="flex items-center space-x-2">
          <span className="inline-flex items-center px-2.5 py-1 rounded text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            <Shield className="w-3.5 h-3.5 mr-1 text-slate-500" />
            SIMULATED DIGITAL TWIN
          </span>
        </div>
      </div>

      {/* Mode Selector Buttons */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {(['APPROVAL_REQUIRED', 'AUTO_APPROVE_SAFE', 'FULL_AUTONOMY'] as AutonomyMode[]).map((mode) => {
          const isSelected = currentMode === mode;
          const conf = modeDescriptions[mode];

          return (
            <button
              key={mode}
              type="button"
              onClick={() => handleModeSelect(mode)}
              disabled={disabled || isUpdating}
              className={`text-left p-3.5 rounded-xl border-2 transition-all flex flex-col justify-between ${
                isSelected
                  ? `${conf.color} shadow-xs`
                  : 'border-slate-200/80 hover:border-slate-300 bg-slate-50/50 text-slate-700'
              } ${disabled || isUpdating ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'}`}
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="inline-flex items-center space-x-1.5 font-bold text-xs text-slate-900">
                    {conf.icon}
                    <span>{conf.title}</span>
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white border border-current font-bold">
                    {conf.badge}
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 line-clamp-2 leading-relaxed">
                  {conf.desc}
                </p>
              </div>

              <div className="mt-3 pt-2 border-t border-slate-200/60 flex items-center justify-between text-[11px]">
                <span className="font-bold text-[10px] tracking-wider uppercase text-slate-500">
                  {isSelected ? 'Active Policy' : 'Select Policy'}
                </span>
                {isSelected && <CheckCircle2 className="w-3.5 h-3.5 text-current" />}
              </div>
            </button>
          );
        })}
      </div>

      {/* Invariant & Threshold Badges */}
      <div className="bg-slate-50 rounded-lg p-3 border border-slate-200/80 text-xs space-y-2">
        <div className="flex items-center justify-between text-slate-700">
          <span className="font-bold flex items-center text-xs">
            <Info className="w-3.5 h-3.5 mr-1.5 text-[#002E6E]" />
            Deterministic Invariants Enforced:
          </span>
          <span className="font-mono text-[11px] text-slate-500">
            Policy v1.0.0 (Zero LLM authority)
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1 text-[11px]">
          <div className="flex items-center space-x-1.5 text-slate-700">
            <span className="w-2 h-2 rounded-full bg-rose-500"></span>
            <span><strong>BLOCK</strong> + Any Mode = BLOCKED</span>
          </div>
          <div className="flex items-center space-x-1.5 text-slate-700">
            <span className="w-2 h-2 rounded-full bg-amber-500"></span>
            <span><strong>ESCALATE</strong> = Requires Human</span>
          </div>
          <div className="flex items-center space-x-1.5 text-slate-700">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            <span><strong>MODIFY</strong> = Clamped Executed</span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 pt-1.5 border-t border-slate-200/80 text-[11px] text-slate-500">
          <span>Max Budget: <strong className="text-slate-800">₹12,000</strong></span>
          <span>•</span>
          <span>Max Discount: <strong className="text-slate-800">₹100</strong></span>
          <span>•</span>
          <span>Safe Risk Threshold: <strong className="text-slate-800">≤ 0.30</strong></span>
          <span>•</span>
          <span>Full Autonomy Risk: <strong className="text-slate-800">≤ 0.50</strong></span>
        </div>
      </div>

      {errorMsg && (
        <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700 flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}
    </div>
  );
};
