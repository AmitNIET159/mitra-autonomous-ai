import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'MITRA — Autonomous AI Teammate for Paytm Merchants',
  description:
    'Paytm Build for India Hackathon (Track 3) — Autonomous AI Teammate: Detect → Investigate → Decide → Guard → Act → Learn.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full bg-slate-100 antialiased">
      <body className="min-h-full flex flex-col text-slate-900 font-sans">{children}</body>
    </html>
  );
}
