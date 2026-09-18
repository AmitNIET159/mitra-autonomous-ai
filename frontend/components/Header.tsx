'use client';

import React, { useState } from 'react';
import { MerchantProfile } from '@/types';
import { Store, RotateCcw, Check, ShieldCheck, Sparkles } from 'lucide-react';
import { resetDemo } from '@/lib/api';

interface HeaderProps {
  merchant: MerchantProfile;
  simulationMode: boolean;
  aiProvider?: string;
  onResetComplete?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  merchant,
  simulationMode,
  aiProvider,
  onResetComplete,
}) => {
  const [resetting, setResetting] = useState<boolean>(false);
  const [resetSuccess, setResetSuccess] = useState<boolean>(false);
  const [lastAuditCount, setLastAuditCount] = useState<number | null>(null);

  const handleReset = async () => {
    if (resetting) return; // double-click protection
    try {
      setResetting(true);
      const res = await resetDemo();
      setResetSuccess(true);
      if (res && typeof res.audit_events_count === 'number') {
        setLastAuditCount(res.audit_events_count);
      }
      if (onResetComplete) {
        onResetComplete();
      }
      setTimeout(() => setResetSuccess(false), 4000);
    } catch (err) {
      console.error('Reset demo failed:', err);
    } finally {
      setResetting(false);
    }
  };

  const displayModelName = aiProvider?.includes('gemini')
    ? 'Gemini 2.5 Flash'
    : (aiProvider || 'Gemini 2.5 Flash');

  return (
    <header className="border-b border-slate-200 bg-white shadow-xs">
      {/* Intentional Product State Simulation Banner */}
      {simulationMode && (
        <div className="bg-slate-900 text-slate-100 border-b border-slate-800 px-4 py-2 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2 font-medium">
            <span className="bg-[#00BAF2] text-[#002E6E] font-extrabold text-[10px] tracking-wider px-1.5 py-0.5 rounded">
              DIGITAL TWIN
            </span>
            <span className="text-slate-300">
              <strong>SIMULATED DATA ENVIRONMENT:</strong> Prototype digital-twin sandbox for Hackathon demonstration. Preserves cryptographic audit ledger across demo resets.
            </span>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-[11px] text-slate-400 font-mono hidden md:inline">
              Paytm Build for India • Track 3: Autonomous AI Teammates
            </span>

            {/* RESET DEMO BUTTON WITH DOUBLE-CLICK PROTECTION & AUDIT INTEGRITY BADGE */}
            <button
              onClick={handleReset}
              disabled={resetting}
              className="bg-[#002E6E] hover:bg-[#003b8c] text-white border border-[#00BAF2]/40 px-3 py-1 rounded text-xs font-bold flex items-center gap-1.5 transition-all shadow-xs disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
              title="Deterministically reset demo simulation baseline while strictly preserving cryptographic audit history"
            >
              {resetSuccess ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-emerald-300 font-mono">
                    Baseline Restored {lastAuditCount ? `(${lastAuditCount} Audits Kept)` : ''}
                  </span>
                </>
              ) : (
                <>
                  <RotateCcw className={`w-3.5 h-3.5 text-[#00BAF2] ${resetting ? 'animate-spin' : ''}`} />
                  <span>{resetting ? 'Resetting Demo...' : 'RESET DEMO'}</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Main Navigation Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* MITRA Brand */}
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-[#002E6E] flex items-center justify-center text-white font-black text-xl tracking-wider shadow-sm shadow-slate-200">
            M
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-[#002E6E] tracking-tight">MITRA</h1>
              <span className="bg-[#00BAF2]/15 text-[#007EA7] text-[11px] font-semibold px-2 py-0.5 rounded-full flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-[#00BAF2]" />
                Autonomous Teammate
              </span>
            </div>
            <p className="text-xs text-slate-500 font-medium">
              Autonomous Merchant Command Center • <span className="text-slate-700 font-semibold">Team Pica pica</span>
            </p>
          </div>
        </div>

        {/* AI Provider Telemetry Badge - STRICT GEMINI 2.5 FLASH */}
        <div className="flex items-center gap-2 bg-slate-900 border border-slate-700 px-3.5 py-1.5 rounded-lg text-xs shadow-xs">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5">
              <span className="text-slate-400 text-[10px] uppercase font-semibold">Model:</span>
              <span className="text-[#00BAF2] font-mono font-bold text-[11px]">
                {displayModelName}
              </span>
            </div>
            <span className="text-[9px] text-slate-400 flex items-center gap-1">
              <ShieldCheck className="w-2.5 h-2.5 text-emerald-400" />
              Non-authoritative advisory layer
            </span>
          </div>
        </div>

        {/* Merchant Context */}
        <div className="flex items-center gap-3 bg-slate-50 border border-slate-200/80 rounded-lg px-3.5 py-2 text-sm">
          <div className="h-9 w-9 rounded-full bg-blue-100 flex items-center justify-center text-[#002E6E] shrink-0">
            <Store className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <div className="text-xs font-bold text-slate-900">{merchant.name}</div>
              <span className="bg-slate-200 text-slate-700 text-[10px] font-mono px-1.5 py-0.5 rounded">
                SIMULATED DIGITAL TWIN
              </span>
            </div>
            <div className="text-[11px] text-slate-500 flex items-center gap-2 mt-0.5">
              <span className="font-mono font-semibold text-slate-700">{merchant.id}</span>
              <span>•</span>
              <span>{merchant.category}</span>
              <span>•</span>
              <span>{merchant.location}</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
