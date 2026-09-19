'use client';

import React, { useEffect, useState } from 'react';
import {
  Sparkles,
  Send,
  HelpCircle,
  ShieldCheck,
  Zap,
  Info,
  Layers,
  CheckCircle2,
} from 'lucide-react';
import { askMitraCopilot, fetchAIStatus } from '@/lib/api';
import { AIProviderStatus, AIResponse } from '@/types';

interface AICopilotPanelProps {
  correlationId?: string;
  actionId?: string;
}

const PRESET_CHIPS = [
  'Why did evening orders drop?',
  'How do guardrails protect my margin?',
  'What is the expected ROI for this action?',
  'Explain why Rs 150 was modified to Rs 100',
];

export const AICopilotPanel: React.FC<AICopilotPanelProps> = ({
  correlationId,
  actionId,
}) => {
  const [status, setStatus] = useState<AIProviderStatus | null>(null);
  const [question, setQuestion] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [currentResponse, setCurrentResponse] = useState<AIResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadStatus() {
      try {
        const s = await fetchAIStatus();
        setStatus(s);
      } catch (err) {
        console.warn('Could not fetch AI status:', err);
      }
    }
    loadStatus();
  }, []);

  const handleAsk = async (qText: string) => {
    if (!qText.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await askMitraCopilot({
        question: qText,
        correlation_id: correlationId || 'wf-evn-decline-01',
        action_id: actionId,
      });
      setCurrentResponse(res);
    } catch (err: unknown) {
      console.error('Copilot request failed:', err);
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-[#001938] border border-[#002e6e]/60 rounded-xl shadow-sm text-slate-100 overflow-hidden">
      {/* Top Bar: Title & Provider Telemetry */}
      <div className="bg-[#00122b] px-5 py-3.5 border-b border-[#002e6e]/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-[#00BAF2]/10 border border-[#00BAF2]/30 flex items-center justify-center text-[#00BAF2]">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xs font-bold text-white uppercase tracking-wider">MITRA Copilot</h2>
              <span className="bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 text-[10px] font-mono font-bold px-2 py-0.5 rounded-full">
                NON-AUTHORITATIVE ADVISORY
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Merchant Q&amp;A &amp; Hypothesis Explainability • Grounded in Digital Twin Telemetry
            </p>
          </div>
        </div>

        {/* AI Provider Badge */}
        <div className="flex items-center gap-2 bg-[#001f47] border border-[#002e6e]/80 px-3 py-1.5 rounded-lg text-xs shadow-xs">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-slate-400 text-[11px]">Provider:</span>
          <span className="text-[#00BAF2] font-mono font-semibold text-[11px]">
            {status?.active_provider
              ? (status.active_provider.toLowerCase().includes('gemini') ? 'Gemini 2.5 Flash' : status.active_provider)
              : 'Gemini 2.5 Flash'}
          </span>
        </div>
      </div>

      {/* Body */}
      <div className="p-5 space-y-4">
        {/* Preset Prompt Chips */}
        <div>
          <div className="text-[11px] font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <HelpCircle className="w-3.5 h-3.5 text-[#00BAF2]" />
            <span>Suggested Merchant Questions:</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {PRESET_CHIPS.map((chip, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  setQuestion(chip);
                  handleAsk(chip);
                }}
                disabled={isLoading}
                className="text-xs bg-[#002654] hover:bg-[#003370] active:scale-[0.98] border border-[#003b82] text-slate-200 px-3 py-1.5 rounded-lg transition-all cursor-pointer text-left disabled:opacity-50 shadow-xs"
              >
                {chip}
              </button>
            ))}
          </div>
        </div>

        {/* Input Form */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleAsk(question);
          }}
          className="flex items-center gap-2"
        >
          <div className="relative flex-1">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask MITRA about signals, hypotheses, guardrails, or business impact..."
              disabled={isLoading}
              className="w-full bg-[#00122b] border border-[#002e6e] rounded-lg px-3.5 py-2 text-xs text-slate-100 placeholder-slate-400 focus:outline-hidden focus:ring-1 focus:ring-[#00BAF2] focus:border-[#00BAF2] disabled:opacity-50"
            />
          </div>
          <button
            type="submit"
            disabled={isLoading || !question.trim()}
            className="bg-[#00BAF2] hover:bg-[#009ecc] active:scale-[0.98] text-[#001D47] font-bold px-4 py-2 rounded-lg text-xs flex items-center justify-center gap-1.5 shadow-sm transition-all cursor-pointer disabled:opacity-40"
          >
            {isLoading ? (
              <Zap className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Send className="w-3.5 h-3.5" />
            )}
            <span>{isLoading ? 'Reasoning...' : 'Ask Copilot'}</span>
          </button>
        </form>

        {/* AI Response Display */}
        {currentResponse && (
          <div className="mt-4 bg-[#00122b] border border-[#002e6e]/70 rounded-xl p-4 space-y-3 shadow-xs">
            <div className="flex items-center justify-between gap-2 border-b border-[#002e6e]/50 pb-2.5">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span className="text-xs font-bold text-white">Copilot Explanation</span>
                <span className="text-[10px] font-mono bg-[#002654] text-sky-200 border border-[#003b82] px-2 py-0.5 rounded-full">
                  {currentResponse.provider}
                </span>
                {currentResponse.is_cached && (
                  <span className="text-[10px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/30 px-2 py-0.5 rounded-full flex items-center gap-1">
                    <Zap className="w-2.5 h-2.5" /> Cached
                  </span>
                )}
              </div>
              <span className="text-[10px] text-slate-400 font-mono">
                ID: {currentResponse.response_id.slice(0, 14)}
              </span>
            </div>

            {/* Answer Text */}
            <div className="text-xs text-slate-200 leading-relaxed whitespace-pre-line font-normal">
              {currentResponse.answer}
            </div>

            {/* Grounding Fact IDs */}
            {currentResponse.fact_ids && currentResponse.fact_ids.length > 0 && (
              <div className="pt-2 border-t border-[#002e6e]/40">
                <div className="text-[10px] font-bold text-slate-300 uppercase tracking-wider mb-1.5 flex items-center gap-1">
                  <Layers className="w-3 h-3 text-[#00BAF2]" />
                  <span>Grounding Data Provenance:</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {currentResponse.fact_ids.map((fid, idx) => (
                    <span
                      key={idx}
                      className="bg-[#002654] border border-[#00BAF2]/40 text-[#00BAF2] text-[10px] font-mono px-2 py-0.5 rounded-full font-bold shadow-xs"
                    >
                      {fid}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Non-authoritative Disclaimer */}
            <div className="bg-[#001d42] border border-[#002e6e]/60 rounded-lg p-2.5 flex items-start gap-2 text-[11px] text-slate-300">
              <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <span>
                <strong className="text-white">Safety Policy:</strong> {currentResponse.disclaimer}
              </span>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-rose-950/40 border border-rose-800 text-rose-300 rounded-lg p-3 text-xs flex items-center gap-2">
            <Info className="w-4 h-4 text-rose-400 shrink-0" />
            <span>Copilot error: {error}</span>
          </div>
        )}
      </div>
    </div>
  );
};
