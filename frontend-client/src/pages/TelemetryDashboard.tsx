import React, { useEffect, useState } from 'react';
import { 
  LineChart, 
  RotateCw, 
  Settings, 
  Sliders, 
  Activity,
  Terminal,
  Database
} from 'lucide-react';
import { useTelemetryStore } from '../state/telemetryStore';
import { TelemetryMetrics } from '../components/TelemetryMetrics';
import { RecoveryPanel } from '../components/RecoveryPanel';
import { usePolling } from '../hooks/usePolling';
import { useToastStore } from '../state/toastStore';

export const TelemetryDashboard: React.FC = () => {
  const { report, loading, error, fetchTelemetry } = useTelemetryStore();
  const [autoPoll, setAutoPoll] = useState(true);

  useEffect(() => {
    fetchTelemetry();
  }, [fetchTelemetry]);

  usePolling(async () => {
    if (!autoPoll) return true; 
    await fetchTelemetry();
    return false; 
  }, autoPoll ? 5000 : null);

  const handleRefresh = async () => {
    try {
      await fetchTelemetry();
      useToastStore.getState().addToast('success', 'Telemetry data refreshed.');
    } catch (err: any) {
      useToastStore.getState().addToast('error', 'Failed to refresh telemetry.');
    }
  };

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="flex flex-col md:flex-row md:justify-between md:items-center border-b border-zinc-900/60 pb-4 gap-4">
        <div>
          <h1 className="text-2xl font-extrabold font-display text-zinc-100 tracking-tight flex items-center gap-2">
            <LineChart className="text-cyan-400 w-6 h-6 stroke-[2]" />
            System Telemetry & Metrics
          </h1>
          <p className="text-xs text-zinc-500 mt-1">
            LIVE OPERATIONAL TELEMETRY FEED, CRYPTOGRAPHIC VALIDATIONS, AND DISTRIBUTED WORKER LOOPS
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <label className="flex items-center space-x-2 text-zinc-500 font-mono text-[10px] cursor-pointer select-none">
            <input
              type="checkbox"
              checked={autoPoll}
              onChange={(e) => setAutoPoll(e.target.checked)}
              className="accent-cyan-500 cursor-pointer rounded bg-zinc-950 border-zinc-800"
            />
            <span>Auto Refresh (5s)</span>
          </label>
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="border border-zinc-800 bg-zinc-900/60 hover:bg-zinc-800 text-zinc-300 rounded-lg px-3.5 py-1.5 text-[11px] cursor-pointer transition-colors font-mono flex items-center gap-1.5"
          >
            <RotateCw size={12} className={loading ? 'animate-spin' : ''} />
            <span>{loading ? 'Polling...' : 'Poll Now'}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-rose-950/20 border border-rose-900/40 text-rose-455 p-4.5 rounded-xl font-mono text-xs animate-fade-in">
          <span className="font-bold">Error reading telemetry:</span> {error}
        </div>
      )}

      {/* Control Console */}
      <RecoveryPanel />

      {/* Primary Metrics Visualization */}
      <TelemetryMetrics report={report} loading={loading} />

      {/* Prometheus exposition format preview shortcut */}
      {report && (
        <div className="glass-card rounded-xl p-6 border-zinc-800/80 bg-zinc-950/40 font-mono text-xs space-y-4 shadow-sm">
          <div className="flex justify-between items-center border-b border-zinc-900 pb-2.5">
            <h4 className="font-display font-bold text-zinc-200 flex items-center gap-1.5">
              <Terminal size={14} className="text-cyan-400" />
              Prometheus Exposition Feed Preview
            </h4>
            <a
              href="http://localhost:8000/metrics"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[10px] text-cyan-400 hover:text-cyan-300 transition-colors underline underline-offset-2"
            >
              Open Feed Raw (/metrics)
            </a>
          </div>
          <p className="text-zinc-500 text-[10.5px] leading-relaxed font-sans font-medium">
            FastAPI exposes standard telemetry in Prometheus text exposition format. The monitoring agent scrapes this endpoint to build Grafana alert thresholds.
          </p>
          <div className="bg-[#050507] border border-zinc-900 rounded-xl p-4 text-[10px] text-zinc-550 max-h-40 overflow-y-auto scrollbar-thin select-all font-mono space-y-0.5">
            <div># HELP bbps_requests_total Total requests processed by the BBPS gateway</div>
            <div className="text-zinc-650"># TYPE bbps_requests_total counter</div>
            <div className="text-cyan-400/90">bbps_requests_total {report.total_requests}</div>
            
            <div className="mt-2.5"># HELP bbps_hmac_failures_total Total HMAC validation failures detected</div>
            <div className="text-zinc-650"># TYPE bbps_hmac_failures_total counter</div>
            <div className="text-cyan-400/90">bbps_hmac_failures_total {report.hmac_failures}</div>
            
            <div className="mt-2.5"># HELP bbps_average_latency_milliseconds Average request latency in milliseconds</div>
            <div className="text-zinc-650"># TYPE bbps_average_latency_milliseconds gauge</div>
            <div className="text-cyan-400/90">bbps_average_latency_milliseconds {report.average_latency_ms.toFixed(3)}</div>
            
            <div className="mt-2.5"># HELP bbps_circuit_breaker_state Current status of the circuit breaker</div>
            <div className="text-zinc-650"># TYPE bbps_circuit_breaker_state gauge</div>
            <div className="text-cyan-400/90">bbps_circuit_breaker_state {report.metrics?.find(m => m.name === 'circuit_breaker_state')?.value === 'CLOSED' ? 0 : 1}</div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TelemetryDashboard;
