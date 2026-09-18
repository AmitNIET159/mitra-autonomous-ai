'use client';

import React from 'react';
import { MerchantMetrics, MerchantProfile, PaytmProduct } from '@/types';
import { ArrowDownRight, Volume2, QrCode, CreditCard } from 'lucide-react';

interface BusinessHealthCardProps {
  merchant: MerchantProfile;
  metrics: MerchantMetrics;
}

export const BusinessHealthCard: React.FC<BusinessHealthCardProps> = ({ merchant, metrics }) => {
  const defaultDevices = merchant.paytm_products || [
    { name: 'Paytm Soundbox 4.0', status: 'ONLINE', battery_pct: 89 },
    { name: 'Paytm All-In-One QR', status: 'ACTIVE', placement: 'Front Counter' },
    { name: 'Paytm Card Machine', status: 'STANDBY' },
  ];

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">Business Health</h2>
            <span className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-mono font-semibold">
              SIMULATED TELEMETRY
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">Aggregated digital-twin metrics for {merchant.name}</p>
        </div>
        <span className="text-[11px] bg-blue-50 text-blue-700 font-semibold px-2 py-0.5 rounded border border-blue-200">
          Live Seeded Data
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
        {/* Total GMV Revenue */}
        <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-lg">
          <div className="text-xs text-slate-500 font-medium">Total Window GMV</div>
          <div className="text-lg font-bold text-slate-900 mt-1">
            ₹{(metrics.total_revenue_inr / 100000).toFixed(2)}L
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">₹{metrics.total_revenue_inr.toLocaleString('en-IN')}</div>
        </div>

        {/* Total Orders */}
        <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-lg">
          <div className="text-xs text-slate-500 font-medium">Total Orders</div>
          <div className="text-lg font-bold text-slate-900 mt-1">
            {metrics.total_orders.toLocaleString('en-IN')}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">14-day recorded window</div>
        </div>

        {/* Evening Orders */}
        <div className="p-3 bg-amber-50/50 border border-amber-200/80 rounded-lg">
          <div className="text-xs text-amber-800 font-medium">Evening Orders (Current)</div>
          <div className="text-lg font-bold text-amber-900 mt-1 flex items-baseline gap-1">
            <span>{metrics.evening_orders_current}</span>
            <span className="text-xs font-semibold text-rose-600 flex items-center">
              <ArrowDownRight className="w-3 h-3" /> {metrics.evening_orders_variance_pct}%
            </span>
          </div>
          <div className="text-[11px] text-amber-700 mt-0.5">Baseline: {metrics.evening_orders_baseline} orders</div>
        </div>

        {/* Repeat Conversion */}
        <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-lg">
          <div className="text-xs text-slate-500 font-medium">Repeat Conversion</div>
          <div className="text-lg font-bold text-slate-900 mt-1 flex items-baseline gap-1">
            <span>{(metrics.repeat_conversion_current * 100).toFixed(1)}%</span>
            <span className="text-xs font-semibold text-rose-600 flex items-center">
              <ArrowDownRight className="w-3 h-3" /> -3.4%
            </span>
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">Prior: {(metrics.repeat_conversion_baseline * 100).toFixed(1)}%</div>
        </div>
      </div>

      {/* Connected Paytm Devices */}
      <div>
        <div className="text-xs font-semibold text-slate-700 mb-2">Connected Paytm Devices (Digital Twin Simulation)</div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {defaultDevices.map((prod: PaytmProduct, idx: number) => (
            <div
              key={idx}
              className="flex items-center justify-between p-2.5 bg-slate-50/70 border border-slate-200 rounded-lg text-xs"
            >
              <div className="flex items-center gap-2">
                {prod.name.includes('Soundbox') ? (
                  <Volume2 className="w-4 h-4 text-[#00BAF2]" />
                ) : prod.name.includes('QR') ? (
                  <QrCode className="w-4 h-4 text-[#002E6E]" />
                ) : (
                  <CreditCard className="w-4 h-4 text-slate-600" />
                )}
                <span className="font-medium text-slate-800">{prod.name}</span>
              </div>
              <span
                className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                  prod.status === 'ONLINE' || prod.status === 'ACTIVE'
                    ? 'bg-emerald-100 text-emerald-700'
                    : 'bg-slate-200 text-slate-700'
                }`}
              >
                {prod.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
