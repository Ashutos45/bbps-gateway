import React from 'react';
import { RefreshCcw, Activity, ShieldAlert, CheckCircle, Database } from 'lucide-react';
import { TransactionLog } from '../types';

interface TransactionTrackerProps {
  transaction: TransactionLog | null;
  pollingActive: boolean;
  onRefresh: () => void;
}

export const TransactionTracker: React.FC<TransactionTrackerProps> = ({
  transaction,
  pollingActive,
  onRefresh,
}) => {
  if (!transaction) return null;

  const states = [
    { code: 'INITIALIZED', label: 'Initialized' },
    { code: 'PENDING_SUBMISSION', label: 'Pending Submission' },
    { code: 'NETWORK_IN_FLIGHT', label: 'Network In-Flight' },
    { code: 'AMBIGUOUS_TIMEOUT', label: 'Ambiguous Timeout' },
    { code: 'SETTLED', label: 'Settled', isTerminal: true, type: 'success' },
    { code: 'FAILED', label: 'Failed', isTerminal: true, type: 'error' },
    { code: 'FAILED_DLQ', label: 'Failed (DLQ)', isTerminal: true, type: 'error' }
  ];

  const getCurrentStateIndex = () => {
    const currentState = transaction.transaction_state;
    if (currentState === 'FAILED_DLQ') return 6;
    if (currentState === 'FAILED') return 5;
    if (currentState === 'SETTLED') return 4;
    if (currentState === 'AMBIGUOUS_TIMEOUT') return 3;
    if (currentState === 'NETWORK_IN_FLIGHT') return 2;
    if (currentState === 'PENDING_SUBMISSION') return 1;
    return 0; 
  };

  const currentIndex = getCurrentStateIndex();
  const currentState = transaction.transaction_state;
  const isTerminal = currentState === 'SETTLED' || currentState === 'FAILED' || currentState === 'FAILED_DLQ';

  const getStateColor = (stateCode: string, idx: number) => {
    const isActive = idx === currentIndex;
    const isCompleted = idx < currentIndex && idx < 4; 
    
    if (isActive) {
      if (stateCode === 'SETTLED') return 'bg-emerald-950/20 text-emerald-450 border-emerald-500/80 animate-pulse';
      if (stateCode === 'FAILED' || stateCode === 'FAILED_DLQ') return 'bg-rose-950/20 text-rose-455 border-rose-500/80 animate-pulse';
      if (stateCode === 'AMBIGUOUS_TIMEOUT') return 'bg-amber-950/20 text-amber-450 border-amber-500/80 animate-pulse';
      return 'bg-cyan-950/20 text-cyan-400 border-cyan-500/80 animate-pulse';
    }
    
    if (isCompleted) return 'bg-[#09090b]/80 text-zinc-500 border-zinc-800/80';
    if (isTerminal && idx < 4) return 'bg-zinc-950/20 text-zinc-650 border-zinc-900/60'; 
    
    return 'bg-zinc-950/40 text-zinc-700 border-zinc-900/40';
  };

  return (
    <div className="glass-card rounded-xl p-6 space-y-6 font-mono text-xs border-zinc-800/80 bg-zinc-950/40">
      <div className="flex justify-between items-center border-b border-zinc-900 pb-3.5">
        <div>
          <h3 className="text-sm font-display font-bold text-zinc-200">Transaction Status Machine</h3>
          <p className="text-[10px] text-zinc-500 mt-0.5">
            Reference Trace ID: <span className="text-zinc-400 font-bold select-all">{transaction.trace_id}</span>
          </p>
        </div>
        <div className="flex items-center space-x-3.5">
          {pollingActive && (
            <div className="flex items-center space-x-1.5 text-[9px] text-amber-500">
              <span className="relative flex h-1.5 w-1.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-amber-500"></span>
              </span>
              <span>Reconciling status...</span>
            </div>
          )}
          <button
            onClick={onRefresh}
            disabled={isTerminal}
            className={`border border-zinc-850 bg-zinc-900 hover:bg-zinc-800 text-zinc-350 rounded-lg px-2.5 py-1.5 text-[11px] cursor-pointer transition-colors flex items-center gap-1 ${
              isTerminal ? 'opacity-30 cursor-not-allowed' : ''
            }`}
          >
            <RefreshCcw size={10} className={pollingActive ? 'animate-spin' : ''} />
            <span>Check Now</span>
          </button>
        </div>
      </div>

      {/* State timeline visualization */}
      <div className="grid grid-cols-1 sm:grid-cols-4 md:grid-cols-7 gap-3">
        {states.slice(0, 4).concat(
          currentState === 'SETTLED' ? [states[4]] :
          currentState === 'FAILED' ? [states[5]] :
          currentState === 'FAILED_DLQ' ? [states[6]] :
          [states[4]] 
        ).map((st, idx) => {
          const colorClass = getStateColor(st.code, idx);
          
          return (
            <div
              key={st.code}
              className={`border px-3 py-3 rounded-lg flex flex-col justify-between h-20 transition-all duration-300 ${colorClass}`}
            >
              <span className="text-[9px] text-zinc-550">STAGE 0{idx + 1}</span>
              <span className="font-extrabold text-[11px] leading-tight truncate">
                {st.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Terminal log panel */}
      <div className="bg-[#050507] border border-zinc-900 rounded-xl p-4.5 text-[10.5px] text-zinc-400 space-y-2 overflow-y-auto max-h-48 scrollbar-thin select-none">
        <div className="text-zinc-600 flex items-start gap-1.5">
          <span>[{new Date(transaction.created_at).toLocaleTimeString()}]</span>
          <span>INITIATE: Created transaction log inside COU registry.</span>
        </div>
        <div className="text-zinc-650 flex items-start gap-1.5">
          <span>[{new Date(transaction.created_at).toLocaleTimeString()}]</span>
          <span>SYSTEM: Set state to INITIALIZED.</span>
        </div>
        
        {currentIndex >= 1 && (
          <div className="text-zinc-650 flex items-start gap-1.5">
            <span>[{new Date(transaction.created_at).toLocaleTimeString()}]</span>
            <span>SEC_MIDDLEWARE: Request signature verified. Canonical JSON validated.</span>
          </div>
        )}
        {currentIndex >= 2 && (
          <div className="text-zinc-600 flex items-start gap-1.5">
            <span>[{new Date(transaction.created_at).toLocaleTimeString()}]</span>
            <span>GATEWAY: Dispatched payload to routing network.</span>
          </div>
        )}
        
        {currentState === 'AMBIGUOUS_TIMEOUT' && (
          <>
            <div className="text-amber-500/90 flex items-start gap-1.5">
              <span>[{new Date().toLocaleTimeString()}]</span>
              <span className="flex items-center gap-1">
                <ShieldAlert size={10} />
                WARNING: Gateway timed out waiting for BOU billing response. State transitioned to AMBIGUOUS_TIMEOUT.
              </span>
            </div>
            <div className="text-amber-600/90 flex items-start gap-1.5">
              <span>[{new Date().toLocaleTimeString()}]</span>
              <span>RECON_WORKER: Enqueued trace {transaction.trace_id} for recovery polling.</span>
            </div>
            {pollingActive && (
              <div className="text-zinc-550 animate-pulse flex items-start gap-1.5">
                <span>[{new Date().toLocaleTimeString()}]</span>
                <span className="flex items-center gap-1">
                  <Activity size={10} className="text-zinc-600" />
                  POLLING: Querying OneView reconciliation logs from database...
                </span>
              </div>
            )}
          </>
        )}

        {currentState === 'SETTLED' && (
          <>
            <div className="text-emerald-500/80 flex items-start gap-1.5">
              <span>[{new Date(transaction.updated_at || '').toLocaleTimeString()}]</span>
              <span>RECON_WORKER: Reconciled transaction with terminal settlement: SETTLED.</span>
            </div>
            <div className="text-emerald-400 font-bold flex items-start gap-1.5">
              <span>[{new Date(transaction.updated_at || '').toLocaleTimeString()}]</span>
              <span className="flex items-center gap-1">
                <CheckCircle size={10} />
                SUCCESS: Payment completed. Reference: {transaction.response_payload?.payment_reference || 'REF-N/A'}
              </span>
            </div>
          </>
        )}

        {currentState === 'FAILED' && (
          <>
            <div className="text-rose-500/80 flex items-start gap-1.5">
              <span>[{new Date(transaction.updated_at || '').toLocaleTimeString()}]</span>
              <span>RECON_WORKER: Reconciled transaction with terminal settlement: FAILED.</span>
            </div>
            <div className="text-rose-400 font-bold flex items-start gap-1.5">
              <span>[{new Date(transaction.updated_at || '').toLocaleTimeString()}]</span>
              <span className="flex items-center gap-1">
                <ShieldAlert size={10} />
                ERROR: Transaction was rejected by downstream provider.
              </span>
            </div>
          </>
        )}

        {currentState === 'FAILED_DLQ' && (
          <>
            <div className="text-rose-500/80 flex items-start gap-1.5">
              <span>[{new Date(transaction.updated_at || '').toLocaleTimeString()}]</span>
              <span>RETRY_ENGINE: Max attempts exceeded. Transitioned to FAILED_DLQ.</span>
            </div>
            <div className="text-rose-455 font-bold flex items-start gap-1.5 animate-pulse">
              <span>[{new Date(transaction.updated_at || '').toLocaleTimeString()}]</span>
              <span className="flex items-center gap-1">
                <ShieldAlert size={10} />
                CRITICAL: Transaction isolated in Dead-Letter Queue. Requires manual operations review.
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default TransactionTracker;
