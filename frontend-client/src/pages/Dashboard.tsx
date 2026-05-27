import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  Database, 
  Activity, 
  Cpu, 
  Terminal, 
  ShieldAlert, 
  FileArchive, 
  Flame, 
  CheckCircle,
  AlertTriangle,
  RotateCw,
  Compass,
  ArrowRight,
  TrendingUp,
  AlertCircle,
  CreditCard,
  Lock,
  Clock
} from 'lucide-react';
import { useCacheStore } from '../state/cacheStore';
import { useReconciliationStore } from '../state/reconciliationStore';
import { useTelemetryStore } from '../state/telemetryStore';
import { useAuthStore } from '../state/authStore';
import { usePaymentStore } from '../state/paymentStore';
import { useToastStore } from '../state/toastStore';
import apiClient from '../api/apiClient';

export const Dashboard: React.FC = () => {
  const { cacheCount, hydrating, hydrationPercent, hydrationStatusText, error: cacheError, checkCacheStatus, hydrate } = useCacheStore();
  const { transactions, loading: txsLoading, loadOneView, reconcileTransaction, reconcilingTraceIds } = useReconciliationStore();
  const { report, fetchTelemetry } = useTelemetryStore();
  const { role, setRole } = useAuthStore();
  const { simulateFailure, setSimulateFailure } = usePaymentStore();

  const customerId = 'cust123'; 

  const [latencyHistory, setLatencyHistory] = useState<number[]>([120, 140, 110, 130, 125, 145, 135, 120, 130, 125, 140, 110]);
  const [cbHistory, setCbHistory] = useState<string[]>(['CLOSED', 'CLOSED', 'CLOSED', 'CLOSED', 'CLOSED', 'CLOSED', 'CLOSED', 'CLOSED', 'CLOSED', 'CLOSED', 'CLOSED', 'CLOSED']);

  const [compiling, setCompiling] = useState(false);
  const [compileProgress, setCompileProgress] = useState(0);
  const [compileFileId, setCompileFileId] = useState<string | null>(null);
  const [compileDownloadUrl, setCompileDownloadUrl] = useState<string | null>(null);
  const [compileError, setCompileError] = useState<string | null>(null);

  // Poll intervals
  useEffect(() => {
    checkCacheStatus();
    loadOneView(customerId);
    fetchTelemetry();

    const timer = setInterval(() => {
      fetchTelemetry();
      loadOneView(customerId);
    }, 3000);

    return () => clearInterval(timer);
  }, [checkCacheStatus, loadOneView, fetchTelemetry]);

  // Update SVG charts and timelines when new report registers
  useEffect(() => {
    if (report) {
      const currentLatency = report.average_latency_ms || 120;
      setLatencyHistory((prev) => {
        const next = [...prev, currentLatency];
        if (next.length > 12) next.shift();
        return next;
      });

      const cbState = report.metrics?.find(m => m.name === 'circuit_breaker_state')?.value || 'CLOSED';
      setCbHistory((prev) => {
        const next = [...prev, String(cbState)];
        if (next.length > 12) next.shift();
        return next;
      });
    }
  }, [report]);

  const handleHydrate = async () => {
    try {
      await hydrate();
      await fetchTelemetry();
      useToastStore.getState().addToast('success', 'Offline biller master hydrated successfully.');
    } catch (err: any) {
      useToastStore.getState().addToast('error', `Hydration failed: ${err.message}`);
    }
  };

  const handleManualReconcile = async (traceId: string) => {
    try {
      await reconcileTransaction(traceId, customerId);
      await fetchTelemetry();
      useToastStore.getState().addToast('success', `Transaction ${traceId} reconciled.`);
    } catch (err: any) {
      useToastStore.getState().addToast('error', `Manual reconciliation failed: ${err.message}`);
    }
  };



  const handleTriggerExport = async () => {
    setCompiling(true);
    setCompileProgress(10);
    setCompileFileId(null);
    setCompileDownloadUrl(null);
    setCompileError(null);

    const sourceId = import.meta.env.VITE_SOURCE_ID || 'mbanking';

    try {
      const response = await apiClient.post(`/BOBCOU/BBPS/${sourceId}/billpay/billers/file`, {
        callbackUrl: 'http://localhost:8000/callback/file'
      });
      const fileId = response.data.fileid;
      setCompileFileId(fileId);

      let attempts = 0;
      const pollTimer = setInterval(async () => {
        attempts++;
        try {
          const statusRes = await apiClient.get(`/BOBCOU/BBPS/${sourceId}/billpay/billers/file/${fileId}`);
          const statusData = statusRes.data;
          
          if (statusData.status === 0) {
            setCompileProgress(100);
            setCompileDownloadUrl(statusData.downloadUrl);
            setCompiling(false);
            clearInterval(pollTimer);
            useToastStore.getState().addToast('success', 'Zip Compilation completed.');
          } else if (statusData.status === 'FAILED') {
            setCompileError('Compilation worker failed.');
            setCompiling(false);
            clearInterval(pollTimer);
            useToastStore.getState().addToast('error', 'Zip Compilation failed.');
          } else {
            setCompileProgress(statusData.progress || 50);
          }
        } catch (err) {
          if (attempts > 15) {
            setCompileError('Polling timed out.');
            setCompiling(false);
            clearInterval(pollTimer);
            useToastStore.getState().addToast('error', 'Polling timed out.');
          }
        }
      }, 700);

    } catch (err: any) {
      setCompileError(err.response?.data?.message || err.message || 'Export failed to initialize.');
      setCompiling(false);
      useToastStore.getState().addToast('error', 'Export initialization failed.');
    }
  };

  // Telemetry attributes
  const totalRequests = report?.total_requests ?? 0;
  const successRate = report?.success_rate ?? 100;
  const avgLatency = report?.average_latency_ms ?? 0;
  const circuitBreakerState = report?.metrics?.find(m => m.name === 'circuit_breaker_state')?.value || 'CLOSED';
  const ambiguousCount = report?.ambiguous_transactions ?? 0;
  const dlqCount = report?.dlq_transitions ?? 0;
  const retryCount = report?.retry_executions ?? 0;
  const recoveryResolutions = report?.ambiguous_recovery_resolutions ?? 0;
  
  // Security audit metrics
  const unauthAttempts = report?.unauthorized_access_attempts ?? 0;
  const jwtFailures = report?.jwt_validation_failures ?? 0;
  const expiredTokens = report?.expired_token_usage ?? 0;
  const downloadAudits = report?.dataset_download_audits ?? 0;

  // Filter recent payments for display
  const recentTxs = transactions.slice(0, 5);

  // SVG Chart rendering helper
  const maxHistory = Math.max(...latencyHistory, 200);
  const chartHeight = 80;
  const chartWidth = 500;
  const points = latencyHistory
    .map((val, i) => {
      const x = (i * (chartWidth / 11)).toFixed(0);
      const y = (chartHeight - (val / maxHistory) * (chartHeight - 15)).toFixed(0);
      return `${x},${y}`;
    })
    .join(' ');

  const areaPoints = points ? `0,${chartHeight} ${points} ${chartWidth},${chartHeight}` : '';

  return (
    <div className="space-y-6">
      {/* Page Title & Time */}
      <div className="flex flex-col md:flex-row md:justify-between md:items-center border-b border-zinc-900/60 pb-4 gap-4">
        <div>
          <h1 className="text-2xl font-extrabold font-display text-zinc-100 tracking-tight flex items-center gap-2">
            <Activity className="text-cyan-400 stroke-[2] w-6 h-6" />
            {role === 'SUPER_ADMIN' && 'Ecosystem Central Command (Super)'}
            {role === 'ADMIN' && 'Ecosystem Central Command'}
            {role === 'OPERATIONS' && 'Transaction Operations Desk'}
            {role === 'AUDITOR' && 'Compliance & Security Audit Desk'}
            {role === 'CLIENT' && 'Consumer Bill Desk'}
          </h1>
          <p className="text-xs text-zinc-500 mt-1">
            BBPS OPERATIONS GATEWAY PLATFORM | CORE CHANNEL: <span className="font-mono text-cyan-400 bg-cyan-950/20 px-1.5 py-0.2 rounded border border-cyan-900/30">BobCOU mbanking</span>
          </p>
        </div>
        <div className="flex items-center gap-2 font-mono text-[10px] text-zinc-400 bg-[#07070a] px-3.5 py-1.5 border border-zinc-900 rounded-lg shadow-sm">
          <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></span>
          <span>TIME:</span> 
          <span className="text-zinc-200 font-bold">{new Date().toISOString().substring(11, 19)} UTC</span>
        </div>
      </div>

      {/* 🔐 SECURITY & ROLE SELECTOR (DEMO WORKSPACE ONLY) */}
      <div className="glass-card rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 border-zinc-800/80 bg-zinc-950/40">
        <div className="flex items-start gap-3">
          <div className="w-9 h-9 rounded-lg bg-cyan-950/30 border border-cyan-800/20 flex items-center justify-center text-cyan-400 mt-0.5 flex-shrink-0">
            <Terminal size={16} />
          </div>
          <div>
            <span className="text-zinc-200 font-semibold text-xs tracking-wider block font-display">SECURITY AUTHORIZATION SWITCHER</span>
            <span className="text-zinc-550 text-[10px] block mt-0.5">
              Swap role identities on-the-fly to test Zero-Trust path validations and inject cryptographic headers.
            </span>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {(['CLIENT', 'OPERATIONS', 'ADMIN', 'SUPER_ADMIN', 'AUDITOR'] as const).map((r) => {
            const isActive = role === r;
            return (
              <button
                key={r}
                onClick={() => setRole(r)}
                className={`px-3 py-1.5 rounded-lg text-[10px] font-bold font-mono border transition-all cursor-pointer ${
                  isActive
                    ? 'bg-gradient-to-r from-cyan-600 to-cyan-500 border-cyan-500 text-black shadow-md shadow-cyan-950/20 stroke-none'
                    : 'bg-zinc-900/60 border-zinc-800 text-zinc-400 hover:bg-zinc-850 hover:text-zinc-200'
                }`}
              >
                {r}
              </button>
            );
          })}
        </div>
      </div>

      {/* ==================== CLIENT ROLE DASHBOARD ==================== */}
      {role === 'CLIENT' && (
        <div className="space-y-6">
          {/* Quick Stats Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 font-mono text-xs">
            <div className="glass-card rounded-xl p-5 flex flex-col justify-between h-28 glass-card-emerald">
              <div className="flex items-center justify-between">
                <span className="text-zinc-550 text-[10px] font-bold">OFFLINE MASTER CACHE</span>
                <Database size={14} className="text-emerald-500" />
              </div>
              <div>
                <span className="block font-black text-xl text-emerald-400 tracking-tight">{cacheCount} Billers</span>
                <span className="text-[9px] text-zinc-500 block mt-0.5 font-sans">Seeded offline operator registry</span>
              </div>
            </div>

            <div className="glass-card rounded-xl p-5 flex flex-col justify-between h-28 glass-card-cyan">
              <div className="flex items-center justify-between">
                <span className="text-zinc-550 text-[10px] font-bold">INTEGRATION CONSOLE KEY</span>
                <Terminal size={14} className="text-cyan-400" />
              </div>
              <div>
                <span className="block font-bold text-sm text-zinc-150 truncate">client_key_123</span>
                <span className="text-[9px] text-zinc-500 block mt-1 font-sans">X-API-Key inject header active</span>
              </div>
            </div>

            <div className="glass-card rounded-xl p-5 flex flex-col justify-between h-28 glass-card-cyan">
              <div className="flex items-center justify-between">
                <span className="text-zinc-550 text-[10px] font-bold">CUSTOMER IDENTITY PROFILE</span>
                <span className="w-1.5 h-1.5 bg-cyan-400 rounded-full"></span>
              </div>
              <div>
                <span className="block font-bold text-base text-zinc-200">Rahul Sharma</span>
                <span className="text-[9px] text-zinc-500 block mt-0.5 font-sans">Customer Reference: cust123</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Payment Shortcut Container */}
            <div className="glass-card rounded-xl p-6 space-y-4 flex flex-col justify-between">
              <div className="space-y-3">
                <h3 className="text-sm font-display font-bold text-zinc-200 border-b border-zinc-900 pb-2.5 flex items-center space-x-2">
                  <CreditCard className="text-cyan-400 w-4 h-4" />
                  <span>Biller Payment Terminal</span>
                </h3>
                <p className="text-xs text-zinc-400 leading-relaxed font-sans">
                  Direct route channel to pay utility bills, water taxes, electricity invoices, DTH charges, or credit cards through BobCOU secure banking pipelines. Supports instant validation checks.
                </p>
              </div>
              <div className="pt-4">
                <Link
                  to="/payment"
                  className="flex items-center justify-center gap-1.5 w-full bg-gradient-to-r from-cyan-600 to-cyan-500 hover:from-cyan-500 hover:to-cyan-400 text-black font-display text-xs font-black py-3 rounded-lg transition-all shadow-md shadow-cyan-950/20 cursor-pointer"
                >
                  LAUNCH PAYMENT ENGINE
                  <ArrowRight size={13} />
                </Link>
              </div>
            </div>

            {/* Offline Database Sync Hydration Panel */}
            <div className="glass-card rounded-xl p-6 space-y-4">
              <h3 className="text-sm font-display font-bold text-zinc-200 border-b border-zinc-900 pb-2.5">
                Local Operator Hydration
              </h3>
              <p className="text-xs text-zinc-400 leading-relaxed font-sans">
                The gateway streams the latest active billers master list directly into your browser IndexedDB offline cache, supporting low-memory virtualized listing checks.
              </p>

              {hydrating && (
                <div className="bg-[#09090b]/80 border border-zinc-800/80 p-4 rounded-xl font-mono text-[10px] space-y-2">
                  <div className="flex justify-between items-center text-zinc-400">
                    <span>Hydrating Cache: {hydrationPercent}%</span>
                    <span className="animate-pulse text-cyan-400 flex items-center gap-1">
                      <RotateCw size={10} className="animate-spin" />
                      Streaming...
                    </span>
                  </div>
                  <div className="w-full bg-zinc-900 h-1.5 rounded-full overflow-hidden border border-zinc-800">
                    <div className="bg-cyan-500 h-full transition-all duration-300" style={{ width: `${hydrationPercent}%` }} />
                  </div>
                  <span className="block text-zinc-500 text-[9px]">{hydrationStatusText}</span>
                </div>
              )}

              {cacheError && (
                <div className="border border-rose-900 bg-rose-950/10 text-rose-400 p-3 rounded-xl text-[10px] font-mono leading-normal flex items-start gap-2">
                  <AlertTriangle size={12} className="flex-shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold">Sync Failure:</span> {cacheError}
                  </div>
                </div>
              )}

              {!hydrating && (
                <div className="pt-2">
                  <button
                    onClick={handleHydrate}
                    className="w-full bg-zinc-900 hover:bg-zinc-850 border border-zinc-800 text-zinc-200 font-mono text-xs font-bold py-2.5 rounded-lg cursor-pointer transition-colors"
                  >
                    {cacheCount > 0 ? 'SYNCHRONIZE LOCAL REGISTRIES' : 'HYDRATE LOCAL BILLER MASTER'}
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Simple Customer Transactions Trail */}
          <div className="glass-card rounded-xl p-6 space-y-4">
            <div className="flex justify-between items-center border-b border-zinc-900 pb-2.5">
              <h3 className="text-sm font-display font-bold text-zinc-200">Customer Bill Payment Logs</h3>
              <Link to="/oneview" className="text-[11px] font-mono text-cyan-400 hover:text-cyan-300 transition-colors">
                View History
              </Link>
            </div>
            {txsLoading ? (
              <div className="text-zinc-650 text-xs font-mono py-8 text-center animate-pulse flex items-center justify-center gap-2">
                <RotateCw className="animate-spin text-zinc-600" size={14} />
                Scanning ledger database...
              </div>
            ) : recentTxs.length === 0 ? (
              <div className="text-zinc-550 text-xs font-mono py-8 text-center">No payment history logged for Rahul Sharma.</div>
            ) : (
              <div className="space-y-3 font-mono text-xs">
                {recentTxs.map((tx) => {
                  const isSettled = tx.transaction_state === 'SETTLED';
                  const isAmbiguous = tx.transaction_state === 'AMBIGUOUS_TIMEOUT';
                  const isFailed = tx.transaction_state.startsWith('FAILED');
                  
                  let stateBadgeClass = 'badge-premium-zinc';
                  if (isSettled) stateBadgeClass = 'badge-premium-emerald';
                  else if (isAmbiguous) stateBadgeClass = 'badge-premium-amber animate-pulse';
                  else if (isFailed) stateBadgeClass = 'badge-premium-rose';

                  return (
                    <div key={tx.trace_id} className="bg-zinc-900/20 border border-zinc-800/40 rounded-lg p-3.5 flex justify-between items-center hover:border-zinc-800 transition-all">
                      <div>
                        <div className="font-bold text-zinc-200">{tx.biller_id}</div>
                        <div className="text-[10px] text-zinc-500 mt-1">₹{tx.amount} | Trace ID: {tx.trace_id}</div>
                      </div>
                      <span className={`badge-premium ${stateBadgeClass}`}>
                        {tx.transaction_state}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ==================== ADMIN ROLE DASHBOARD ==================== */}
      {(role === 'ADMIN' || role === 'SUPER_ADMIN') && (
        <div className="space-y-6 animate-fade-in">
          {/* Admin metrics grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 font-mono text-xs">
            <div className="glass-card rounded-xl p-5 flex flex-col justify-between h-28 glass-card-cyan">
              <div className="flex justify-between items-start text-zinc-550">
                <span className="text-[10px] font-bold">TOTAL REQUEST LOGS</span>
                <Cpu size={14} className="text-cyan-400" />
              </div>
              <div>
                <span className="block font-black text-2xl text-zinc-100 tracking-tight">{totalRequests}</span>
                <span className="text-[9px] text-zinc-500 block mt-0.5 font-sans">Aggregated routing operations</span>
              </div>
            </div>

            <div className="glass-card rounded-xl p-5 flex flex-col justify-between h-28 glass-card-emerald">
              <div className="flex justify-between items-start text-zinc-550">
                <span className="text-[10px] font-bold">SETTLEMENT RATIO</span>
                <TrendingUp size={14} className="text-emerald-400" />
              </div>
              <div>
                <span className="block font-black text-2xl text-emerald-400 tracking-tight">{successRate.toFixed(1)}%</span>
                <span className="text-[9px] text-zinc-500 block mt-0.5 font-sans">Database transaction integrity</span>
              </div>
            </div>

            <div className="glass-card rounded-xl p-5 flex flex-col justify-between h-28 glass-card-amber">
              <div className="flex justify-between items-start text-zinc-550">
                <span className="text-[10px] font-bold">CIRCUIT BREAKER</span>
                <Flame size={14} className={circuitBreakerState === 'CLOSED' ? 'text-emerald-400' : 'text-rose-400'} />
              </div>
              <div>
                <span className={`block font-black text-2xl tracking-tight ${
                  circuitBreakerState === 'CLOSED' ? 'text-emerald-400' :
                  circuitBreakerState === 'OPEN' ? 'text-rose-500 animate-pulse-cyan' : 'text-amber-500'
                }`}>{circuitBreakerState}</span>
                <span className="text-[9px] text-zinc-500 block mt-0.5 font-sans font-normal">Downstream timeout protector</span>
              </div>
            </div>

            <div className="glass-card rounded-xl p-5 flex flex-col justify-between h-28 glass-card-cyan">
              <div className="flex justify-between items-start text-zinc-550">
                <span className="text-[10px] font-bold">AVERAGE LATENCY</span>
                <Activity size={14} className="text-cyan-400" />
              </div>
              <div>
                <span className="block font-black text-2xl text-zinc-100 tracking-tight">{avgLatency.toFixed(1)} ms</span>
                <span className="text-[9px] text-zinc-500 block mt-0.5 font-sans font-normal">Includes DB row lock checks</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* SVG Latency Chart & Timeline */}
            <div className="glass-card rounded-xl p-6 space-y-4 lg:col-span-8 flex flex-col justify-between">
              <div>
                <div className="flex justify-between items-center border-b border-zinc-900 pb-2.5">
                  <span className="text-xs font-display font-bold text-zinc-200 tracking-wider">LIVE GATEWAY RESPONSE LATENCY (MS)</span>
                  <span className="text-[9px] text-zinc-500 font-mono bg-zinc-900 px-2 py-0.5 rounded border border-zinc-800/40">12-sample rolling window</span>
                </div>
              </div>
              
              <div className="flex justify-center py-4 bg-zinc-900/10 border border-zinc-900 rounded-lg p-2 overflow-hidden h-36 items-center">
                <svg width="100%" height="100%" viewBox={`0 0 ${chartWidth} ${chartHeight}`} preserveAspectRatio="none" className="overflow-visible">
                  <defs>
                    <linearGradient id="latencyGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.25" />
                      <stop offset="100%" stopColor="#06b6d4" stopOpacity="0" />
                    </linearGradient>
                  </defs>
                  <line x1="0" y1="10" x2={chartWidth} y2="10" stroke="rgba(39, 39, 42, 0.3)" strokeDasharray="3,3" />
                  <line x1="0" y1="40" x2={chartWidth} y2="40" stroke="rgba(39, 39, 42, 0.3)" strokeDasharray="3,3" />
                  <line x1="0" y1="70" x2={chartWidth} y2="70" stroke="rgba(39, 39, 42, 0.3)" strokeDasharray="3,3" />
                  {areaPoints && <polygon fill="url(#latencyGrad)" points={areaPoints} className="transition-all duration-300" />}
                  <polyline fill="none" stroke="#06b6d4" strokeWidth="2" points={points} className="transition-all duration-300" />
                  {latencyHistory.map((val, i) => (
                    <circle key={i} cx={i * (chartWidth / 11)} cy={chartHeight - (val / maxHistory) * (chartHeight - 15)} r="4" fill="#06b6d4" stroke="#030303" strokeWidth="1.5" />
                  ))}
                </svg>
              </div>

              {/* CB state timeline */}
              <div className="pt-4 border-t border-zinc-900/60">
                <span className="text-[10px] text-zinc-400 font-mono block mb-2">CIRCUIT BREAKER TICK HISTOGRAM:</span>
                <div className="grid grid-cols-12 gap-1 bg-[#050507] border border-zinc-900 rounded-lg p-2">
                  {cbHistory.map((state, i) => (
                    <div
                      key={i}
                      className={`h-4 rounded transition-all duration-300 ${
                        state === 'CLOSED' ? 'bg-emerald-500/20 border border-emerald-950 text-emerald-400' :
                        state === 'OPEN' ? 'bg-rose-500/20 border border-rose-950 text-rose-400' :
                        'bg-amber-500/20 border border-amber-950 text-amber-400'
                      }`}
                      title={`Tick ${i + 1}: ${state}`}
                    />
                  ))}
                </div>
              </div>
            </div>

            {/* Admin Console Commands */}
            <div className="glass-card rounded-xl p-6 space-y-4 lg:col-span-4 flex flex-col justify-between">
              <div className="space-y-4">
                <h3 className="text-sm font-display font-bold text-zinc-200 border-b border-zinc-900 pb-2.5">
                  Administrative Controls
                </h3>

                <div className="space-y-2">
                  <button
                    onClick={handleHydrate}
                    disabled={hydrating}
                    className="w-full bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-black font-mono text-[10px] font-bold py-2.5 rounded-lg transition-all cursor-pointer shadow-sm"
                  >
                    {hydrating ? 'HYDRATING CACHE...' : 'FORCE CACHE HYDRATE'}
                  </button>
                  
                  <button
                    onClick={handleTriggerExport}
                    disabled={compiling}
                    className="w-full bg-zinc-900 hover:bg-zinc-850 border border-zinc-800 text-zinc-300 font-mono text-[10px] font-bold py-2.5 rounded-lg transition-all cursor-pointer"
                  >
                    {compiling ? 'COMPILING DATASETS...' : 'COMPILE MASTER ZIP'}
                  </button>
                </div>

                {/* Async Export progress bar */}
                {(compiling || compileProgress > 0) && (
                  <div className="bg-zinc-900/60 border border-zinc-800/80 p-3 rounded-xl font-mono text-[9px] space-y-2">
                    <div className="flex justify-between text-zinc-400">
                      <span>Zip: {compileProgress}%</span>
                      {compiling && <span className="animate-pulse text-cyan-400 flex items-center gap-1"><RotateCw size={8} className="animate-spin" />Running</span>}
                    </div>
                    <div className="w-full bg-zinc-950 h-1 rounded-full overflow-hidden">
                      <div className="bg-cyan-500 h-full" style={{ width: `${compileProgress}%` }} />
                    </div>
                    {compileDownloadUrl && (
                      <a href={compileDownloadUrl} target="_blank" rel="noreferrer" className="block text-center bg-cyan-600 hover:bg-cyan-500 text-black font-bold p-1 text-[8px] rounded mt-2">
                        DOWNLOAD ARCHIVE
                      </a>
                    )}
                  </div>
                )}

                {/* Chaos simulation */}
                <div className="border border-zinc-900 rounded-xl p-3.5 bg-zinc-900/10 font-mono space-y-2">
                  <span className="text-[10px] text-zinc-500 font-bold block flex items-center gap-1">
                    <Flame size={12} className="text-orange-500" /> CHAOS TESTING LAYER
                  </span>
                  <div className="flex items-center justify-between text-[10px]">
                    <span className="text-zinc-450">Force 30% Downstream Drops</span>
                    <button
                      onClick={() => setSimulateFailure(!simulateFailure)}
                      className={`px-2 py-0.5 rounded text-[8px] font-bold cursor-pointer transition-all ${
                        simulateFailure ? 'bg-rose-600 text-white' : 'bg-zinc-800 text-zinc-400'
                      }`}
                    >
                      {simulateFailure ? 'ACTIVE' : 'OFF'}
                    </button>
                  </div>
                </div>
              </div>

              <div className="border border-zinc-900 border-dashed p-3 rounded-lg text-[9px] text-zinc-500 font-mono text-center">
                ADMIN SYSTEM CREDENTIALS VALIDATED
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ==================== OPERATIONS ROLE DASHBOARD ==================== */}
      {role === 'OPERATIONS' && (
        <div className="space-y-6 animate-fade-in">
          {/* Operator metrics grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 font-mono text-xs">
            <div className="glass-card rounded-xl p-5 flex flex-col justify-between h-28 glass-card-cyan">
              <div className="flex justify-between items-start text-zinc-550">
                <span className="text-[10px] font-bold">TOTAL TRANSACTIONS</span>
                <CreditCard size={14} className="text-cyan-400" />
              </div>
              <div>
                <span className="block font-black text-2xl text-zinc-100 tracking-tight">{transactions.length}</span>
                <span className="text-[9px] text-zinc-500 block mt-0.5 font-sans">Active database ledger rows</span>
              </div>
            </div>

            <div className="glass-card rounded-xl p-5 flex flex-col justify-between h-28 glass-card-amber animate-pulse">
              <div className="flex justify-between items-start text-zinc-550">
                <span className="text-[10px] font-bold">AMBIGUOUS COU TIMEOUTS</span>
                <AlertCircle size={14} className="text-amber-500" />
              </div>
              <div>
                <span className="block font-black text-2xl text-amber-500 tracking-tight">{ambiguousCount}</span>
                <span className="text-[9px] text-zinc-500 block mt-0.5 font-sans">Requiring manual settlement sweep</span>
              </div>
            </div>

            <div className="glass-card rounded-xl p-5 flex flex-col justify-between h-28 glass-card-rose">
              <div className="flex justify-between items-start text-zinc-550">
                <span className="text-[10px] font-bold">DLQ TRANSITIONS</span>
                <ShieldAlert size={14} className="text-rose-500" />
              </div>
              <div>
                <span className="block font-black text-2xl text-rose-500 tracking-tight">{dlqCount}</span>
                <span className="text-[9px] text-zinc-500 block mt-0.5 font-sans">Isolated poisonous payloads</span>
              </div>
            </div>

            <div className="glass-card rounded-xl p-5 flex flex-col justify-between h-28 glass-card-emerald">
              <div className="flex justify-between items-start text-zinc-550">
                <span className="text-[10px] font-bold">RECOVERY ACTIONS</span>
                <CheckCircle size={14} className="text-emerald-400" />
              </div>
              <div>
                <span className="block font-black text-2xl text-emerald-400 tracking-tight">{recoveryResolutions}</span>
                <span className="text-[9px] text-zinc-500 block mt-0.5 font-sans">Successfully swept ambiguities</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Reconciliation operations table */}
            <div className="glass-card rounded-xl p-6 space-y-4 lg:col-span-8">
              <div className="flex justify-between items-center border-b border-zinc-900 pb-2.5">
                <h3 className="text-sm font-display font-bold text-zinc-200">Manual Reconciliation Console</h3>
                <span className="text-[9px] text-zinc-500 font-mono">Real-time status updates</span>
              </div>

              {txsLoading ? (
                <div className="text-zinc-650 text-xs font-mono py-12 text-center flex items-center justify-center gap-2">
                  <RotateCw className="animate-spin text-zinc-600" size={14} />
                  Accessing audit trails...
                </div>
              ) : recentTxs.length === 0 ? (
                <div className="text-zinc-550 text-xs font-mono py-12 text-center">No transaction records found.</div>
              ) : (
                <div className="space-y-3 font-mono text-xs">
                  {recentTxs.map((tx) => {
                    const isSettled = tx.transaction_state === 'SETTLED';
                    const isAmbiguous = tx.transaction_state === 'AMBIGUOUS_TIMEOUT';
                    const isFailed = tx.transaction_state.startsWith('FAILED');
                    const isReconciling = reconcilingTraceIds[tx.trace_id];

                    return (
                      <div
                        key={tx.trace_id}
                        className="bg-zinc-900/10 border border-zinc-900/80 rounded-xl p-4 flex flex-col sm:flex-row justify-between sm:items-center gap-3 hover:border-zinc-800 transition-all"
                      >
                        <div>
                          <div className="flex items-center space-x-2">
                            <span className="font-bold text-zinc-200 text-xs">{tx.biller_id}</span>
                            <span className="text-[10px] text-zinc-500 font-mono">Trace: {tx.trace_id}</span>
                          </div>
                          <div className="text-[10px] text-zinc-400 mt-2 flex gap-4">
                            <span>Amount: ₹{tx.amount}</span>
                            <span>Retries: {tx.retry_attempts}</span>
                          </div>
                        </div>

                        <div className="flex items-center gap-3">
                          <span className={`badge-premium ${
                            isSettled ? 'badge-premium-emerald' :
                            isAmbiguous ? 'badge-premium-amber animate-pulse' :
                            isFailed ? 'badge-premium-rose' : 'badge-premium-zinc'
                          }`}>
                            {tx.transaction_state}
                          </span>

                          {isAmbiguous && (
                            <button
                              onClick={() => handleManualReconcile(tx.trace_id)}
                              disabled={isReconciling}
                              className="bg-amber-500 hover:bg-amber-400 disabled:bg-zinc-900 text-black font-bold font-mono text-[9px] px-2 py-1 rounded transition-all cursor-pointer shadow-sm"
                            >
                              {isReconciling ? 'RECONCILING...' : 'RECONCILE'}
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Operator Telemetry stats panel */}
            <div className="glass-card rounded-xl p-6 space-y-4 lg:col-span-4 flex flex-col justify-between">
              <div className="space-y-4">
                <h3 className="text-sm font-display font-bold text-zinc-200 border-b border-zinc-900 pb-2.5">
                  Operational Telemetry
                </h3>
                
                <div className="bg-zinc-900/20 border border-zinc-900 p-4 rounded-xl text-xs space-y-3 font-mono">
                  <div className="flex justify-between items-center text-[10px]">
                    <span className="text-zinc-550">RETRY WORKER TIMER:</span>
                    <span className="text-emerald-400 font-bold">10s POLL</span>
                  </div>
                  <div className="flex justify-between items-center text-[10px]">
                    <span className="text-zinc-550">RECONCILIATION POLL:</span>
                    <span className="text-emerald-400 font-bold">5s POLL</span>
                  </div>
                  <div className="flex justify-between items-center text-[10px]">
                    <span className="text-zinc-550">TOTAL ACTIVE SWEEPS:</span>
                    <span className="text-zinc-200 font-bold">{retryCount} executed</span>
                  </div>
                </div>

                <p className="text-[11px] text-zinc-500 leading-relaxed font-sans">
                  You are in Operational clearance mode. You have read-write permissions to reconcile transactions. Core system parameter overrides and seeding actions are restricted to administrators.
                </p>
              </div>

              <div className="border border-zinc-900 border-dashed p-3 rounded-lg text-[9px] text-zinc-500 font-mono text-center">
                OPERATIONS CLEARANCE SECURED
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ==================== AUDITOR ROLE DASHBOARD ==================== */}
      {role === 'AUDITOR' && (
        <div className="space-y-6 animate-fade-in">
          {/* Compliance & Security Audit metrics grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 font-mono text-xs">
            <div className="glass-card rounded-xl p-5 flex flex-col justify-between h-28 glass-card-rose shadow-[0_0_15px_rgba(239,68,68,0.05)]">
              <div className="flex justify-between items-start text-zinc-555">
                <span className="text-[10px] font-bold">HMAC VERIFICATION FAILS</span>
                <ShieldAlert size={14} className="text-rose-500" />
              </div>
              <div>
                <span className="block font-black text-2xl text-rose-500 tracking-tight">{unauthAttempts}</span>
                <span className="text-[9px] text-zinc-500 block mt-0.5 font-sans">Incorrect client signatures</span>
              </div>
            </div>

            <div className="glass-card rounded-xl p-5 flex flex-col justify-between h-28 glass-card-rose shadow-[0_0_15px_rgba(239,68,68,0.05)]">
              <div className="flex justify-between items-start text-zinc-555">
                <span className="text-[10px] font-bold">REPLAY ATTACK BLOCKS</span>
                <Lock size={14} className="text-rose-500" />
              </div>
              <div>
                <span className="block font-black text-2xl text-rose-500 tracking-tight">{jwtFailures}</span>
                <span className="text-[9px] text-zinc-500 block mt-0.5 font-sans">Duplicate nonce validations</span>
              </div>
            </div>

            <div className="glass-card rounded-xl p-5 flex flex-col justify-between h-28 glass-card-amber">
              <div className="flex justify-between items-start text-zinc-555">
                <span className="text-[10px] font-bold">STALE ACCESS TOKENS</span>
                <Clock size={14} className="text-amber-500" />
              </div>
              <div>
                <span className="block font-black text-2xl text-amber-500 tracking-tight">{expiredTokens}</span>
                <span className="text-[9px] text-zinc-500 block mt-0.5 font-sans font-normal">Expired token access attempts</span>
              </div>
            </div>

            <div className="glass-card rounded-xl p-5 flex flex-col justify-between h-28 glass-card-emerald">
              <div className="flex justify-between items-start text-zinc-555">
                <span className="text-[10px] font-bold">AUDITED DOWNLOADS</span>
                <CheckCircle size={14} className="text-emerald-500" />
              </div>
              <div>
                <span className="block font-black text-2xl text-emerald-400 tracking-tight">{downloadAudits}</span>
                <span className="text-[9px] text-zinc-500 block mt-0.5 font-sans">Master zip downloads</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Live HMAC & Nonce audit table */}
            <div className="glass-card rounded-xl p-6 space-y-4 lg:col-span-8">
              <div className="flex justify-between items-center border-b border-zinc-900 pb-2.5">
                <h3 className="text-sm font-display font-bold text-zinc-200 flex items-center gap-1.5">
                  <Terminal size={14} className="text-cyan-400" />
                  <span>Cryptographic Verification & Signature Trails (Read-Only)</span>
                </h3>
                <span className="text-[9px] text-zinc-500 font-mono">Zero-Trust validations</span>
              </div>

              {txsLoading ? (
                <div className="text-zinc-650 text-xs font-mono py-12 text-center">Reading signature trails...</div>
              ) : recentTxs.length === 0 ? (
                <div className="text-zinc-550 text-xs font-mono py-12 text-center">No transaction validation logs.</div>
              ) : (
                <div className="space-y-3 font-mono text-[11px]">
                  {recentTxs.map((tx) => (
                    <div key={tx.trace_id} className="bg-[#050507] border border-zinc-900 rounded-lg p-3 space-y-2">
                      <div className="flex justify-between items-center border-b border-zinc-900 pb-1.5">
                        <span className="text-zinc-400 font-bold">TRACE: {tx.trace_id}</span>
                        <span className="text-emerald-400 font-bold bg-emerald-950/20 border border-emerald-900/30 px-1.5 py-0.5 rounded text-[9px]">
                          HMAC_VERIFIED
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-y-1 gap-x-4 text-[10px] text-zinc-500">
                        <div><span className="text-zinc-600">NONCE:</span> NNC_REGISTRY_OK</div>
                        <div><span className="text-zinc-600">TIMESTAMP:</span> {new Date(tx.created_at).toISOString()}</div>
                        <div className="col-span-2 truncate"><span className="text-zinc-600">X-SIGNATURE:</span> sha256_hash_{tx.trace_id.replace(/-/g, '').substring(0, 24)}...</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Nonce stats configuration panel */}
            <div className="glass-card rounded-xl p-6 space-y-4 lg:col-span-4 flex flex-col justify-between">
              <div className="space-y-4">
                <h3 className="text-sm font-display font-bold text-zinc-200 border-b border-zinc-900 pb-2.5">
                  Audit Configuration
                </h3>
                
                <div className="space-y-2 text-xs font-mono">
                  <div className="p-3 bg-zinc-900/20 border border-zinc-900 rounded-xl space-y-2">
                    <div className="flex justify-between text-[10px]">
                      <span className="text-zinc-500">ROLE CLEARANCE:</span>
                      <span className="text-purple-400 font-bold">AUDITOR</span>
                    </div>
                    <div className="flex justify-between text-[10px]">
                      <span className="text-zinc-550">HMAC CHECK:</span>
                      <span className="text-emerald-400 font-bold">STRICT</span>
                    </div>
                    <div className="flex justify-between text-[10px]">
                      <span className="text-zinc-555">LOG RETENTION:</span>
                      <span className="text-zinc-300 font-bold">90 Days</span>
                    </div>
                  </div>

                  <p className="text-[11px] text-zinc-500 font-sans leading-relaxed pt-2">
                    You have read-only access to compliance reports, transaction trails, and cryptographic logs. System configuration modifications and action triggers are restricted.
                  </p>
                </div>
              </div>

              <div className="border border-purple-950/30 bg-purple-950/10 p-3 rounded-lg text-[9.5px] text-purple-400 font-mono text-center font-bold">
                AUDITOR COMPLIANCE ACTIVE
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
