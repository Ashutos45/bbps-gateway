import React from 'react';
import { ShieldCheck, Flame, RefreshCw, AlertTriangle } from 'lucide-react';
import { usePaymentStore } from '../state/paymentStore';
import { useTelemetryStore } from '../state/telemetryStore';

export const RecoveryPanel: React.FC = () => {
  const { simulateFailure, setSimulateFailure } = usePaymentStore();
  const { report, fetchTelemetry } = useTelemetryStore();

  const circuitBreakerState = report?.metrics?.find(m => m.name === 'circuit_breaker_state')?.value || 'CLOSED';
  const hmacFailures = report?.hmac_failures || 0;
  const replayAttacks = report?.replay_attacks || 0;
  const retryExecutions = report?.retry_executions || 0;
  const dlqTransitions = report?.dlq_transitions || 0;
  const unresolvedAmbiguities = report?.unresolved_ambiguity_counts || 0;

  const handleRefreshTelemetry = async () => {
    await fetchTelemetry();
  };

  const getCBStateColor = (state: string) => {
    switch (state.toUpperCase()) {
      case 'OPEN':
        return 'bg-rose-950/20 text-rose-400 border-rose-900/60 shadow-rose-950/10';
      case 'HALF-OPEN':
      case 'HALF_OPEN':
        return 'bg-amber-950/20 text-amber-400 border-amber-900/60 shadow-amber-950/10';
      default:
        return 'bg-emerald-950/20 text-emerald-400 border-emerald-900/60 shadow-emerald-950/10';
    }
  };

  return (
    <div className="glass-card rounded-xl p-6 space-y-6 font-mono text-xs border-zinc-800/80 bg-zinc-950/40">
      <div className="flex justify-between items-center border-b border-zinc-900 pb-3">
        <div>
          <h3 className="text-sm font-display font-bold text-zinc-200">Resilience Operations Console</h3>
          <p className="text-[10px] text-zinc-550 mt-0.5">CONFIGURE CHAOS VARIABLES & MONITOR BREAKER STATE MACHINE</p>
        </div>
        <button
          onClick={handleRefreshTelemetry}
          className="border border-zinc-850 bg-zinc-900/60 hover:bg-zinc-800 text-zinc-350 rounded-lg px-2.5 py-1.5 text-[11px] cursor-pointer transition-colors flex items-center gap-1"
        >
          <RefreshCw size={11} />
          <span>Refresh Stats</span>
        </button>
      </div>

      {/* Simulator Switch */}
      <div className="bg-[#050507]/40 border border-zinc-900 rounded-xl p-4.5 flex flex-col sm:flex-row justify-between sm:items-center gap-4">
        <div className="space-y-1">
          <span className="font-extrabold text-zinc-200 block text-[12px] font-display">Simulate Downstream Gateway Failures</span>
          <span className="text-[10.5px] text-zinc-500 block max-w-lg leading-relaxed font-sans font-medium">
            When active, forces the backend payment endpoint to fail with 504 Gateway Timeouts by injecting `X-Simulate-Failure: true` headers.
          </span>
        </div>
        <button
          onClick={() => setSimulateFailure(!simulateFailure)}
          className={`px-4.5 py-2.5 font-mono text-[11px] font-black rounded-lg cursor-pointer transition-all duration-205 border ${
            simulateFailure
              ? 'bg-rose-600 border-rose-500 hover:bg-rose-500 text-white shadow-lg shadow-rose-950/20'
              : 'bg-zinc-900 border-zinc-800 hover:bg-zinc-850 text-zinc-300'
          }`}
        >
          {simulateFailure ? 'CHAOS INJECTION ACTIVE' : 'ACTIVATE CHAOS'}
        </button>
      </div>

      {/* Status Grids */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-5">
        {/* Circuit Breaker Status */}
        <div className={`border p-4.5 rounded-xl flex flex-col justify-between h-28 transition-all ${getCBStateColor(circuitBreakerState)}`}>
          <div className="flex justify-between items-start">
            <span className="text-[9px] text-zinc-500 font-bold uppercase">CIRCUIT BREAKER</span>
            <Flame size={12} />
          </div>
          <div>
            <span className="block font-black text-lg leading-none font-display">{circuitBreakerState.toUpperCase()}</span>
            <span className="text-[9px] opacity-75 mt-1 block leading-normal font-sans">Protects backend from database lock saturation</span>
          </div>
        </div>

        {/* Unresolved Ambiguities */}
        <div className="border border-zinc-900 bg-zinc-900/10 p-4.5 rounded-xl flex flex-col justify-between h-28 text-zinc-300">
          <div className="flex justify-between items-start">
            <span className="text-[9px] text-zinc-500 font-bold uppercase">UNRESOLVED AMBIGUITIES</span>
            <span className="w-1.5 h-1.5 bg-amber-500 rounded-full animate-pulse"></span>
          </div>
          <div>
            <span className="block font-black text-lg leading-none font-display text-amber-400">{unresolvedAmbiguities}</span>
            <span className="text-[9px] text-zinc-550 mt-1 block font-sans">Awaiting automatic reconciliation sweep checks</span>
          </div>
        </div>

        {/* Retry / DLQ Isolations */}
        <div className="border border-zinc-900 bg-zinc-900/10 p-4.5 rounded-xl flex flex-col justify-between h-28 text-zinc-300">
          <div className="flex justify-between items-start">
            <span className="text-[9px] text-zinc-500 font-bold uppercase">ISOLATIONS & RETRIES</span>
            <ShieldCheck size={12} className="text-emerald-450" />
          </div>
          <div>
            <div className="flex items-baseline space-x-2">
              <span className="font-black text-lg leading-none font-display text-rose-455">{dlqTransitions}</span>
              <span className="text-zinc-550 text-[10px]">DLQ</span>
              <span className="font-black text-sm leading-none ml-2 font-display text-zinc-200">{retryExecutions}</span>
              <span className="text-zinc-550 text-[10px]">Retries</span>
            </div>
            <span className="text-[9px] text-zinc-550 mt-1.5 block font-sans">Isolated after threshold retry limits exceeded</span>
          </div>
        </div>
      </div>

      {/* Telemetry quick warning */}
      {(hmacFailures > 0 || replayAttacks > 0) && (
        <div className="border border-amber-900/30 bg-amber-950/10 text-amber-400 p-4 rounded-xl text-[10px] leading-relaxed flex items-start gap-2.5">
          <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-bold">Cryptographic Anomalies Intercepted:</span>
            <span className="block mt-0.5 opacity-90">
              HMAC Signature Validation Failures: {hmacFailures} | Replay Attack Attempts Blocked: {replayAttacks}. Security layer successfully locked down integrity boundaries.
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default RecoveryPanel;
