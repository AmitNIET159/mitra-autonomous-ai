'use client';

import React, { useEffect, useState } from 'react';
import { FileText, HelpCircle, RotateCw, ShieldAlert, ShieldCheck } from 'lucide-react';
import { AuditEvent, WorkflowAuditVerification } from '@/types';
import { fetchAuditEvents, fetchWorkflowAudit, verifyWorkflowAudit } from '@/lib/api';

interface AuditActivityAreaProps {
  correlationId?: string;
  onOpenExplainability?: () => void;
  reloadTrigger?: number;
}

export const AuditActivityArea: React.FC<AuditActivityAreaProps> = ({
  correlationId,
  onOpenExplainability,
  reloadTrigger = 0,
}) => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [verification, setVerification] = useState<WorkflowAuditVerification | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  useEffect(() => {
    let isSubscribed = true;

    async function loadAuditData() {
      setIsLoading(true);
      try {
        let evts: AuditEvent[] = [];
        if (correlationId) {
          evts = await fetchWorkflowAudit(correlationId);
        } else {
          evts = await fetchAuditEvents('MID-DEMO-98234', undefined, 20);
        }

        if (isSubscribed) {
          setEvents(evts);
        }

        // Verify cryptographic chain
        const activeCorr = correlationId || (evts.length > 0 ? evts[0].correlation_id : undefined);
        if (activeCorr) {
          const ver = await verifyWorkflowAudit(activeCorr);
          if (isSubscribed) {
            setVerification(ver);
          }
        }
      } catch (err) {
        console.warn('Failed to load live audit events:', err);
      } finally {
        if (isSubscribed) setIsLoading(false);
      }
    }

    loadAuditData();
    return () => {
      isSubscribed = false;
    };
  }, [correlationId, reloadTrigger]);

  const isChainValid = verification?.valid ?? (events.length > 0);

  return (
    <div className="bg-white border border-slate-200/90 rounded-xl p-5 shadow-xs space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-blue-50 border border-blue-200/70 text-[#002E6E]">
            <FileText className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Authoritative Audit Trail (SHA-256 Chained)
            </h2>
            <p className="text-xs text-slate-500">
              Cryptographically linked ledger in SQLite — Tamper-evident &amp; non-repudiable
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {verification && (
            <span
              className={`inline-flex items-center gap-1 text-[10px] font-bold px-2.5 py-0.5 rounded-full border ${
                isChainValid
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-rose-50 text-rose-700 border-rose-200'
              }`}
            >
              {isChainValid ? (
                <>
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                  <span>CHAIN VERIFIED</span>
                </>
              ) : (
                <>
                  <ShieldAlert className="w-3.5 h-3.5 text-rose-600" />
                  <span>TAMPER DETECTED</span>
                </>
              )}
            </span>
          )}

          {onOpenExplainability && (
            <button
              onClick={onOpenExplainability}
              className="flex items-center gap-1.5 text-xs font-bold px-3.5 py-1.5 bg-[#002E6E] hover:bg-[#001D47] active:scale-[0.98] text-white rounded-lg shadow-xs transition-all cursor-pointer"
            >
              <HelpCircle className="w-3.5 h-3.5 text-[#00BAF2]" />
              <span>Explain Workflow (Why MITRA?)</span>
            </button>
          )}
        </div>
      </div>

      <div className="divide-y divide-slate-100">
        {isLoading && events.length === 0 ? (
          <div className="py-6 text-center text-xs text-slate-400 flex items-center justify-center gap-2">
            <RotateCw className="w-4 h-4 animate-spin text-slate-400" />
            <span>Loading authoritative audit trail...</span>
          </div>
        ) : events.length === 0 ? (
          <div className="py-6 text-center text-xs text-slate-400 italic">
            No audit events recorded yet for this session.
          </div>
        ) : (
          events.map((entry) => (
            <div
              key={entry.event_id || entry.id}
              className="py-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs"
            >
              <div className="flex items-start gap-2.5">
                <span className="font-mono text-[10px] bg-sky-50 text-[#002E6E] border border-sky-200 font-bold px-2 py-0.5 rounded-full shrink-0">
                  {entry.stage}
                </span>
                <div>
                  <div className="font-bold text-slate-800">{entry.action_description || entry.description}</div>
                  <div className="text-[11px] text-slate-500 flex items-center gap-2 mt-0.5">
                    <span>Actor: <strong className="text-slate-700">{entry.actor || entry.source}</strong></span>
                    <span>•</span>
                    <span>{entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString() : 'Recent'}</span>
                    {entry.correlation_id && (
                      <>
                        <span>•</span>
                        <span className="font-mono text-[10px] text-slate-500">{entry.correlation_id}</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <div
                  className="text-[10px] font-mono text-slate-500 bg-slate-50 px-2 py-1 rounded-md border border-slate-200/70 truncate max-w-[130px]"
                  title={`Digest: ${entry.integrity_hash || ''}\nPrev: ${entry.previous_hash || ''}`}
                >
                  hash: {entry.integrity_hash ? entry.integrity_hash.substring(0, 10) : '...'}...
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
