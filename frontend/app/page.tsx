'use client';

import React, { useEffect, useState } from 'react';
import {
  analyzeBusinessImpact,
  approveAutonomyAction,
  evaluateAutonomy,
  executeSimulation,
  fetchActionByInvestigation,
  fetchAutonomyByAction,
  fetchBusinessImpactByOutcome,
  fetchDecisionByAction,
  fetchExecutionByDecision,
  fetchExecutionsHistory,
  fetchGuardrailByAction,
  fetchInvestigationBySignal,
  fetchMerchant,
  fetchMerchantAutonomyPolicy,
  fetchMerchantMetrics,
  fetchOutcomeByExecution,
  fetchSignals,
  fetchSystemStatus,
  fetchWorkflowExplainability,
  measureOutcome,
  rejectAutonomyAction,
  triggerActionPlanning,
  triggerDecisionCreation,
  triggerGuardrailEvaluation,
  triggerInvestigation,
  triggerSignalDetection,
  fetchAIStatus,
} from '@/lib/api';
import {
  ActionProposal,
  AIProviderStatus,
  AutonomyEvaluation,
  BusinessImpact,
  BusinessSignal,
  Decision,
  DemoScenarioResult,
  ExecutionResult,
  ExplainabilitySummary,
  GuardrailEvaluation,
  InvestigationResult,
  MerchantAutonomyPolicy,
  MerchantMetrics,
  MerchantProfile,
  OutcomeResult,
  SystemStatus,
} from '@/types';
import { Header } from '@/components/Header';
import { SystemStatusBanner } from '@/components/SystemStatusBanner';
import { WorkflowRibbon } from '@/components/WorkflowRibbon';
import { BusinessHealthCard } from '@/components/BusinessHealthCard';
import { ActiveSignalCard } from '@/components/ActiveSignalCard';
import { MitraActivityArea } from '@/components/MitraActivityArea';
import { GuardrailStatusArea } from '@/components/GuardrailStatusArea';
import { DecisionStatusArea } from '@/components/DecisionStatusArea';
import { ExecutionStatusArea } from '@/components/ExecutionStatusArea';
import { OutcomeStatusArea } from '@/components/OutcomeStatusArea';
import { BusinessImpactStatusArea } from '@/components/BusinessImpactStatusArea';
import { AuditActivityArea } from '@/components/AuditActivityArea';
import { ExplainabilityPanel } from '@/components/ExplainabilityPanel';
import { AutonomyModeSelector } from '@/components/AutonomyModeSelector';
import { DemoScenarioController } from '@/components/DemoScenarioController';
import { AICopilotPanel } from '@/components/AICopilotPanel';


// Default initial state matching the seeded digital twin for instantaneous SSR
const initialMerchant: MerchantProfile = {
  id: 'MID-DEMO-98234',
  name: 'Sharma Kirana & General Store',
  category: 'Retail / Grocery',
  location: 'Delhi NCR',
  minimum_margin: 0.10,
  daily_budget: 12000.0,
  max_discount: 100.0,
  max_campaign_frequency: 3,
  autonomy_level: 'APPROVAL_REQUIRED',
  simulated: true,
  paytm_products: [
    { name: 'Paytm Soundbox 4.0', status: 'ONLINE', battery_pct: 89 },
    { name: 'Paytm All-In-One QR', status: 'ACTIVE', placement: 'Front Counter' },
    { name: 'Paytm Card Machine', status: 'STANDBY' },
  ],
};

const initialMetrics: MerchantMetrics = {
  merchant_id: 'MID-DEMO-98234',
  total_revenue_inr: 481849.82,
  total_orders: 1284,
  avg_basket_size_inr: 375.27,
  evening_orders_current: 291,
  evening_orders_baseline: 410,
  evening_orders_variance_pct: -29.02,
  repeat_conversion_current: 0.148,
  repeat_conversion_baseline: 0.182,
  target_campaign_customers: 486,
  simulated: true,
};

const initialSystemStatus: SystemStatus = {
  service: 'MITRA',
  version: '0.1.0',
  environment: 'development',
  simulation_mode: true,
  simulation_disclaimer:
    'PROTOTYPE SIMULATION NOTICE: All merchant metrics, transaction signals, and action outcomes are synthetic simulations in digital-twin sandbox.',
  llm_provider: 'Deterministic Fallback Client (Offline Safe)',
  llm_is_active: false,
  guardrails_enforced: true,
  merchant_profile: {
    merchant_id: 'MID-DEMO-98234',
    business_name: 'Sharma Kirana & General Store',
    category: 'Retail / Grocery',
    location: 'Delhi NCR',
  },
};

const initialSignal: BusinessSignal = {
  signal_id: 'SIG-EVN-DECLINE-01',
  merchant_id: 'MID-DEMO-98234',
  signal_type: 'EVENING_ORDER_DECLINE',
  severity: 'HIGH',
  metric_name: 'evening_orders',
  baseline_value: 410.0,
  observed_value: 291.0,
  change_percentage: -29.02,
  decline_percentage: 29.02,
  variance_percentage: -29.02,
  description: 'Evening orders (5:00 PM - 8:59 PM) fell from 410 baseline to 291 observed.',
  status: 'ACTIVE',
  detected_at: new Date().toISOString(),
  context_data: {
    detector: 'EveningOrderDeclineDetector',
    metric: 'evening_orders',
    hours: '17:00-20:59',
    baseline_orders: 410,
    observed_orders: 291,
    baseline_window: 'Sep 01 – Sep 10, 2026 (10 Days)',
    observed_window: 'Sep 11 – Sep 14, 2026 (Recent 4 Days)',
    decline_pct: 29.02,
  },
};

export default function DashboardPage() {
  const [systemStatus, setSystemStatus] = useState<SystemStatus>(initialSystemStatus);
  const [merchant, setMerchant] = useState<MerchantProfile>(initialMerchant);
  const [metrics, setMetrics] = useState<MerchantMetrics>(initialMetrics);
  const [activeSignal, setActiveSignal] = useState<BusinessSignal>(initialSignal);
  const [investigation, setInvestigation] = useState<InvestigationResult | null>(null);
  const [actionProposal, setActionProposal] = useState<ActionProposal | null>(null);
  const [guardrailEvaluation, setGuardrailEvaluation] = useState<GuardrailEvaluation | null>(null);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [execution, setExecution] = useState<ExecutionResult | null>(null);
  const [executionsHistory, setExecutionsHistory] = useState<ExecutionResult[]>([]);
  const [outcome, setOutcome] = useState<OutcomeResult | null>(null);
  const [businessImpact, setBusinessImpact] = useState<BusinessImpact | null>(null);
  const [autonomyPolicy, setAutonomyPolicy] = useState<MerchantAutonomyPolicy | null>(null);
  const [autonomyEvaluation, setAutonomyEvaluation] = useState<AutonomyEvaluation | null>(null);
  const [isDetecting, setIsDetecting] = useState<boolean>(false);
  const [isInvestigating, setIsInvestigating] = useState<boolean>(false);
  const [isPlanning, setIsPlanning] = useState<boolean>(false);
  const [isEvaluatingGuardrails, setIsEvaluatingGuardrails] = useState<boolean>(false);
  const [isCreatingDecision, setIsCreatingDecision] = useState<boolean>(false);
  const [isApproving, setIsApproving] = useState<boolean>(false);
  const [isRejecting, setIsRejecting] = useState<boolean>(false);
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [isMeasuringOutcome, setIsMeasuringOutcome] = useState<boolean>(false);
  const [isAnalyzingImpact, setIsAnalyzingImpact] = useState<boolean>(false);
  const [lastDetectedAt, setLastDetectedAt] = useState<string | undefined>(undefined);
  const [reloadTrigger, setReloadTrigger] = useState<number>(0);
  const [isExplainabilityOpen, setIsExplainabilityOpen] = useState<boolean>(false);
  const [explainabilitySummary, setExplainabilitySummary] = useState<ExplainabilitySummary | null>(null);
  const [isExplainabilityLoading, setIsExplainabilityLoading] = useState<boolean>(false);
  const [aiStatus, setAiStatus] = useState<AIProviderStatus | null>(null);

  useEffect(() => {
    let isSubscribed = true;

    async function loadData() {
      try {
        const [statusData, merchantData, metricsData, signalsData] = await Promise.all([
          fetchSystemStatus(),
          fetchMerchant(),
          fetchMerchantMetrics(),
          fetchSignals('MID-DEMO-98234'),
        ]);
        if (isSubscribed) {
          setSystemStatus(statusData);
          setMerchant(merchantData);
          setMetrics(metricsData);

          // Fetch AI provider status
          try {
            const ai = await fetchAIStatus();
            if (isSubscribed && ai) {
              setAiStatus(ai);
            }
          } catch (aiErr) {
            console.warn('Failed to load AI provider status:', aiErr);
          }

          // Fetch executions history
          try {
            const hist = await fetchExecutionsHistory('MID-DEMO-98234');
            if (isSubscribed && hist) {
              setExecutionsHistory(hist);
            }
          } catch (histErr) {
            console.warn('No executions history found:', histErr);
          }

          // Fetch merchant autonomy policy
          try {
            const pol = await fetchMerchantAutonomyPolicy('MID-DEMO-98234');
            if (isSubscribed && pol) {
              setAutonomyPolicy(pol);
            }
          } catch (polErr) {
            console.warn('Failed to load merchant autonomy policy:', polErr);
          }

          if (signalsData && signalsData.length > 0) {
            const primary =
              signalsData.find((s) => s.signal_type === 'EVENING_ORDER_DECLINE') || signalsData[0];
            setActiveSignal(primary);

            // Fetch any persisted investigation for this signal
            try {
              const existingInv = await fetchInvestigationBySignal(primary.signal_id);
              if (isSubscribed && existingInv) {
                setInvestigation(existingInv);

                // Fetch any persisted action proposal for this investigation
                try {
                  const existingAction = await fetchActionByInvestigation(existingInv.investigation_id);
                  if (isSubscribed && existingAction) {
                    setActionProposal(existingAction);

                    // Fetch any persisted autonomy evaluation
                    try {
                      const existingAut = await fetchAutonomyByAction(existingAction.action_id);
                      if (isSubscribed && existingAut) {
                        setAutonomyEvaluation(existingAut);
                      }
                    } catch (autErr) {
                      console.warn('No existing autonomy evaluation found:', autErr);
                    }

                    // Fetch any persisted guardrail evaluation for this action
                    try {
                      const existingGrd = await fetchGuardrailByAction(existingAction.action_id);
                      if (isSubscribed && existingGrd) {
                        setGuardrailEvaluation(existingGrd);

                        // Fetch any persisted decision for this action
                        try {
                          const existingDec = await fetchDecisionByAction(existingAction.action_id);
                          if (isSubscribed && existingDec) {
                            setDecision(existingDec);

                            // Fetch any persisted execution for this decision
                            try {
                              const existingExec = await fetchExecutionByDecision(existingDec.decision_id);
                              if (isSubscribed && existingExec) {
                                setExecution(existingExec);

                                // Fetch any persisted outcome for this execution
                                try {
                                  const existingOut = await fetchOutcomeByExecution(existingExec.execution_id);
                                  if (isSubscribed && existingOut) {
                                    setOutcome(existingOut);

                                    // Fetch any persisted business impact for this outcome
                                    try {
                                      const existingImpact = await fetchBusinessImpactByOutcome(existingOut.outcome_id);
                                      if (isSubscribed && existingImpact) {
                                        setBusinessImpact(existingImpact);
                                      }
                                    } catch (impactErr) {
                                      console.warn('No existing business impact found:', impactErr);
                                    }
                                  }
                                } catch (outErr) {
                                  console.warn('No existing outcome found:', outErr);
                                }
                              }
                            } catch (execErr) {
                              console.warn('No existing execution found:', execErr);
                            }
                          }
                        } catch (decErr) {
                          console.warn('No existing decision found:', decErr);
                        }
                      }
                    } catch (grdErr) {
                      console.warn('No existing guardrail evaluation found:', grdErr);
                    }
                  }
                } catch (actionErr) {
                  console.warn('No existing action proposal found:', actionErr);
                }
              }
            } catch (invErr) {
              console.warn('No existing investigation found:', invErr);
            }
          }
        }
      } catch (err) {
        console.error('Failed to update live dashboard data:', err);
      }
    }

    loadData();

    return () => {
      isSubscribed = false;
    };
  }, [reloadTrigger]);

  const handleRunDetection = async () => {
    setIsDetecting(true);
    try {
      const result = await triggerSignalDetection(merchant.id);
      if (result.signals_detected && result.signals_detected.length > 0) {
        const primary =
          result.signals_detected.find((s) => s.signal_type === 'EVENING_ORDER_DECLINE') ||
          result.signals_detected[0];
        setActiveSignal(primary);
      }
      const updatedMetrics = await fetchMerchantMetrics();
      setMetrics(updatedMetrics);
      const now = new Date();
      setLastDetectedAt(now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    } catch (err) {
      console.error('Signal detection failed:', err);
    } finally {
      setIsDetecting(false);
    }
  };

  const handleRunInvestigation = async () => {
    if (!activeSignal) return;
    setIsInvestigating(true);
    try {
      const result = await triggerInvestigation(activeSignal.signal_id);
      setInvestigation(result);
    } catch (err) {
      console.error('Investigation failed:', err);
    } finally {
      setIsInvestigating(false);
    }
  };

  const handleRunPlanning = async () => {
    if (!investigation) return;
    setIsPlanning(true);
    try {
      const proposal = await triggerActionPlanning(investigation.investigation_id);
      setActionProposal(proposal);
      setGuardrailEvaluation(null);
      setDecision(null);
    } catch (err) {
      console.error('Action planning failed:', err);
    } finally {
      setIsPlanning(false);
    }
  };

  const handleRunGuardrailEvaluation = async () => {
    if (!actionProposal) return;
    setIsEvaluatingGuardrails(true);
    try {
      const evaluation = await triggerGuardrailEvaluation(actionProposal.action_id);
      setGuardrailEvaluation(evaluation);
      setDecision(null);
      setAutonomyEvaluation(null);
    } catch (err) {
      console.error('Guardrail evaluation failed:', err);
    } finally {
      setIsEvaluatingGuardrails(false);
    }
  };

  const handleCreateDecision = async () => {
    if (!actionProposal || !guardrailEvaluation) return;
    setIsCreatingDecision(true);
    try {
      const dec = await triggerDecisionCreation(actionProposal.action_id, merchant.id);
      setDecision(dec);

      // Evaluate autonomy policy
      try {
        const aut = await evaluateAutonomy(actionProposal.action_id, merchant.id);
        setAutonomyEvaluation(aut);
        if (aut.auto_approval_allowed) {
          const refreshedDec = await fetchDecisionByAction(actionProposal.action_id);
          if (refreshedDec) {
            setDecision(refreshedDec);
          }
        }
      } catch (autErr) {
        console.warn('Autonomy evaluation failed:', autErr);
      }
    } catch (err) {
      console.error('Decision creation failed:', err);
    } finally {
      setIsCreatingDecision(false);
    }
  };

  const handleApproveDecision = async () => {
    if (!actionProposal) return;
    setIsApproving(true);
    try {
      const aut = await approveAutonomyAction(actionProposal.action_id, merchant.id, 'Sharma Kirana Store Owner');
      setAutonomyEvaluation(aut);
      const refreshedDec = await fetchDecisionByAction(actionProposal.action_id);
      if (refreshedDec) {
        setDecision(refreshedDec);
      }
    } catch (err) {
      console.error('Decision approval failed:', err);
    } finally {
      setIsApproving(false);
    }
  };

  const handleRejectDecision = async () => {
    if (!actionProposal) return;
    setIsRejecting(true);
    try {
      const aut = await rejectAutonomyAction(
        actionProposal.action_id,
        merchant.id,
        'Merchant rejected proposed action parameters',
        'Sharma Kirana Store Owner'
      );
      setAutonomyEvaluation(aut);
      const refreshedDec = await fetchDecisionByAction(actionProposal.action_id);
      if (refreshedDec) {
        setDecision(refreshedDec);
      }
    } catch (err) {
      console.error('Decision rejection failed:', err);
    } finally {
      setIsRejecting(false);
    }
  };

  const handleExecuteSimulation = async () => {
    if (!decision) return;
    setIsExecuting(true);
    try {
      const res = await executeSimulation(decision.decision_id, merchant.id);
      setExecution(res);
      setExecutionsHistory((prev) => [res, ...prev.filter((x) => x.execution_id !== res.execution_id)]);
      const updatedMetrics = await fetchMerchantMetrics();
      setMetrics(updatedMetrics);
    } catch (err: unknown) {
      console.error('Simulation execution failed:', err);
      alert(`Simulation execution failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsExecuting(false);
    }
  };

  const handleMeasureOutcome = async () => {
    if (!execution || execution.execution_state !== 'COMPLETED') return;
    setIsMeasuringOutcome(true);
    try {
      const res = await measureOutcome(execution.execution_id, merchant.id);
      setOutcome(res);
      setReloadTrigger((prev) => prev + 1);
    } catch (err: unknown) {
      console.error('Outcome measurement failed:', err);
      alert(`Outcome measurement failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsMeasuringOutcome(false);
    }
  };

  const handleAnalyzeImpact = async () => {
    if (!outcome || outcome.outcome_status !== 'MEASURED') return;
    setIsAnalyzingImpact(true);
    try {
      const res = await analyzeBusinessImpact(outcome.outcome_id, merchant.id);
      setBusinessImpact(res);
      setReloadTrigger((prev) => prev + 1);
    } catch (err: unknown) {
      console.error('Business impact analysis failed:', err);
      alert(`Business impact analysis failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsAnalyzingImpact(false);
    }
  };

  const handleResetComplete = () => {
    setInvestigation(null);
    setActionProposal(null);
    setGuardrailEvaluation(null);
    setDecision(null);
    setAutonomyEvaluation(null);
    setExecution(null);
    setOutcome(null);
    setBusinessImpact(null);
    setExecutionsHistory([]);
    setReloadTrigger((prev) => prev + 1);
  };

  const handleOpenExplainability = async () => {
    setIsExplainabilityOpen(true);
    setIsExplainabilityLoading(true);
    try {
      const sigId = activeSignal?.signal_id || 'SIG-EVN-DECLINE-01';
      const correlationId = `wf-${sigId.toLowerCase().replace('sig-', '')}`;
      const summary = await fetchWorkflowExplainability(correlationId);
      setExplainabilitySummary(summary);
    } catch (err) {
      console.warn('Failed to load workflow explainability:', err);
    } finally {
      setIsExplainabilityLoading(false);
    }
  };


  return (
    <div className="min-h-screen flex flex-col bg-slate-100">
      {/* 1. Header with Simulation Banner, Simulated MID, AI Provider, and Reset Button */}
      <Header
        merchant={merchant}
        simulationMode={systemStatus.simulation_mode}
        aiProvider={aiStatus?.active_provider}
        onResetComplete={handleResetComplete}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* 2. System Status & Safety Guarantees */}
        <SystemStatusBanner status={systemStatus} />

        {/* 2.2 Live Scenario Orchestrator for Hackathon Demonstration (Phase 13) */}
        <DemoScenarioController
          onScenarioExecuted={(res: DemoScenarioResult) => {
            console.log('Live scenario executed:', res.scenario);
            setReloadTrigger((prev) => prev + 1);
          }}
        />

        {/* 2.5 Controlled Autonomy Policy Mode Selector (Phase 12) */}
        <AutonomyModeSelector
          policy={autonomyPolicy}
          onPolicyChange={(updated) => setAutonomyPolicy(updated)}
          disabled={isApproving || isExecuting}
        />

        {/* 3. Autonomous Workflow Ribbon */}
        <WorkflowRibbon
          onOpenExplainability={handleOpenExplainability}
          activeStage={
            outcome?.outcome_status === 'MEASURED'
              ? 'LEARN'
              : execution?.execution_state === 'COMPLETED'
              ? 'ACT'
              : decision?.approval_status === 'APPROVED'
              ? 'ACT'
              : decision
              ? 'APPROVE'
              : guardrailEvaluation
              ? 'DECIDE'
              : actionProposal
              ? 'GUARD'
              : investigation
              ? 'PLAN'
              : 'DETECT'
          }
        />

        {/* 4. Top Grid: Real Seeded Business Health + Active Signal */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <BusinessHealthCard merchant={merchant} metrics={metrics} />
          <ActiveSignalCard
            signal={activeSignal}
            metrics={metrics}
            investigation={investigation}
            actionProposal={actionProposal}
            guardrailEvaluation={guardrailEvaluation}
            onRunDetection={handleRunDetection}
            onRunInvestigation={handleRunInvestigation}
            onRunPlanning={handleRunPlanning}
            isDetecting={isDetecting}
            isInvestigating={isInvestigating}
            isPlanning={isPlanning}
            lastDetectedAt={lastDetectedAt}
          />
        </div>

        {/* 5. Middle Grid: MITRA Activity Area + Guardrail Status */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <MitraActivityArea
            investigation={investigation}
            actionProposal={actionProposal}
            guardrailEvaluation={guardrailEvaluation}
            isInvestigating={isInvestigating}
            isPlanning={isPlanning}
            isEvaluatingGuardrails={isEvaluatingGuardrails}
          />
          <GuardrailStatusArea
            evaluation={guardrailEvaluation}
            proposal={actionProposal}
            isEvaluating={isEvaluatingGuardrails}
            onEvaluate={handleRunGuardrailEvaluation}
          />
        </div>

        {/* 6. Authoritative Decision & Merchant Sign-off Gateway */}
        <DecisionStatusArea
          decision={decision}
          proposal={actionProposal}
          guardrailEvaluation={guardrailEvaluation}
          autonomyEvaluation={autonomyEvaluation}
          isCreating={isCreatingDecision}
          isApproving={isApproving}
          isRejecting={isRejecting}
          onCreateDecision={handleCreateDecision}
          onApprove={handleApproveDecision}
          onReject={handleRejectDecision}
        />

        {/* 7. Safe Execution Simulator Gateway & History */}
        <ExecutionStatusArea
          decision={decision}
          execution={execution}
          executionsHistory={executionsHistory}
          isExecuting={isExecuting}
          onExecuteSimulation={handleExecuteSimulation}
        />

        {/* 8. Post-Execution Outcome Monitoring & Measurement */}
        <OutcomeStatusArea
          execution={execution}
          outcome={outcome}
          onMeasureOutcome={handleMeasureOutcome}
          isMeasuring={isMeasuringOutcome}
        />

        {/* 9. Post-Outcome Business Impact & ROI Analysis */}
        <BusinessImpactStatusArea
          outcome={outcome}
          businessImpact={businessImpact}
          onAnalyzeImpact={handleAnalyzeImpact}
          isAnalyzing={isAnalyzingImpact}
        />

        {/* 9.5 AI Copilot Assistant & Telemetry Grounded Q&A (Phase 13) */}
        <AICopilotPanel
          correlationId={
            activeSignal
              ? `wf-${activeSignal.signal_id.toLowerCase().replace('sig-', '')}`
              : 'wf-evn-decline-01'
          }
          actionId={actionProposal?.action_id}
        />

        {/* 10. Audit Trail Activity Area */}
        <AuditActivityArea
          correlationId={
            activeSignal
              ? `wf-${activeSignal.signal_id.toLowerCase().replace('sig-', '')}`
              : undefined
          }
          onOpenExplainability={handleOpenExplainability}
          reloadTrigger={reloadTrigger}
        />

        {/* 11. Workflow Explainability Modal / Drawer */}
        <ExplainabilityPanel
          isOpen={isExplainabilityOpen}
          onClose={() => setIsExplainabilityOpen(false)}
          summary={explainabilitySummary}
          isLoading={isExplainabilityLoading}
          onRefresh={handleOpenExplainability}
        />

      </main>


      {/* Footer with simulation notice */}
      <footer className="border-t border-slate-200 bg-white py-6 mt-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-xs text-slate-500 space-y-2">
          <div className="font-semibold text-slate-700">
            MITRA — Autonomous AI Teammate for Paytm Merchants • Paytm Build for India AI Hackathon
          </div>
          <p className="max-w-2xl mx-auto text-[11px] text-slate-400">
            {systemStatus.simulation_disclaimer}
          </p>
          <div className="pt-2 text-[10px] text-slate-400">
            Built by Team <strong className="text-slate-600">Pica pica</strong> • Track 3: Autonomous AI Teammates
          </div>
        </div>
      </footer>
    </div>
  );
}
