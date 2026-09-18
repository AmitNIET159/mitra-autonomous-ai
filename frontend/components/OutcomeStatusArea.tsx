'use client';

import React, { useState } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  BarChart3,
  Calendar,
  CheckCircle2,
  Clock,
  Eye,
  Info,
  Loader2,
  TrendingUp,
} from 'lucide-react';
import { ExecutionResult, OutcomeResult } from '@/types';

interface OutcomeStatusAreaProps {
  execution: ExecutionResult | null;
  outcome: OutcomeResult | null;
  onMeasureOutcome: () => Promise<void>;
  isMeasuring?: boolean;
}

export const OutcomeStatusArea: React.FC<OutcomeStatusAreaProps> = ({
  execution,
  outcome,
  onMeasureOutcome,
  isMeasuring = false,
}) => {
  const [activeTab, setActiveTab] = useState<'metrics' | 'windows'>('metrics');

  const isExecutionCompleted = execution?.execution_state === 'COMPLETED';

  // Status styling
  const getStatusBadge = () => {
    if (!outcome) {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-700 border border-gray-300">
          <Clock className="w-3.5 h-3.5 mr-1" />
          PENDING MEASUREMENT
        </span>
      );
    }
    switch (outcome.outcome_status) {
      case 'MEASURED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
            <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
            SIMULATED OBSERVATION AVAILABLE
          </span>
        );
      case 'INSUFFICIENT_DATA':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-300">
            <AlertTriangle className="w-3.5 h-3.5 mr-1" />
            INSUFFICIENT DATA
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800 border border-red-300">
            <AlertTriangle className="w-3.5 h-3.5 mr-1" />
            MEASUREMENT FAILED
          </span>
        );
      default:
        return null;
    }
  };

  const eveningChange = outcome?.metric_changes?.evening_orders;
  const ordersChange = outcome?.metric_changes?.orders;
  const revenueChange = outcome?.metric_changes?.revenue;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden mb-6">
      {/* Header */}
      <div className="p-5 border-b border-slate-100 bg-slate-50/50 flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <BarChart3 className="w-5 h-5 text-indigo-600" />
            <h3 className="text-base font-bold text-slate-900">
              Phase 9: Outcome Monitoring & Measurement
            </h3>
            {getStatusBadge()}
          </div>
          <p className="text-xs text-slate-500">
            Measures observed business metrics in the digital-twin sandbox post-execution.
          </p>
        </div>

        {/* Action Button */}
        <div>
          <button
            onClick={onMeasureOutcome}
            disabled={!isExecutionCompleted || isMeasuring}
            className={`inline-flex items-center justify-center px-4 py-2 rounded-lg text-sm font-semibold transition-all shadow-sm ${
              !isExecutionCompleted
                ? 'bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200'
                : isMeasuring
                ? 'bg-indigo-400 text-white cursor-wait'
                : outcome
                ? 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-indigo-100'
                : 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-emerald-100 animate-pulse'
            }`}
          >
            {isMeasuring ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Measuring Sandbox Impact...
              </>
            ) : outcome ? (
              <>
                <Activity className="w-4 h-4 mr-2" />
                Re-measure Simulated Outcome
              </>
            ) : (
              <>
                <TrendingUp className="w-4 h-4 mr-2" />
                Measure Simulated Outcome
              </>
            )}
          </button>
        </div>
      </div>

      {/* Mandatory Sandbox Disclaimer Banner */}
      <div className="bg-amber-50/80 border-b border-amber-200/60 px-5 py-2.5 flex items-start gap-2.5 text-xs text-amber-900">
        <Info className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold">SIMULATED / PROTOTYPE / DIGITAL TWIN:</span>{' '}
          All measurements reflect synthetic digital-twin telemetry. No real Paytm transactions,
          customer communications, or actual financial figures are modified. Results represent
          observed simulated changes and do not constitute causal proof.
        </div>
      </div>

      {/* Main Content Area */}
      <div className="p-5">
        {!isExecutionCompleted ? (
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-6 text-center">
            <Clock className="w-8 h-8 text-slate-400 mx-auto mb-2" />
            <h4 className="text-sm font-semibold text-slate-800 mb-1">
              Simulated Execution Required First
            </h4>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              Outcome monitoring measures the post-execution observation window. Execute the
              approved action in the simulation sandbox above before measuring impact.
            </p>
          </div>
        ) : !outcome ? (
          <div className="bg-emerald-50/60 border border-emerald-200/80 rounded-lg p-6 text-center">
            <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto mb-2" />
            <h4 className="text-sm font-semibold text-emerald-950 mb-1">
              Sandbox Execution Completed — Ready for Measurement
            </h4>
            <p className="text-xs text-emerald-700 max-w-md mx-auto mb-4">
              Execution <code className="bg-emerald-100 px-1 py-0.5 rounded font-mono text-emerald-900">{execution.execution_id}</code> is
              complete. Click below to pull baseline and post-action digital twin metrics.
            </p>
            <button
              onClick={onMeasureOutcome}
              disabled={isMeasuring}
              className="inline-flex items-center px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-lg shadow-sm"
            >
              {isMeasuring ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Measuring...
                </>
              ) : (
                <>
                  <TrendingUp className="w-4 h-4 mr-2" />
                  Measure Simulated Outcome Now
                </>
              )}
            </button>
          </div>
        ) : (
          <div>
            {/* Primary Signal Highlight Card (Section 20) */}
            <div className="bg-gradient-to-br from-indigo-900 to-slate-900 rounded-xl p-5 text-white mb-6 shadow-md relative overflow-hidden">
              <div className="absolute top-0 right-0 p-8 opacity-10 pointer-events-none">
                <TrendingUp className="w-36 h-36" />
              </div>
              <div className="relative z-10">
                <div className="flex items-center justify-between gap-2 mb-3">
                  <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-200 text-xs font-medium border border-indigo-400/30">
                    <Activity className="w-3 h-3" />
                    PRIMARY SIGNAL OBSERVATION
                  </div>
                  <span className="text-xs text-slate-300 font-mono">
                    ID: {outcome.outcome_id}
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-3">
                  <div>
                    <div className="text-xs text-indigo-200 mb-0.5">Primary Target Metric</div>
                    <div className="text-lg font-bold">Evening Orders</div>
                    <div className="text-xs text-slate-300">5:00 PM – 8:59 PM slot</div>
                  </div>

                  <div className="flex items-center gap-6">
                    <div>
                      <div className="text-xs text-indigo-200 mb-0.5">Pre-Action Baseline</div>
                      <div className="text-2xl font-bold font-mono">
                        {outcome.baseline_metrics?.evening_orders ?? '—'}
                      </div>
                      <div className="text-xs text-slate-300">orders</div>
                    </div>
                    <div className="text-indigo-400 font-bold text-xl">→</div>
                    <div>
                      <div className="text-xs text-indigo-200 mb-0.5">Simulated After</div>
                      <div className="text-2xl font-bold font-mono text-emerald-400">
                        {outcome.post_action_metrics?.evening_orders ?? '—'}
                      </div>
                      <div className="text-xs text-slate-300">orders</div>
                    </div>
                  </div>

                  <div className="bg-white/10 rounded-lg p-3 border border-white/10 flex flex-col justify-center">
                    <div className="text-xs text-indigo-200 mb-0.5">Observed Simulated Change</div>
                    <div className="text-2xl font-bold text-emerald-400 flex items-center gap-1 font-mono">
                      <ArrowUpRight className="w-6 h-6" />
                      +{eveningChange?.percentage_change ?? 0}%
                    </div>
                    <div className="text-xs text-slate-300 font-mono">
                      +{eveningChange?.absolute_change ?? 0} orders during window
                    </div>
                  </div>
                </div>

                <div className="text-[11px] text-slate-300 italic pt-2 border-t border-white/10 flex items-center gap-1.5">
                  <Eye className="w-3 h-3 text-indigo-300 shrink-0" />
                  <span>
                    Non-Causal Notice: Metric changes reflect simulated digital-twin behavior during
                    the 7-day observation period.
                  </span>
                </div>
              </div>
            </div>

            {/* Tabs for Metrics vs Window Details */}
            <div className="flex items-center gap-2 border-b border-slate-200 mb-4 text-xs font-semibold">
              <button
                onClick={() => setActiveTab('metrics')}
                className={`pb-2 px-1 border-b-2 transition-colors ${
                  activeTab === 'metrics'
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-slate-500 hover:text-slate-800'
                }`}
              >
                Before vs After Metrics
              </button>
              <button
                onClick={() => setActiveTab('windows')}
                className={`pb-2 px-1 border-b-2 transition-colors ${
                  activeTab === 'windows'
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-slate-500 hover:text-slate-800'
                }`}
              >
                Observation Windows & Integrity
              </button>
            </div>

            {/* Tab 1: Metrics Table */}
            {activeTab === 'metrics' && (
              <div className="overflow-x-auto border border-slate-200 rounded-lg">
                <table className="w-full text-xs text-left">
                  <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                    <tr>
                      <th className="py-2.5 px-4">Metric</th>
                      <th className="py-2.5 px-4">Before (Baseline)</th>
                      <th className="py-2.5 px-4">After (Simulated)</th>
                      <th className="py-2.5 px-4">Observed Simulated Change</th>
                      <th className="py-2.5 px-4">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono">
                    <tr className="hover:bg-slate-50/50">
                      <td className="py-2.5 px-4 font-sans font-medium text-slate-800">
                        Total Revenue / GMV
                      </td>
                      <td className="py-2.5 px-4 text-slate-600">
                        ₹{(outcome.baseline_metrics?.revenue ?? 0).toLocaleString('en-IN')}
                      </td>
                      <td className="py-2.5 px-4 text-slate-900 font-semibold">
                        ₹{(outcome.post_action_metrics?.revenue ?? 0).toLocaleString('en-IN')}
                      </td>
                      <td className="py-2.5 px-4 text-emerald-600 font-semibold">
                        +{revenueChange?.percentage_change ?? 0}% (+₹
                        {(revenueChange?.absolute_change ?? 0).toLocaleString('en-IN')})
                      </td>
                      <td className="py-2.5 px-4 font-sans text-xs text-emerald-700">
                        Observed Lift
                      </td>
                    </tr>

                    <tr className="hover:bg-slate-50/50">
                      <td className="py-2.5 px-4 font-sans font-medium text-slate-800">
                        Total Orders
                      </td>
                      <td className="py-2.5 px-4 text-slate-600">
                        {(outcome.baseline_metrics?.orders ?? 0).toLocaleString('en-IN')}
                      </td>
                      <td className="py-2.5 px-4 text-slate-900 font-semibold">
                        {(outcome.post_action_metrics?.orders ?? 0).toLocaleString('en-IN')}
                      </td>
                      <td className="py-2.5 px-4 text-emerald-600 font-semibold">
                        +{ordersChange?.percentage_change ?? 0}% (+
                        {ordersChange?.absolute_change ?? 0})
                      </td>
                      <td className="py-2.5 px-4 font-sans text-xs text-emerald-700">
                        Observed Lift
                      </td>
                    </tr>

                    <tr className="hover:bg-slate-50/50 bg-indigo-50/20">
                      <td className="py-2.5 px-4 font-sans font-medium text-indigo-900">
                        Evening Orders (5-9 PM)
                      </td>
                      <td className="py-2.5 px-4 text-slate-600">
                        {outcome.baseline_metrics?.evening_orders ?? 0}
                      </td>
                      <td className="py-2.5 px-4 text-indigo-900 font-bold">
                        {outcome.post_action_metrics?.evening_orders ?? 0}
                      </td>
                      <td className="py-2.5 px-4 text-emerald-600 font-bold">
                        +{eveningChange?.percentage_change ?? 0}% (+
                        {eveningChange?.absolute_change ?? 0})
                      </td>
                      <td className="py-2.5 px-4 font-sans text-xs font-semibold text-emerald-700">
                        Target Recovered
                      </td>
                    </tr>

                    <tr className="hover:bg-slate-50/50">
                      <td className="py-2.5 px-4 font-sans font-medium text-slate-800">
                        Average Order Value (AOV)
                      </td>
                      <td className="py-2.5 px-4 text-slate-600">
                        ₹{outcome.baseline_metrics?.average_order_value ?? 0}
                      </td>
                      <td className="py-2.5 px-4 text-slate-900 font-semibold">
                        ₹{outcome.post_action_metrics?.average_order_value ?? 0}
                      </td>
                      <td className="py-2.5 px-4 text-slate-600">
                        {outcome.metric_changes?.average_order_value?.percentage_change ?? 0}%
                      </td>
                      <td className="py-2.5 px-4 font-sans text-xs text-slate-600">
                        Normal Range
                      </td>
                    </tr>

                    <tr className="hover:bg-slate-50/50">
                      <td className="py-2.5 px-4 font-sans font-medium text-slate-800">
                        Target Customer Conversion
                      </td>
                      <td className="py-2.5 px-4 text-slate-600">
                        {((outcome.baseline_metrics?.target_customer_conversion ?? 0) * 100).toFixed(1)}%
                      </td>
                      <td className="py-2.5 px-4 text-slate-900 font-semibold">
                        {((outcome.post_action_metrics?.target_customer_conversion ?? 0) * 100).toFixed(1)}%
                      </td>
                      <td className="py-2.5 px-4 text-emerald-600 font-semibold">
                        +{outcome.metric_changes?.target_customer_conversion?.percentage_change ?? 0}%
                      </td>
                      <td className="py-2.5 px-4 font-sans text-xs text-emerald-700">
                        Re-engagement
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            )}

            {/* Tab 2: Windows & Integrity */}
            {activeTab === 'windows' && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="border border-slate-200 rounded-lg p-4 bg-slate-50">
                  <div className="flex items-center gap-2 text-xs font-semibold text-slate-800 mb-2">
                    <Calendar className="w-4 h-4 text-slate-500" />
                    Baseline Window (Pre-Action)
                  </div>
                  <div className="text-xs text-slate-600 space-y-1 font-mono">
                    <div>Start: {outcome.baseline_window?.start ?? '2026-09-07T21:00:00Z'}</div>
                    <div>End: {outcome.baseline_window?.end ?? '2026-09-17T21:00:00Z'}</div>
                    <div>Duration: {outcome.baseline_window?.duration_days ?? 10} days</div>
                  </div>
                </div>

                <div className="border border-indigo-200 rounded-lg p-4 bg-indigo-50/40">
                  <div className="flex items-center gap-2 text-xs font-semibold text-indigo-900 mb-2">
                    <Calendar className="w-4 h-4 text-indigo-600" />
                    Measurement Window (Post-Action Simulation)
                  </div>
                  <div className="text-xs text-indigo-800 space-y-1 font-mono">
                    <div>Start: {outcome.measurement_window?.start ?? '2026-09-17T21:00:00Z'}</div>
                    <div>End: {outcome.measurement_window?.end ?? '2026-09-24T21:00:00Z'}</div>
                    <div>Duration: {outcome.measurement_window?.duration_days ?? 7} days</div>
                  </div>
                </div>

                <div className="md:col-span-2 border border-slate-200 rounded-lg p-3 bg-white text-xs text-slate-500 font-mono flex items-center justify-between">
                  <span>Measured At: {outcome.measured_at}</span>
                  <span className="font-semibold text-indigo-700">Mode: {outcome.measurement_mode}</span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
