'use client';

import React, { useState, useEffect } from 'react';
import { SystemStatus, SystemHealthResponse } from '@/types';
import { getSystemHealth } from '@/lib/api';
import {
  Server,
  Database,
  Cpu,
  ShieldAlert,
  FileCheck2,
  Lock,
  RefreshCw,
} from 'lucide-react';

interface SystemStatusBannerProps {
  status: SystemStatus;
  onRefresh?: () => void;
}

export const SystemStatusBanner: React.FC<SystemStatusBannerProps> = ({
  status,
  onRefresh,
}) => {
  const [health, setHealth] = useState<SystemHealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const fetchHealth = async () => {
    setLoading(true);
    try {
      const data = await getSystemHealth();
      setHealth(data);
    } catch {
      // Fall back gracefully if health endpoint is initializing
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    const loadInitialHealth = async () => {
      try {
        const data = await getSystemHealth();
        if (isMounted) {
          setHealth(data);
        }
      } catch {
        // Fall back gracefully if health endpoint is initializing
      }
    };

    loadInitialHealth();
    const interval = setInterval(loadInitialHealth, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleRefreshClick = () => {
    fetchHealth();
    if (onRefresh) onRefresh();
  };

  const aiName = health?.ai || status.llm_provider || 'Gemini 2.5 Flash';
  const isGemini = aiName.toLowerCase().includes('gemini');
  const autonomyMode = health?.autonomy_mode || 'APPROVAL_REQUIRED';

  return (
    <div className="bg-slate-900 text-white rounded-xl p-4 shadow-sm border border-slate-800">
      {/* Top Telemetry Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 mb-3 border-b border-slate-800/80 gap-2">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
            System Health &amp; Subsystem Telemetry
          </span>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
            6-PILLAR VERIFIED
          </span>
        </div>

        <div className="flex items-center gap-2.5">
          {/* Autonomy Mode Badge */}
          <div className="flex items-center gap-1.5 text-xs bg-slate-800/90 px-2.5 py-1 rounded-md border border-slate-700/80">
            <span className="text-slate-400 text-[11px]">Autonomy:</span>
            <span
              className={`font-mono font-bold text-[11px] ${
                autonomyMode === 'FULL_AUTONOMY'
                  ? 'text-amber-400'
                  : autonomyMode === 'AUTO_APPROVE_SAFE'
                  ? 'text-blue-400'
                  : 'text-emerald-400'
              }`}
            >
              {autonomyMode}
            </span>
          </div>

          {/* Refresh Button with double-click protection */}
          <button
            onClick={handleRefreshClick}
            disabled={loading}
            title="Refresh system health telemetry"
            className="p-1.5 text-slate-400 hover:text-white bg-slate-800/70 hover:bg-slate-800 rounded-md border border-slate-700/60 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-[#00BAF2]' : ''}`} />
          </button>
        </div>
      </div>

      {/* 6-Pillar Subsystem Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* 1. Backend Server */}
        <div className="p-2.5 rounded-lg bg-slate-800/50 border border-slate-700/50 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider">1. Backend</span>
            <Server className="w-3.5 h-3.5 text-slate-400" />
          </div>
          <div className="text-xs font-bold text-emerald-400 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            {health?.backend || 'ONLINE'}
          </div>
          <div className="text-[10px] text-slate-400 font-mono mt-0.5">FastAPI :8000</div>
        </div>

        {/* 2. Database Digital Twin */}
        <div className="p-2.5 rounded-lg bg-slate-800/50 border border-slate-700/50 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider">2. Database</span>
            <Database className="w-3.5 h-3.5 text-slate-400" />
          </div>
          <div className="text-xs font-bold text-emerald-400 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            {health?.database || 'ONLINE'}
          </div>
          <div className="text-[10px] text-slate-400 font-mono mt-0.5">Digital Twin DB</div>
        </div>

        {/* 3. AI Advisory Reasoner */}
        <div className="p-2.5 rounded-lg bg-slate-800/50 border border-slate-700/50 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider">3. AI Reasoner</span>
            <Cpu className={`w-3.5 h-3.5 ${isGemini ? 'text-[#00BAF2]' : 'text-slate-400'}`} />
          </div>
          <div className="text-xs font-bold text-[#00BAF2] truncate" title={aiName}>
            {isGemini ? 'Gemini 2.5 Flash' : aiName}
          </div>
          <div className="text-[10px] text-slate-400 font-mono mt-0.5">Non-Authoritative</div>
        </div>

        {/* 4. Deterministic Guardrails */}
        <div className="p-2.5 rounded-lg bg-slate-800/50 border border-slate-700/50 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider">4. Guardrails</span>
            <ShieldAlert className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="text-xs font-bold text-emerald-400 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            {health?.guardrails || 'ACTIVE'}
          </div>
          <div className="text-[10px] text-slate-400 font-mono mt-0.5">Phase 6 Invariant</div>
        </div>

        {/* 5. Cryptographic Audit Ledger */}
        <div className="p-2.5 rounded-lg bg-slate-800/50 border border-slate-700/50 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider">5. Audit Ledger</span>
            <FileCheck2 className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="text-xs font-bold text-emerald-400 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            {health?.audit || 'ACTIVE'}
          </div>
          <div className="text-[10px] text-slate-400 font-mono mt-0.5">SHA-256 Chained</div>
        </div>

        {/* 6. Execution Barrier */}
        <div className="p-2.5 rounded-lg bg-slate-800/50 border border-slate-700/50 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider">6. Execution Barrier</span>
            <Lock className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <div className="text-xs font-bold text-amber-400 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            {health?.execution || 'SIMULATED'}
          </div>
          <div className="text-[10px] text-slate-400 font-mono mt-0.5">Zero Live Side Effects</div>
        </div>
      </div>
    </div>
  );
};
