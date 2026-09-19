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
    <div className="bg-white border border-slate-200/90 rounded-xl p-5 shadow-xs flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Business Health Telemetry</h2>
              <span className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full font-mono font-bold border border-slate-200">
                DIGITAL TWIN
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">Aggregated transactional metrics for {merchant.name}</p>
          </div>
          <span className="text-[11px] bg-sky-50 text-[#007EA7] font-bold px-2.5 py-1 rounded-full border border-sky-200">
            Live Seeded Data
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
          {/* Total GMV Revenue */}
          <div className="p-3.5 bg-slate-50/70 border border-slate-200/80 rounded-xl">
            <div className="text-[11px] text-slate-500 font-semibold uppercase tracking-wider">Window GMV</div>
            <div className="text-xl font-extrabold text-slate-900 mt-1">
              ₹{(metrics.total_revenue_inr / 100000).toFixed(2)}L
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5 font-mono">₹{metrics.total_revenue_inr.toLocaleString('en-IN')}</div>
          </div>

          {/* Total Orders */}
          <div className="p-3.5 bg-slate-50/70 border border-slate-200/80 rounded-xl">
            <div className="text-[11px] text-slate-500 font-semibold uppercase tracking-wider">Total Orders</div>
            <div className="text-xl font-extrabold text-slate-900 mt-1">
              {metrics.total_orders.toLocaleString('en-IN')}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">14-day window</div>
          </div>

          {/* Evening Orders */}
          <div className="p-3.5 bg-amber-50/40 border border-amber-200/70 rounded-xl">
            <div className="text-[11px] text-amber-900 font-semibold uppercase tracking-wider">Evening Orders</div>
            <div className="text-xl font-extrabold text-amber-950 mt-1 flex items-baseline gap-1.5">
              <span>{metrics.evening_orders_current}</span>
              <span className="text-xs font-bold text-rose-600 flex items-center font-mono">
                <ArrowDownRight className="w-3.5 h-3.5" /> {metrics.evening_orders_variance_pct}%
              </span>
            </div>
            <div className="text-[11px] text-amber-800/80 mt-0.5 font-medium">Baseline: {metrics.evening_orders_baseline} orders</div>
          </div>

          {/* Repeat Conversion */}
          <div className="p-3.5 bg-slate-50/70 border border-slate-200/80 rounded-xl">
            <div className="text-[11px] text-slate-500 font-semibold uppercase tracking-wider">Repeat Conv.</div>
            <div className="text-xl font-extrabold text-slate-900 mt-1 flex items-baseline gap-1.5">
              <span>{(metrics.repeat_conversion_current * 100).toFixed(1)}%</span>
              <span className="text-xs font-bold text-rose-600 flex items-center font-mono">
                <ArrowDownRight className="w-3.5 h-3.5" /> -3.4%
              </span>
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">Prior: {(metrics.repeat_conversion_baseline * 100).toFixed(1)}%</div>
          </div>
        </div>
      </div>

      {/* Connected Paytm Devices */}
      <div className="pt-3 border-t border-slate-100">
        <div className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2.5 flex items-center justify-between">
          <span>Connected Merchant Devices</span>
          <span className="text-[10px] text-slate-400 font-mono font-normal">Active Hardware Endpoints</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
          {defaultDevices.map((prod: PaytmProduct, idx: number) => (
            <div
              key={idx}
              className="flex items-center justify-between p-2.5 bg-slate-50/80 border border-slate-200/80 rounded-lg text-xs"
            >
              <div className="flex items-center gap-2">
                {prod.name.includes('Soundbox') ? (
                  <Volume2 className="w-4 h-4 text-[#00BAF2]" />
                ) : prod.name.includes('QR') ? (
                  <QrCode className="w-4 h-4 text-[#002E6E]" />
                ) : (
                  <CreditCard className="w-4 h-4 text-slate-600" />
                )}
                <span className="font-semibold text-slate-800">{prod.name}</span>
              </div>
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                  prod.status === 'ONLINE' || prod.status === 'ACTIVE'
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                    : 'bg-slate-100 text-slate-600 border-slate-200'
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
