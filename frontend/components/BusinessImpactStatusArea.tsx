'use client';

import React from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  Calculator,
  CheckCircle2,
  DollarSign,
  Info,
  Loader2,
  Percent,
  TrendingUp,
} from 'lucide-react';
import { BusinessImpact, OutcomeResult } from '@/types';

interface BusinessImpactStatusAreaProps {
  outcome: OutcomeResult | null;
  businessImpact: BusinessImpact | null;
  onAnalyzeImpact: () => Promise<void>;
  isAnalyzing?: boolean;
}

export const BusinessImpactStatusArea: React.FC<BusinessImpactStatusAreaProps> = ({
  outcome,
  businessImpact,
  onAnalyzeImpact,
  isAnalyzing = false,
}) => {
  const isOutcomeMeasured = outcome?.outcome_status === 'MEASURED';

  const formatCurrency = (val: number | null | undefined): string => {
    if (val === null || val === undefined) return 'N/A';
    return `₹${val.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
  };

  const getClassificationBadge = () => {
    if (!businessImpact) {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-700 border border-gray-300">
          AWAITING ANALYSIS
        </span>
      );
    }
    switch (businessImpact.impact_classification) {
      case 'POSITIVE':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
            <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
            POSITIVE IMPACT
          </span>
        );
      case 'NEUTRAL':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-300">
            <Info className="w-3.5 h-3.5 mr-1" />
            NEUTRAL IMPACT
          </span>
        );
      case 'NEGATIVE':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-300">
            <AlertTriangle className="w-3.5 h-3.5 mr-1" />
            NEGATIVE IMPACT
          </span>
        );
      case 'INSUFFICIENT_DATA':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-300">
            <AlertTriangle className="w-3.5 h-3.5 mr-1" />
            INSUFFICIENT DATA
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden mb-6">
      {/* Header */}
      <div className="p-5 border-b border-slate-100 bg-slate-50/50 flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Calculator className="w-5 h-5 text-indigo-600" />
            <h3 className="text-base font-bold text-slate-900">
              Phase 10: ROI & Business Impact Analysis
            </h3>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800 border border-purple-200 uppercase tracking-wider">
              SIMULATED • DIGITAL TWIN
            </span>
            {getClassificationBadge()}
          </div>
          <p className="text-xs text-slate-500">
            Calculates deterministic return on investment and business impact strictly from the persisted digital-twin outcome.
          </p>
        </div>

        {/* Action Button */}
        <div>
          <button
            onClick={onAnalyzeImpact}
            disabled={!isOutcomeMeasured || isAnalyzing}
            className={`inline-flex items-center justify-center px-4 py-2 rounded-lg text-sm font-semibold transition-all shadow-sm ${
              !isOutcomeMeasured
                ? 'bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200'
                : isAnalyzing
                ? 'bg-indigo-400 text-white cursor-wait'
                : businessImpact
                ? 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-indigo-100'
                : 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-emerald-100 animate-pulse'
            }`}
          >
            {isAnalyzing ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Analyzing Business Impact...
              </>
            ) : businessImpact ? (
              <>
                <Activity className="w-4 h-4 mr-2" />
                Re-analyze Business Impact
              </>
            ) : (
              <>
                <TrendingUp className="w-4 h-4 mr-2" />
                Analyze Business Impact
              </>
            )}
          </button>
        </div>
      </div>

      {/* Content Area */}
      <div className="p-6">
        {!businessImpact ? (
          <div className="text-center py-10 px-4 bg-slate-50/50 rounded-lg border border-dashed border-slate-200">
            <Calculator className="w-10 h-10 text-slate-300 mx-auto mb-2" />
            <p className="text-sm font-semibold text-slate-700">
              {!isOutcomeMeasured
                ? 'Awaiting Outcome Measurement from Phase 9'
                : 'Outcome is Measured — Ready to Calculate Business Impact'}
            </p>
            <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
              {!isOutcomeMeasured
                ? 'Phase 10 strictly requires a verified simulated outcome before calculating ROI and efficiency metrics.'
                : 'Click "Analyze Business Impact" to deterministically calculate ROI, incremental revenue, and campaign efficiency.'}
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Primary KPI Grid (4 Cards) */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* 1. Simulated ROI */}
              <div className="p-4 rounded-xl bg-gradient-to-br from-indigo-50 to-indigo-100/50 border border-indigo-200/60 shadow-sm">
                <div className="flex items-center justify-between text-indigo-700 mb-1">
                  <span className="text-xs font-semibold uppercase tracking-wider">
                    Simulated ROI
                  </span>
                  <Percent className="w-4 h-4" />
                </div>
                <div className="text-2xl font-black text-indigo-900">
                  {businessImpact.roi_percentage !== null && businessImpact.roi_percentage !== undefined
                    ? `${businessImpact.roi_percentage > 0 ? '+' : ''}${businessImpact.roi_percentage}%`
                    : 'N/A'}
                </div>
                <p className="text-[11px] text-indigo-700/80 mt-1">
                  Projected impact within digital-twin scenario
                </p>
              </div>

              {/* 2. Incremental Revenue */}
              <div className="p-4 rounded-xl bg-gradient-to-br from-emerald-50 to-emerald-100/50 border border-emerald-200/60 shadow-sm">
                <div className="flex items-center justify-between text-emerald-700 mb-1">
                  <span className="text-xs font-semibold uppercase tracking-wider">
                    Incremental GMV
                  </span>
                  <ArrowUpRight className="w-4 h-4" />
                </div>
                <div className="text-2xl font-black text-emerald-900">
                  +{formatCurrency(businessImpact.incremental_revenue)}
                </div>
                <p className="text-[11px] text-emerald-700/80 mt-1">
                  Observed simulated change: {formatCurrency(businessImpact.baseline_revenue)} → {formatCurrency(businessImpact.post_action_revenue)}
                </p>
              </div>

              {/* 3. Campaign Cost */}
              <div className="p-4 rounded-xl bg-gradient-to-br from-slate-50 to-slate-100 border border-slate-200 shadow-sm">
                <div className="flex items-center justify-between text-slate-600 mb-1">
                  <span className="text-xs font-semibold uppercase tracking-wider">
                    Campaign Cost
                  </span>
                  <DollarSign className="w-4 h-4" />
                </div>
                <div className="text-2xl font-black text-slate-800">
                  {formatCurrency(businessImpact.campaign_cost)}
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  Clamped approved incentive value strictly enforced
                </p>
              </div>

              {/* 4. Evening Orders Impact (Primary Signal) */}
              <div className="p-4 rounded-xl bg-gradient-to-br from-amber-50 to-amber-100/50 border border-amber-200/60 shadow-sm">
                <div className="flex items-center justify-between text-amber-700 mb-1">
                  <span className="text-xs font-semibold uppercase tracking-wider">
                    Evening Orders Change
                  </span>
                  <TrendingUp className="w-4 h-4" />
                </div>
                <div className="text-2xl font-black text-amber-900">
                  +{businessImpact.evening_orders_change} orders
                </div>
                <p className="text-[11px] text-amber-700/80 mt-1">
                  Observed simulated change: {businessImpact.baseline_evening_orders} → {businessImpact.post_action_evening_orders}
                </p>
              </div>
            </div>

            {/* Secondary Efficiency & Governance Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
                  Cost / Incremental Order
                </div>
                <div className="text-lg font-bold text-slate-900">
                  {businessImpact.cost_per_incremental_order !== null && businessImpact.cost_per_incremental_order !== undefined
                    ? formatCurrency(businessImpact.cost_per_incremental_order)
                    : 'N/A in simulation'}
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  Campaign Cost ÷ {businessImpact.incremental_orders} incremental orders
                </p>
              </div>

              <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
                  Revenue / Campaign Rupee
                </div>
                <div className="text-lg font-bold text-slate-900">
                  {businessImpact.revenue_per_campaign_rupee !== null && businessImpact.revenue_per_campaign_rupee !== undefined
                    ? `₹${businessImpact.revenue_per_campaign_rupee} per ₹1`
                    : 'N/A in simulation'}
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  Incremental GMV ÷ Campaign Cost
                </p>
              </div>

              <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
                  Gross Profit Impact
                </div>
                <div className="text-lg font-bold text-slate-500 italic">
                  Not available in simulation
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  Zero COGS fabrication policy strictly enforced
                </p>
              </div>
            </div>

            {/* Non-Causal Prototype Notice */}
            <div className="p-4 rounded-lg bg-indigo-50/70 border border-indigo-100 flex items-start gap-3">
              <Info className="w-5 h-5 text-indigo-600 shrink-0 mt-0.5" />
              <div className="text-xs text-indigo-950 space-y-1">
                <div className="font-semibold text-indigo-900">
                  Digital-Twin Simulation & Non-Causal Framing Notice
                </div>
                <p className="text-indigo-800/90 leading-relaxed">
                  All business impact metrics and ROI calculations are derived strictly from the digital-twin simulation model. No live Paytm APIs were invoked, and zero real financial transactions or merchant campaign funds were utilized. Figures reflect observed simulated outcomes and are not causal claims of actual production merchant performance.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
