import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  Terminal, 
  Copy, 
  Download, 
  RefreshCcw, 
  Sliders, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle,
  History,
  Lock,
  Workflow,
  Cpu,
  Layers,
  Database,
  Search
} from 'lucide-react';
import { calculateHmacSha256, canonicalize, generateNonce } from '../utils/crypto';
import apiClient from '../api/apiClient';
import axios from 'axios';

const PROBE_URL = '/demo/hmac-probe';

export const PlatformDemo: React.FC = () => {
  // CLIENT STATE
  const [clientDraftTraceId, setClientDraftTraceId] = useState('TXN-175137');
  const [clientDraftAmount, setClientDraftAmount] = useState('2500.00');
  const [clientPackage, setClientPackage] = useState<any>(null);

  // ADMIN STATE
  const [pastedJson, setPastedJson] = useState('');
  const [adminVerificationCopy, setAdminVerificationCopy] = useState<any>(null);
  const [adminLoadError, setAdminLoadError] = useState('');

  const [backendResponse, setBackendResponse] = useState<any>(null);
  const [serverMsg, setServerMsg] = useState('');
  
  // AUDITOR STATE
  const [auditLogs, setAuditLogs] = useState<any[]>([]);

  // TELEMETRY STATE
  const [replayMetrics, setReplayMetrics] = useState<any>(null);
  const [chaosStatus, setChaosStatus] = useState<any>(null);
  const [idempotencyStats, setIdempotencyStats] = useState<any>(null);
  const [testSummary, setTestSummary] = useState<any>(null);
  const [telemetry, setTelemetry] = useState<any>(null);

  const fetchMetricsAndLogs = async () => {
    try {
      const [replay, chaos, idempotency, test, tel, logs] = await Promise.all([
        apiClient.get('/demo/security/replay-metrics'),
        apiClient.get('/demo/chaos/status'),
        apiClient.get('/demo/idempotency/stats'),
        apiClient.get('/demo/system/test-summary'),
        apiClient.get('/telemetry'),
        apiClient.get('/demo/hmac-probe/audit-logs')
      ]);
      setReplayMetrics(replay.data);
      setChaosStatus(chaos.data);
      setIdempotencyStats(idempotency.data);
      setTestSummary(test.data);
      setTelemetry(tel.data);
      setAuditLogs(logs.data);
    } catch (err) {
      console.error("Error fetching metrics", err);
    }
  };

  useEffect(() => {
    fetchMetricsAndLogs();
    const interval = setInterval(fetchMetricsAndLogs, 5000);
    return () => clearInterval(interval);
  }, []);

  // CLIENT ACTIONS
  const generateSecureRequest = async () => {
    const traceId = clientDraftTraceId.trim();
    const amountVal = parseFloat(clientDraftAmount);
    if (!traceId || isNaN(amountVal)) {
      setServerMsg("Invalid Client inputs. Trace ID and Amount are required.");
      return;
    }

    const payload = {
      trace_id: traceId,
      amount: amountVal
    };
    const canonicalStr = canonicalize(payload);
    const ts = Math.floor(Date.now() / 1000).toString();
    const nonce = generateNonce();
    
    const secret = import.meta.env.VITE_CLIENT_SECRET || '';
    const sigInput = canonicalStr + ts + nonce;
    const sig = await calculateHmacSha256(sigInput, secret);
    const upperSig = sig.toUpperCase();
    
    const pkg = {
      package_id: 'PKG-' + Math.floor(100000 + Math.random() * 900000),
      payload,
      headers: {
        'X-Signature': upperSig,
        'X-Timestamp': ts,
        'X-Nonce': nonce,
        'X-Source-Id': 'mbanking'
      },
      created_at: new Date().toISOString()
    };
    
    setClientPackage(pkg);
    setServerMsg(`Signed package ${pkg.package_id} generated successfully.`);
  };

  const copyRequestPackage = () => {
    if (!clientPackage) return;
    navigator.clipboard.writeText(JSON.stringify(clientPackage, null, 2));
    setServerMsg('Signed request package JSON copied to clipboard.');
  };

  const exportJson = () => {
    if (!clientPackage) return;
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(clientPackage, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `${clientPackage.package_id}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
    setServerMsg(`Package ${clientPackage.package_id}.json exported successfully.`);
  };

  const generateNewPackage = () => {
    setClientDraftTraceId('TXN-' + Math.floor(100000 + Math.random() * 900000));
    setClientDraftAmount('2500.00');
    setClientPackage(null);
    setServerMsg('Ready to configure and generate new secure package.');
  };

  // ADMIN ACTIONS
  const loadRequest = () => {
    try {
      const parsed = JSON.parse(pastedJson.trim());
      if (!parsed.payload || !parsed.payload.trace_id || parsed.payload.amount === undefined || !parsed.headers || !parsed.headers['X-Signature']) {
        throw new Error("Invalid request package format. Missing payload or cryptographic headers.");
      }
      
      setAdminVerificationCopy({
        trace_id: parsed.payload.trace_id,
        amount: parsed.payload.amount,
        payload: parsed.payload,
        headers: parsed.headers,
        package_id: parsed.package_id || 'PKG-EXTERNAL',
        original: JSON.parse(JSON.stringify(parsed)) 
      });
      setAdminLoadError('');
      setBackendResponse(null);
      setServerMsg(`Loaded request package ${parsed.package_id || ''} successfully.`);
    } catch (err: any) {
      setAdminLoadError(err.message);
      setAdminVerificationCopy(null);
      setServerMsg(`Failed to load request package: ${err.message}`);
    }
  };

  const tamperAmount = () => {
    if (!adminVerificationCopy) return;
    setAdminVerificationCopy((prev: any) => {
      const newAmount = prev.amount + 1.0;
      return {
        ...prev,
        amount: newAmount,
        payload: {
          ...prev.payload,
          amount: newAmount
        }
      };
    });
    setServerMsg("Admin Panel: Mutated payload amount.");
  };

  const tamperTraceId = () => {
    if (!adminVerificationCopy) return;
    setAdminVerificationCopy((prev: any) => {
      const newTraceId = prev.trace_id + '_TAMPERED';
      return {
        ...prev,
        trace_id: newTraceId,
        payload: {
          ...prev.payload,
          trace_id: newTraceId
        }
      };
    });
    setServerMsg("Admin Panel: Mutated payload trace ID.");
  };

  const tamperSignature = () => {
    if (!adminVerificationCopy) return;
    setAdminVerificationCopy((prev: any) => {
      const currentSig = prev.headers['X-Signature'];
      const corruptedSig = currentSig.slice(0, -1) + (currentSig.slice(-1) === 'F' ? '0' : 'F');
      return {
        ...prev,
        headers: {
          ...prev.headers,
          'X-Signature': corruptedSig
        }
      };
    });
    setServerMsg("Admin Panel: Corrupted cryptographic signature hash.");
  };

  const tamperTimestamp = () => {
    if (!adminVerificationCopy) return;
    setAdminVerificationCopy((prev: any) => {
      const skewedTimestamp = (Math.floor(Date.now() / 1000) - 600).toString(); 
      return {
        ...prev,
        headers: {
          ...prev.headers,
          'X-Timestamp': skewedTimestamp
        }
      };
    });
    setServerMsg("Admin Panel: Skewed clock timestamp (-10 minutes).");
  };

  const verifyRequest = async () => {
    if (!adminVerificationCopy) return;
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    
    try {
      const response = await axios.post(
        `${baseUrl}${PROBE_URL}`,
        adminVerificationCopy.payload,
        {
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Timestamp': adminVerificationCopy.headers['X-Timestamp'],
            'X-Nonce': adminVerificationCopy.headers['X-Nonce'],
            'X-Signature': adminVerificationCopy.headers['X-Signature'],
            'X-Source-Id': adminVerificationCopy.headers['X-Source-Id'],
          }
        }
      );
      setBackendResponse(response.data);
      fetchMetricsAndLogs();
    } catch (err: any) {
      const responseData = err.response?.data;
      setBackendResponse(responseData || { success: false, status: 'ERROR', message: err.message });
      fetchMetricsAndLogs();
    }
  };

  // AUDITOR LOG STATS
  const logStats = auditLogs.reduce((acc, log) => {
    if (log.status === 'VALID') acc.valid++;
    else if (log.status === 'TAMPERED') acc.tampered++;
    else if (log.status === 'REPLAY_ATTACK') acc.replay++;
    else if (log.status === 'EXPIRED_TIMESTAMP') acc.expired++;
    return acc;
  }, { valid: 0, tampered: 0, replay: 0, expired: 0 });

  // Diff checks
  const diffTraceId = adminVerificationCopy?.original && (adminVerificationCopy.trace_id !== adminVerificationCopy.original.payload.trace_id);
  const diffAmount = adminVerificationCopy?.original && (adminVerificationCopy.amount !== adminVerificationCopy.original.payload.amount);
  const diffSignature = adminVerificationCopy?.original && (adminVerificationCopy.headers['X-Signature'] !== adminVerificationCopy.original.headers['X-Signature']);
  const diffTimestamp = adminVerificationCopy?.original && (adminVerificationCopy.headers['X-Timestamp'] !== adminVerificationCopy.original.headers['X-Timestamp']);

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="flex flex-col md:flex-row md:justify-between md:items-center border-b border-zinc-900/60 pb-4 gap-4">
        <div>
          <h1 className="text-2xl font-extrabold font-display text-zinc-100 tracking-tight flex items-center gap-2">
            <ShieldCheck className="text-cyan-400 w-6 h-6 stroke-[2]" />
            Security Operations Center Console
          </h1>
          <p className="text-xs text-zinc-500 mt-1">
            MONITOR HMAC SIGNATURE VERIFICATIONS, BLOCK REPLAY ATTACKS, AND TRACE INTERNAL CRYPTOGRAPHIC ROUTING CHAINS
          </p>
        </div>
        {serverMsg && (
          <div className="flex items-center gap-2 font-mono text-[10px] text-cyan-400 bg-cyan-950/20 px-3.5 py-1.5 border border-cyan-900/30 rounded-lg shadow-sm">
            <span className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-pulse-cyan"></span>
            <span>ALERT: {serverMsg}</span>
          </div>
        )}
      </div>

      {/* API GATEWAY VISUALIZATION */}
      <div className="glass-card rounded-xl p-6 border-zinc-800/80 bg-zinc-950/40 relative overflow-hidden">
        <h2 className="text-sm font-display font-bold text-zinc-200 border-b border-zinc-900 pb-3 flex items-center gap-2">
          <Workflow size={14} className="text-cyan-400" />
          Gateway Routing Topology — Cryptographic Audit Checkpoints
        </h2>

        {/* Dynamic Topology Chart */}
        <div className="py-6 flex flex-col md:flex-row justify-between items-center relative gap-6 md:gap-4 max-w-4xl mx-auto">
          
          {/* Node 1: Client API */}
          <div className="flow-node flex flex-col items-center gap-2 relative z-10 w-24">
            <div className="w-12 h-12 rounded-xl bg-zinc-900 border border-zinc-800 flex items-center justify-center text-cyan-400 shadow-md">
              <Cpu size={20} className="stroke-[1.8]" />
            </div>
            <div className="text-center">
              <span className="text-[10px] font-bold text-zinc-300 block font-display">Client Initiator</span>
              <span className="text-[8px] text-zinc-550 font-mono">Signed Header</span>
            </div>
          </div>

          {/* Connection Vector 1 */}
          <div className="hidden md:block flex-1 h-0.5 bg-zinc-850 relative min-w-[32px]">
            <div className="absolute top-1/2 left-0 -translate-y-1/2 w-full h-[1px] bg-gradient-to-r from-cyan-500 to-emerald-500 overflow-hidden">
              <div className="h-full bg-white/40 w-1/3 rounded flow-active-line"></div>
            </div>
          </div>

          {/* Node 2: Security Middleware Layer */}
          <div className="flow-node flex flex-col items-center gap-2 relative z-10 w-24">
            <div className={`w-12 h-12 rounded-xl bg-zinc-900 border flex items-center justify-center text-cyan-400 shadow-md ${backendResponse?.status === 'TAMPERED' ? 'border-rose-800 text-rose-400' : 'border-zinc-800'}`}>
              <Lock size={20} className="stroke-[1.8]" />
            </div>
            <div className="text-center">
              <span className="text-[10px] font-bold text-zinc-300 block font-display">HMAC Sandbox</span>
              <span className="text-[8px] text-zinc-550 font-mono">Verify Signature</span>
            </div>
          </div>

          {/* Connection Vector 2 */}
          <div className="hidden md:block flex-1 h-0.5 bg-zinc-850 relative min-w-[32px]">
            <div className="absolute top-1/2 left-0 -translate-y-1/2 w-full h-[1px] bg-gradient-to-r from-emerald-500 to-amber-500"></div>
          </div>

          {/* Node 3: Gateway Middleware */}
          <div className="flow-node flex flex-col items-center gap-2 relative z-10 w-24">
            <div className={`w-12 h-12 rounded-xl bg-zinc-900 border flex items-center justify-center text-cyan-400 shadow-md ${backendResponse?.status === 'REPLAY_ATTACK' ? 'border-rose-800 text-rose-400' : 'border-zinc-800'}`}>
              <Layers size={20} className="stroke-[1.8]" />
            </div>
            <div className="text-center">
              <span className="text-[10px] font-bold text-zinc-300 block font-display">COU Router</span>
              <span className="text-[8px] text-zinc-550 font-mono">Nonce Cache</span>
            </div>
          </div>

          {/* Connection Vector 3 */}
          <div className="hidden md:block flex-1 h-0.5 bg-zinc-850 relative min-w-[32px]">
            <div className="absolute top-1/2 left-0 -translate-y-1/2 w-full h-[1px] bg-gradient-to-r from-amber-500 to-emerald-500"></div>
          </div>

          {/* Node 4: Downstream BBPS BOU Simulator */}
          <div className="flow-node flex flex-col items-center gap-2 relative z-10 w-24">
            <div className="w-12 h-12 rounded-xl bg-zinc-900 border border-zinc-800 flex items-center justify-center text-emerald-400 shadow-md">
              <Sliders size={20} className="stroke-[1.8]" />
            </div>
            <div className="text-center">
              <span className="text-[10px] font-bold text-zinc-300 block font-display">BOU Simulator</span>
              <span className="text-[8px] text-zinc-550 font-mono">Biller Response</span>
            </div>
          </div>

          {/* Connection Vector 4 */}
          <div className="hidden md:block flex-1 h-0.5 bg-zinc-850 relative min-w-[32px]">
            <div className="absolute top-1/2 left-0 -translate-y-1/2 w-full h-[1px] bg-gradient-to-r from-emerald-500 to-cyan-500"></div>
          </div>

          {/* Node 5: Database Commit Ledger */}
          <div className="flow-node flex flex-col items-center gap-2 relative z-10 w-24">
            <div className="w-12 h-12 rounded-xl bg-zinc-900 border border-zinc-800 flex items-center justify-center text-cyan-400 shadow-md">
              <Database size={20} className="stroke-[1.8]" />
            </div>
            <div className="text-center">
              <span className="text-[10px] font-bold text-zinc-300 block font-display">Ledger DB</span>
              <span className="text-[8px] text-zinc-550 font-mono">Commit Block</span>
            </div>
          </div>

        </div>

        {/* Animated paths logic preview */}
        <div className="border border-zinc-900/80 p-3 rounded-lg bg-[#07070a] font-mono text-[9px] text-zinc-550 text-center max-w-lg mx-auto">
          DASHED PATH INDICATORS TRACE ACTIVE SYSTEM HANDSHAKES RUNNING THROUGH MIDDLEWARE STAGE
        </div>
      </div>

      {/* WORKFLOW PANELS CONTAINER */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* 1. CLIENT PANEL */}
        <div className="lg:col-span-4 glass-card rounded-xl p-5 border-zinc-800/80 bg-zinc-950/40 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-5 pb-3 border-b border-zinc-900">
              <h2 className="text-xs font-display font-bold text-cyan-400 flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-cyan-400 animate-ping"></span>
                🔑 Signature Initiator Desk
              </h2>
              <span className="text-[8px] uppercase bg-cyan-950/40 text-cyan-400 border border-cyan-800/30 px-2 py-0.5 rounded font-mono">
                Role: Client
              </span>
            </div>

            <div className="space-y-4 mb-5">
              <div>
                <label className="block text-[10px] font-mono font-bold text-zinc-500 mb-1.5 uppercase tracking-wider">
                  Trace Ref ID
                </label>
                <input
                  type="text"
                  value={clientDraftTraceId}
                  onChange={(e) => setClientDraftTraceId(e.target.value)}
                  className="input-premium font-mono"
                />
              </div>
              <div>
                <label className="block text-[10px] font-mono font-bold text-zinc-550 mb-1.5 uppercase tracking-wider">
                  Amount (₹)
                </label>
                <input
                  type="text"
                  value={clientDraftAmount}
                  onChange={(e) => setClientDraftAmount(e.target.value)}
                  className="input-premium font-mono"
                />
              </div>
            </div>

            <div className="flex flex-col gap-2 mb-5">
              <button
                onClick={generateSecureRequest}
                className="w-full bg-cyan-600 hover:bg-cyan-500 text-black font-display font-black text-xs py-2.5 rounded-lg transition-all cursor-pointer shadow-md shadow-cyan-950/20 uppercase tracking-wider"
              >
                Generate Signed Package
              </button>
              {clientPackage && (
                <div className="grid grid-cols-3 gap-2">
                  <button
                    onClick={copyRequestPackage}
                    className="bg-zinc-900 hover:bg-zinc-850 border border-zinc-800 text-zinc-300 font-mono text-[9px] py-1.5 rounded-lg transition-colors cursor-pointer flex items-center justify-center gap-1"
                  >
                    <Copy size={10} />
                    Copy JSON
                  </button>
                  <button
                    onClick={exportJson}
                    className="bg-zinc-900 hover:bg-zinc-850 border border-zinc-800 text-zinc-300 font-mono text-[9px] py-1.5 rounded-lg transition-colors cursor-pointer flex items-center justify-center gap-1"
                  >
                    <Download size={10} />
                    Export
                  </button>
                  <button
                    onClick={generateNewPackage}
                    className="bg-zinc-900 hover:bg-zinc-850 border border-zinc-800 text-zinc-300 font-mono text-[9px] py-1.5 rounded-lg transition-colors cursor-pointer flex items-center justify-center gap-1"
                  >
                    <RefreshCcw size={10} />
                    Reset
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Signed Request Package Preview */}
          <div className="bg-[#050507] border border-zinc-900 rounded-xl p-4 min-h-[180px] font-mono text-[10px] flex flex-col justify-between">
            <span className="text-zinc-650 block mb-2 uppercase text-[8px] tracking-widest font-extrabold border-b border-zinc-900 pb-1">
              Signed Package JSON
            </span>
            <div className="flex-1 overflow-auto max-h-[140px]">
              {clientPackage ? (
                <pre className="text-cyan-400/90 whitespace-pre-wrap select-all font-mono">
                  {JSON.stringify(clientPackage, null, 2)}
                </pre>
              ) : (
                <p className="text-zinc-600 italic py-8 text-center font-sans text-xs">No signed package generated. Set trace & amount, then click submit.</p>
              )}
            </div>
          </div>
        </div>

        {/* 2. ADMIN VERIFICATION CONSOLE */}
        <div className="lg:col-span-8 glass-card rounded-xl p-5 border-zinc-800/80 bg-zinc-950/40 grid grid-cols-1 md:grid-cols-12 gap-5">
          
          {/* Package JSON Input Column */}
          <div className="md:col-span-4 border-r border-zinc-900/60 pr-0 md:pr-4.5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4 pb-2 border-b border-zinc-900">
                <h3 className="text-[10px] font-mono font-bold text-emerald-400 uppercase tracking-wider">
                  JSON Ingestion Node
                </h3>
              </div>
              
              <textarea
                value={pastedJson}
                onChange={(e) => setPastedJson(e.target.value)}
                placeholder="Paste signed request package JSON..."
                className="w-full bg-[#050507] border border-zinc-900 rounded-xl p-3.5 text-[10px] font-mono text-zinc-300 placeholder-zinc-700 focus:outline-none focus:border-emerald-500 h-[220px] resize-none"
              />
              {adminLoadError && (
                <p className="text-rose-450 text-[9px] mt-2 font-mono">{adminLoadError}</p>
              )}
            </div>

            <button
              onClick={loadRequest}
              className="w-full bg-emerald-700 hover:bg-emerald-600 text-white font-display font-extrabold text-xs py-2.5 rounded-lg transition-all border border-emerald-600 shadow-md mt-4 cursor-pointer"
            >
              Load & Decrypt Request
            </button>
          </div>

          {/* Verification Desk Right Column */}
          <div className="md:col-span-8 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4 pb-2 border-b border-zinc-900">
                <h3 className="text-xs font-display font-bold text-emerald-400 tracking-wider">
                  🛡️ Cryptographic Tampering Suite
                </h3>
                <span className="text-[8px] uppercase bg-emerald-950/40 text-emerald-400 border border-emerald-800/30 px-2 py-0.5 rounded font-mono">
                  Role: Verify Desk
                </span>
              </div>

              {!adminVerificationCopy ? (
                <div className="text-center py-20 text-zinc-650 italic font-sans text-xs flex flex-col items-center justify-center gap-2">
                  <Sliders size={24} />
                  <span>Pasted signed package to unlock tampering tools.</span>
                </div>
              ) : (
                <div className="space-y-4 animate-fadeIn font-mono">
                  <div className="flex justify-between items-center text-[9px] border-b border-zinc-900/60 pb-1.5">
                    <span className="text-zinc-550">VERIFICATION REF:</span>
                    <span className="text-emerald-400 font-bold">{adminVerificationCopy.package_id}</span>
                  </div>

                  {/* Form fields */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-[9px] text-zinc-500 uppercase font-bold mb-1">
                        Trace ID {diffTraceId && <span className="text-rose-400">(Tampered)</span>}
                      </label>
                      <input
                        type="text"
                        value={adminVerificationCopy.trace_id}
                        onChange={(e) => setAdminVerificationCopy({
                          ...adminVerificationCopy,
                          trace_id: e.target.value,
                          payload: { ...adminVerificationCopy.payload, trace_id: e.target.value }
                        })}
                        className={`w-full bg-[#050507] border rounded-lg px-3 py-2 text-xs text-white focus:outline-none ${
                          diffTraceId ? 'border-rose-500 text-rose-400 bg-rose-950/5' : 'border-zinc-900'
                        }`}
                      />
                    </div>
                    <div>
                      <label className="block text-[9px] text-zinc-500 uppercase font-bold mb-1">
                        Amount (₹) {diffAmount && <span className="text-rose-400">(Tampered)</span>}
                      </label>
                      <input
                        type="text"
                        value={adminVerificationCopy.amount}
                        onChange={(e) => setAdminVerificationCopy({
                          ...adminVerificationCopy,
                          amount: parseFloat(e.target.value) || 0,
                          payload: { ...adminVerificationCopy.payload, amount: parseFloat(e.target.value) || 0 }
                        })}
                        className={`w-full bg-[#050507] border rounded-lg px-3 py-2 text-xs text-white focus:outline-none ${
                          diffAmount ? 'border-rose-500 text-rose-400 bg-rose-950/5' : 'border-zinc-900'
                        }`}
                      />
                    </div>
                  </div>

                  <div className="space-y-2.5">
                    <div>
                      <label className="block text-[9px] text-zinc-500 uppercase font-bold mb-1">
                        Cryptographic Signature (HMAC) {diffSignature && <span className="text-rose-400">(Tampered)</span>}
                      </label>
                      <input
                        type="text"
                        value={adminVerificationCopy.headers['X-Signature']}
                        onChange={(e) => setAdminVerificationCopy({
                          ...adminVerificationCopy,
                          headers: { ...adminVerificationCopy.headers, 'X-Signature': e.target.value }
                        })}
                        className={`w-full bg-[#050507] border rounded-lg px-3 py-2 text-xs text-white focus:outline-none ${
                          diffSignature ? 'border-rose-500 text-rose-400 bg-rose-950/5' : 'border-zinc-900'
                        }`}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-[9px] text-zinc-500 uppercase font-bold mb-1">
                          Timestamp {diffTimestamp && <span className="text-rose-400">(Clock Skew)</span>}
                        </label>
                        <input
                          type="text"
                          value={adminVerificationCopy.headers['X-Timestamp']}
                          onChange={(e) => setAdminVerificationCopy({
                            ...adminVerificationCopy,
                            headers: { ...adminVerificationCopy.headers, 'X-Timestamp': e.target.value }
                          })}
                          className={`w-full bg-[#050507] border rounded-lg px-3 py-2 text-xs text-white focus:outline-none ${
                            diffTimestamp ? 'border-rose-500 text-rose-400 bg-rose-950/5' : 'border-zinc-900'
                          }`}
                        />
                      </div>
                      <div>
                        <label className="block text-[9px] text-zinc-500 uppercase font-bold mb-1">
                          Nonce Index
                        </label>
                        <input
                          type="text"
                          readOnly
                          value={adminVerificationCopy.headers['X-Nonce']}
                          className="w-full bg-[#050507] border border-zinc-900/60 rounded-lg px-3 py-2 text-xs text-zinc-550 focus:outline-none"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Tamper testing tools */}
                  <div className="p-3 bg-zinc-900/30 border border-zinc-900 rounded-xl space-y-2">
                    <span className="text-[9px] text-zinc-500 block font-bold uppercase tracking-wider">
                      ⚠️ In-flight packet mutations
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      <button
                        onClick={tamperAmount}
                        className="bg-rose-950/20 hover:bg-rose-950/40 text-rose-450 border border-rose-900/30 text-[9px] font-mono px-2 py-1 rounded"
                      >
                        Modify Amount (+1.00)
                      </button>
                      <button
                        onClick={tamperTraceId}
                        className="bg-rose-950/20 hover:bg-rose-950/40 text-rose-450 border border-rose-900/30 text-[9px] font-mono px-2 py-1 rounded"
                      >
                        Mutate Trace ID
                      </button>
                      <button
                        onClick={tamperSignature}
                        className="bg-rose-950/20 hover:bg-rose-950/40 text-rose-450 border border-rose-900/30 text-[9px] font-mono px-2 py-1 rounded"
                      >
                        Corrupt Signature
                      </button>
                      <button
                        onClick={tamperTimestamp}
                        className="bg-rose-950/20 hover:bg-rose-950/40 text-rose-450 border border-rose-900/30 text-[9px] font-mono px-2 py-1 rounded"
                      >
                        skew Timestamp
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Verification trigger node */}
            {adminVerificationCopy && (
              <div className="mt-5 flex flex-col sm:flex-row items-center gap-4 border-t border-zinc-900/60 pt-4">
                <button
                  onClick={verifyRequest}
                  className="w-full sm:w-auto bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-black font-display font-black text-xs px-6 py-3 rounded-lg border border-emerald-500 shadow-md cursor-pointer uppercase tracking-wider flex-shrink-0"
                >
                  Verify Packet Integrity
                </button>

                {backendResponse && (
                  <div className="flex-1 w-full bg-[#050507] border border-zinc-900 rounded-xl p-3 flex items-center justify-between font-mono text-[10px]">
                    <div className="flex items-center gap-2">
                      <span className="text-zinc-550">VERDICT:</span>
                      {backendResponse.status === 'VALID' && (
                        <span className="badge-premium badge-premium-emerald text-[9px] font-black">
                          <CheckCircle2 size={10} />
                          VALID
                        </span>
                      )}
                      {backendResponse.status === 'TAMPERED' && (
                        <span className="badge-premium badge-premium-rose text-[9px] font-black animate-pulse">
                          <XCircle size={10} />
                          TAMPERED
                        </span>
                      )}
                      {backendResponse.status === 'REPLAY_ATTACK' && (
                        <span className="badge-premium badge-premium-rose text-[9px] font-black animate-pulse">
                          <AlertTriangle size={10} />
                          REPLAY BLOCK
                        </span>
                      )}
                      {backendResponse.status === 'EXPIRED_TIMESTAMP' && (
                        <span className="badge-premium badge-premium-amber text-[9px] font-black">
                          <AlertTriangle size={10} />
                          EXPIRED SKEW
                        </span>
                      )}
                    </div>
                    <span className="text-zinc-400 italic text-[11px] truncate max-w-[200px]" title={backendResponse.message}>
                      {backendResponse.message}
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 3. AUDIT & COMPLIANCE PANEL */}
      <div className="glass-card rounded-xl p-6 border-zinc-800/80 bg-zinc-950/40">
        <div className="flex items-center justify-between mb-5 pb-3 border-b border-zinc-900">
          <h2 className="text-sm font-display font-bold text-amber-400 flex items-center gap-2">
            <History size={14} className="text-amber-500" />
            Immutable Audit Trail Ledger (X-Signature Logs)
          </h2>
          <span className="text-[8px] uppercase bg-amber-950/40 text-amber-400 border border-amber-800/30 px-2 py-0.5 rounded font-mono">
            Role: Compliance Auditor
          </span>
        </div>

        {/* Audit Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-5">
          <div className="bg-[#050507]/60 border border-zinc-900 rounded-xl p-4 text-center font-mono">
            <span className="text-zinc-550 text-[9px] uppercase block mb-1">TOTAL RUNS</span>
            <h3 className="text-xl font-bold text-cyan-400">{auditLogs.length}</h3>
          </div>
          <div className="bg-[#050507]/60 border border-zinc-900 rounded-xl p-4 text-center font-mono">
            <span className="text-zinc-550 text-[9px] uppercase block mb-1">VALID PACKETS</span>
            <h3 className="text-xl font-bold text-emerald-400">{logStats.valid}</h3>
          </div>
          <div className="bg-[#050507]/60 border border-zinc-900 rounded-xl p-4 text-center font-mono">
            <span className="text-zinc-550 text-[9px] uppercase block mb-1">TAMPERED BLOCKS</span>
            <h3 className="text-xl font-bold text-rose-400">{logStats.tampered}</h3>
          </div>
          <div className="bg-[#050507]/60 border border-zinc-900 rounded-xl p-4 text-center font-mono">
            <span className="text-zinc-550 text-[9px] uppercase block mb-1">REPLAY BLOCKS</span>
            <h3 className="text-xl font-bold text-amber-400">{logStats.replay}</h3>
          </div>
          <div className="bg-[#050507]/60 border border-zinc-900 rounded-xl p-4 text-center font-mono">
            <span className="text-zinc-550 text-[9px] uppercase block mb-1">CLOCK SKEWS</span>
            <h3 className="text-xl font-bold text-yellow-500">{logStats.expired}</h3>
          </div>
        </div>

        {/* Professional Table layout */}
        <div className="overflow-x-auto max-h-[300px] border border-zinc-900 rounded-lg">
          <table className="w-full text-left font-mono text-[11px] text-zinc-400 border-collapse">
            <thead>
              <tr className="bg-zinc-900/30 border-b border-zinc-900 text-zinc-500 uppercase text-[9px] tracking-wider select-none">
                <th className="px-4 py-3">Timestamp</th>
                <th className="px-4 py-3">Trace Ref</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">Nonce Hash</th>
                <th className="px-4 py-3">HMAC Hash</th>
                <th className="px-4 py-3">Verdict</th>
                <th className="px-4 py-3">Auditor Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-900/60">
              {auditLogs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-zinc-650 italic font-sans text-xs">
                    Audit trail ledger is clean. No gateway integrity checks recorded yet.
                  </td>
                </tr>
              ) : (
                [...auditLogs].reverse().map((log, index) => (
                  <tr key={index} className="hover:bg-zinc-900/10">
                    <td className="px-4 py-2.5 text-zinc-550 whitespace-nowrap">{log.timestamp}</td>
                    <td className="px-4 py-2.5 font-bold text-zinc-300 select-all">{log.trace_id}</td>
                    <td className="px-4 py-2.5 text-zinc-200">₹{log.amount.toFixed(2)}</td>
                    <td className="px-4 py-2.5 text-zinc-500" title={log.nonce}>
                      {log.nonce.slice(0, 8)}...
                    </td>
                    <td className="px-4 py-2.5 text-zinc-550" title={log.signature}>
                      {log.signature.slice(0, 10)}...
                    </td>
                    <td className="px-4 py-2.5 whitespace-nowrap">
                      {log.status === 'VALID' && (
                        <span className="badge-premium badge-premium-emerald text-[9px]">VALID</span>
                      )}
                      {log.status === 'TAMPERED' && (
                        <span className="badge-premium badge-premium-rose text-[9px]">TAMPERED</span>
                      )}
                      {log.status === 'REPLAY_ATTACK' && (
                        <span className="badge-premium badge-premium-rose text-[9px] animate-pulse">REPLAY</span>
                      )}
                      {log.status === 'EXPIRED_TIMESTAMP' && (
                        <span className="badge-premium badge-premium-amber text-[9px]">EXPIRED</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-[10px] text-zinc-400 truncate max-w-xs" title={log.message}>{log.message}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* REPLAY PREVENTION TELEMETRY */}
      <div className="glass-card rounded-xl p-6 border-zinc-800/80 bg-zinc-950/40">
        <h2 className="text-sm font-display font-bold text-zinc-200 border-b border-zinc-900 pb-3 mb-4 flex items-center gap-2">
          <ShieldCheck size={14} className="text-cyan-400" />
          Replay Prevention Engine Dashboard
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 text-center font-mono">
          <div className="bg-[#050507]/40 border border-zinc-900 rounded-xl p-5 shadow-sm">
            <p className="text-zinc-550 text-[10px] uppercase mb-2">BLOCKED DUPLICATE NONCES</p>
            <h3 className="text-3xl font-black text-rose-400">
              {replayMetrics?.rejected_duplicate_nonces || 0}
            </h3>
          </div>

          <div className="bg-[#050507]/40 border border-zinc-900 rounded-xl p-5 shadow-sm">
            <p className="text-zinc-550 text-[10px] uppercase mb-2">REGISTERED NONCES IN MEMORY</p>
            <h3 className="text-3xl font-black text-cyan-450">
              {replayMetrics?.registered_nonces_count || 0}
            </h3>
          </div>

          <div className="bg-[#050507]/40 border border-zinc-900 rounded-xl p-5 shadow-sm">
            <p className="text-zinc-550 text-[10px] uppercase mb-2">SLIDING TIME WINDOW</p>
            <h3 className="text-3xl font-black text-emerald-450">300 seconds</h3>
          </div>
        </div>
      </div>

      {/* TELEMETRY & SYSTEM HEALTH */}
      <div className="glass-card rounded-xl p-6 border-zinc-800/80 bg-zinc-950/40">
        <h2 className="text-sm font-display font-bold text-cyan-400 border-b border-zinc-900 pb-3 mb-4 flex items-center gap-2">
          <Cpu size={14} className="text-cyan-400" />
          Operations Telemetry & Automation States
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <div className="bg-[#050507]/50 rounded-xl border border-zinc-900/80 p-5 font-mono">
            <p className="text-zinc-550 text-[9px] uppercase mb-1.5 block">TOTAL REQUESTS</p>
            <h3 className="text-3xl font-bold text-emerald-400">{telemetry?.total_requests || 0}</h3>
            <div className="mt-4 h-1.5 bg-zinc-900 rounded-full overflow-hidden">
              <div className="h-full w-full bg-emerald-500"></div>
            </div>
          </div>

          <div className="bg-[#050507]/50 rounded-xl border border-zinc-900/80 p-5 font-mono">
            <p className="text-zinc-550 text-[9px] uppercase mb-1.5 block">FAILURE SIMULATION RATE</p>
            <h3 className="text-3xl font-bold text-rose-455">
              {chaosStatus?.simulated_failure_rate ? `${chaosStatus.simulated_failure_rate * 100}%` : 'OFF'}
            </h3>
            <div className="mt-4 h-1.5 bg-zinc-900 rounded-full overflow-hidden">
              <div className="h-full bg-rose-500 rounded-full" style={{ width: chaosStatus?.simulated_failure_rate ? `${chaosStatus.simulated_failure_rate * 100}%` : '0%' }}></div>
            </div>
          </div>

          <div className="bg-[#050507]/50 rounded-xl border border-zinc-900/80 p-5 font-mono">
            <p className="text-zinc-550 text-[9px] uppercase mb-1.5 block">ACTIVE IDEMPOTENCY LOCKS</p>
            <h3 className="text-3xl font-bold text-cyan-455">
              {idempotencyStats?.active_idempotency_locks || 0}
            </h3>
            <div className="mt-4 h-1.5 bg-zinc-900 rounded-full overflow-hidden">
              <div className="h-full w-[40%] bg-cyan-500 rounded-full"></div>
            </div>
          </div>

          <div className="bg-[#050507]/50 rounded-xl border border-zinc-900/80 p-5 font-mono">
            <p className="text-zinc-550 text-[9px] uppercase mb-1.5 block">TEST COMPLIANCE REPORT</p>
            <h3 className="text-3xl font-bold text-emerald-450">
              {testSummary?.passed_tests || 0}/{testSummary?.total_tests || 0}
            </h3>
            <div className="mt-4 h-1.5 bg-zinc-900 rounded-full overflow-hidden">
              <div className="h-full w-full bg-emerald-500 rounded-full"></div>
            </div>
          </div>
        </div>
      </div>

    </div>
  );
};

export default PlatformDemo;