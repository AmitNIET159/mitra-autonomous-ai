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
      icon: <Lock className="w-4 h-4" />,
      color: 'border-blue-500 bg-blue-50 text-blue-900 dark:bg-blue-950/40 dark:text-blue-200 dark:border-blue-600',
    },
    AUTO_APPROVE_SAFE: {
      title: 'Auto-Approve Safe',
      badge: 'RISK ≤ 0.30',
      desc: 'Deterministic auto-approval for low-risk actions passing all 16 safety checks.',
      icon: <Zap className="w-4 h-4" />,
      color: 'border-emerald-500 bg-emerald-50 text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200 dark:border-emerald-600',
    },
    FULL_AUTONOMY: {
      title: 'Full Autonomy',
      badge: 'RISK ≤ 0.50',
      desc: 'Broader deterministic auto-approval. Hard guardrail BLOCK still halts execution.',
      icon: <Shield className="w-4 h-4" />,
      color: 'border-purple-500 bg-purple-50 text-purple-900 dark:bg-purple-950/40 dark:text-purple-200 dark:border-purple-600',
    },
  };

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100 dark:border-slate-800">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 rounded-lg">
            <Sliders className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm sm:text-base">
                Controlled Autonomy Engine
              </h3>
              <span className="px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase rounded-full bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300">
                Phase 12
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Autonomous execution bounded by strict deterministic safety rules. Autonomy never overrides safety.
            </p>
          </div>
        </div>

        {/* Prototype boundary badge */}
        <div className="flex items-center space-x-2">
          <span className="inline-flex items-center px-2.5 py-1 rounded text-[11px] font-medium bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
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
              className={`text-left p-3.5 rounded-lg border-2 transition-all flex flex-col justify-between ${
                isSelected
                  ? `${conf.color} shadow-sm ring-1 ring-offset-1 ring-indigo-400 dark:ring-offset-slate-900`
                  : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 bg-slate-50/50 dark:bg-slate-800/40 text-slate-700 dark:text-slate-300'
              } ${disabled || isUpdating ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'}`}
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="inline-flex items-center space-x-1.5 font-medium text-xs">
                    {conf.icon}
                    <span>{conf.title}</span>
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/70 dark:bg-black/30 border border-current font-bold">
                    {conf.badge}
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 dark:text-slate-400 line-clamp-2 leading-relaxed">
                  {conf.desc}
                </p>
              </div>

              <div className="mt-3 pt-2 border-t border-current/10 flex items-center justify-between text-[11px]">
                <span className="font-semibold text-[10px] tracking-wider uppercase">
                  {isSelected ? 'Active Mode' : 'Switch Mode'}
                </span>
                {isSelected && <CheckCircle2 className="w-3.5 h-3.5" />}
              </div>
            </button>
          );
        })}
      </div>

      {/* Invariant & Threshold Badges */}
      <div className="bg-slate-50 dark:bg-slate-800/60 rounded-lg p-3 border border-slate-200 dark:border-slate-700 text-xs space-y-2">
        <div className="flex items-center justify-between text-slate-700 dark:text-slate-300">
          <span className="font-medium flex items-center">
            <Info className="w-3.5 h-3.5 mr-1.5 text-indigo-500" />
            Deterministic Invariants Enforced:
          </span>
          <span className="font-mono text-[11px] text-slate-500">
            Policy v1.0.0 (Zero LLM authority)
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1 text-[11px]">
          <div className="flex items-center space-x-1.5 text-slate-600 dark:text-slate-400">
            <span className="w-1.5 h-1.5 rounded-full bg-red-500"></span>
            <span>BLOCK + Any Mode = BLOCKED</span>
          </div>
          <div className="flex items-center space-x-1.5 text-slate-600 dark:text-slate-400">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
            <span>ESCALATE = Requires Human</span>
          </div>
          <div className="flex items-center space-x-1.5 text-slate-600 dark:text-slate-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            <span>MODIFY = Clamped Executed</span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 pt-1.5 border-t border-slate-200/80 dark:border-slate-700 text-[11px] text-slate-500">
          <span>Max Budget: <strong className="text-slate-700 dark:text-slate-300">₹12,000</strong></span>
          <span>•</span>
          <span>Max Discount: <strong className="text-slate-700 dark:text-slate-300">₹100</strong></span>
          <span>•</span>
          <span>Safe Risk Threshold: <strong className="text-slate-700 dark:text-slate-300">≤ 0.30</strong></span>
          <span>•</span>
          <span>Full Autonomy Risk: <strong className="text-slate-700 dark:text-slate-300">≤ 0.50</strong></span>
        </div>
      </div>

      {errorMsg && (
        <div className="p-2.5 rounded-lg bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-xs text-red-700 dark:text-red-300 flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}
    </div>
  );
};
