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

  const isFallback = Boolean(
    aiProvider?.toLowerCase().includes('fallback') ||
    aiProvider?.toLowerCase().includes('offline') ||
    aiProvider?.toLowerCase().includes('client')
  );

  const displayModelName = isFallback
    ? 'Deterministic Fallback'
    : (aiProvider?.includes('gemini') ? 'Gemini 2.5 Flash' : (aiProvider || 'Gemini 2.5 Flash'));

  return (
    <header className="border-b border-slate-200/90 bg-white sticky top-0 z-30 shadow-xs">
      {/* Simulation / Digital Twin Top Notification Bar */}
      {simulationMode && (
        <div className="bg-[#001D47] text-slate-100 border-b border-[#002E6E] px-4 py-2 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
          <div className="flex items-center gap-2 font-medium">
            <span className="bg-[#00BAF2] text-[#001D47] font-black text-[10px] tracking-wider px-2 py-0.5 rounded shadow-xs">
              DIGITAL TWIN
            </span>
            <span className="text-slate-200 text-xs">
              <strong>SANDBOX SIMULATION:</strong> Preserves cryptographic SHA-256 audit ledger across demo resets. Zero production side effects.
            </span>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-[11px] text-slate-300/80 font-mono hidden lg:inline">
              Paytm Build for India • Track 3: Autonomous AI Teammates
            </span>

            {/* RESET DEMO BUTTON */}
            <button
              onClick={handleReset}
              disabled={resetting}
              className="bg-[#002E6E] hover:bg-[#003b8c] active:bg-[#001D47] text-white border border-[#00BAF2]/50 hover:border-[#00BAF2] px-3.5 py-1.5 rounded-lg text-xs font-bold flex items-center gap-2 transition-all shadow-xs disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
              title="Deterministically reset demo simulation baseline while strictly preserving cryptographic audit history"
            >
              {resetSuccess ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-emerald-300 font-mono text-xs">
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
        {/* MITRA Identity */}
        <div className="flex items-center gap-3">
          <div className="h-11 w-11 rounded-xl bg-gradient-to-br from-[#002E6E] to-[#001D47] border border-[#00BAF2]/30 flex items-center justify-center text-white font-black text-2xl tracking-wider shadow-sm shadow-blue-950/10">
            M
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-extrabold text-[#002E6E] tracking-tight">MITRA</h1>
              <span className="bg-sky-50 text-[#007EA7] border border-sky-200 text-[11px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-[#00BAF2]" />
                AI Merchant Teammate
              </span>
            </div>
            <p className="text-xs text-slate-500 font-medium">
              Autonomous Merchant Operations • <span className="text-slate-700 font-semibold">Team Pica pica</span>
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* AI Provider Telemetry Badge */}
          <div className="flex items-center gap-2.5 bg-[#0f172a] border border-slate-700/80 px-3.5 py-2 rounded-xl text-xs shadow-xs">
            <span
              className={`w-2 h-2 rounded-full ${
                isFallback ? 'bg-amber-400' : 'bg-emerald-400 animate-pulse'
              }`}
            />
            <div className="flex flex-col">
              <div className="flex items-center gap-1.5">
                <span className="text-slate-400 text-[10px] uppercase font-semibold">AI Layer:</span>
                <span className="text-[#00BAF2] font-mono font-bold text-[11px]">
                  {displayModelName}
                </span>
              </div>
              <span className="text-[10px] text-slate-400 flex items-center gap-1">
                <ShieldCheck className="w-3 h-3 text-emerald-400" />
                {isFallback ? 'Offline Safe Mode' : 'Non-authoritative advisory layer'}
              </span>
            </div>
          </div>

          {/* Merchant Credentials Card */}
          <div className="flex items-center gap-3 bg-slate-50 border border-slate-200/90 rounded-xl px-3.5 py-2 text-sm shadow-xs">
            <div className="h-9 w-9 rounded-lg bg-blue-100/80 border border-blue-200/70 flex items-center justify-center text-[#002E6E] shrink-0">
              <Store className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-900">{merchant.name}</span>
                <span className="bg-slate-200/80 text-slate-700 text-[10px] font-mono font-bold px-1.5 py-0.5 rounded">
                  {merchant.id}
                </span>
              </div>
              <div className="text-[11px] text-slate-500 flex items-center gap-1.5 mt-0.5 font-medium">
                <span>{merchant.category}</span>
                <span>•</span>
                <span>{merchant.location}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
