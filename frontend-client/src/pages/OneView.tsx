import React, { useEffect, useState } from 'react';
import { 
  History, 
  RotateCw, 
  Search, 
  SlidersHorizontal,
  ChevronRight,
  Database,
  Cpu,
  Layers,
  Activity,
  ShieldCheck,
  CheckCircle,
  AlertTriangle,
  Play
} from 'lucide-react';
import { useReconciliationStore } from '../state/reconciliationStore';
import { useRecovery } from '../hooks/useRecovery';
import { useAuthStore } from '../state/authStore';

export const OneView: React.FC = () => {
  const { transactions, loading, error: storeError, loadOneView } = useReconciliationStore();
  const { triggerRecovery, reconcilingId, error: recoveryError, successMessage } = useRecovery();
  const { role } = useAuthStore();
  const [customerId] = useState('cust123');
  const [selectedTx, setSelectedTx] = useState<any | null>(null);

  useEffect(() => {
    loadOneView(customerId);
  }, [loadOneView, customerId]);

  const handleRefresh = () => {
    loadOneView(customerId);
  };

  const handleReconcile = async (traceId: string) => {
    await triggerRecovery(traceId, customerId);
  };

  const getBadgeStyle = (state: string) => {
    switch (state) {
      case 'SETTLED':
        return 'badge-premium-emerald';
      case 'AMBIGUOUS_TIMEOUT':
        return 'badge-premium-amber animate-pulse';
      case 'FAILED':
      case 'FAILED_DLQ':
        return 'badge-premium-rose';
      default:
        return 'badge-premium-cyan';
    }
  };

  return (
    <div className="space-y-6">
      {/* PAGE HEADER */}
      <div className="flex flex-col md:flex-row md:justify-between md:items-center border-b border-zinc-900/60 pb-4 gap-4">
        <div>
          <h1 className="text-2xl font-extrabold font-display text-zinc-100 tracking-tight flex items-center gap-2">
            <History className="text-cyan-400 w-6 h-6 stroke-[2]" />
            OneView Operations Ledger
          </h1>
          <p className="text-xs text-zinc-500 mt-1">
            REAL-TIME SETTLEMENT AUDITING, DETAILED STAGE TRACES, AND MANUAL SWEEP CONTROLS FOR CUSTOMER: <span className="font-mono font-bold text-cyan-400 bg-cyan-950/20 px-1.5 py-0.2 rounded border border-cyan-900/30">{customerId}</span>
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={loading}
          className="border border-zinc-800 bg-zinc-900/60 hover:bg-zinc-800 text-zinc-300 rounded-lg px-3.5 py-1.5 text-[11px] cursor-pointer transition-colors font-mono flex items-center gap-1.5"
        >
          <RotateCw size={12} className={loading ? 'animate-spin' : ''} />
          <span>{loading ? 'Refreshing...' : 'Refresh Logs'}</span>
        </button>
      </div>

      {/* Alert Notices */}
      {successMessage && (
        <div className="bg-emerald-950/20 border border-emerald-900/40 text-emerald-400 p-4.5 rounded-xl font-mono text-xs animate-fade-in flex items-center gap-2">
          <CheckCircle size={14} />
          <span>{successMessage}</span>
        </div>
      )}
      {recoveryError && (
        <div className="bg-rose-950/20 border border-rose-900/40 text-rose-450 p-4.5 rounded-xl font-mono text-xs animate-fade-in flex items-start gap-2.5">
          <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-bold">Reconciliation sweep failed:</span>
            <p className="mt-1 text-rose-350">{recoveryError}</p>
          </div>
        </div>
      )}
      {storeError && (
        <div className="bg-rose-950/20 border border-rose-900/40 text-rose-455 p-4.5 rounded-xl font-mono text-xs animate-fade-in flex items-start gap-2.5">
          <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-bold">Database registry read failure:</span>
            <p className="mt-1 text-rose-355">{storeError}</p>
          </div>
        </div>
      )}

      {/* Main split display: table vs detailed inspect */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Side: Transactions List Table (8 cols) */}
        <div className="lg:col-span-8 space-y-4">
          {loading && transactions.length === 0 ? (
            <div className="text-zinc-650 text-xs font-mono py-16 text-center flex items-center justify-center gap-2">
              <RotateCw className="animate-spin text-zinc-650" size={16} />
              Scanning database transaction schemas...
            </div>
          ) : transactions.length === 0 ? (
            <div className="text-zinc-500 text-xs font-sans py-16 border border-dashed border-zinc-900 rounded-xl text-center bg-zinc-950/10 flex flex-col items-center justify-center gap-2.5">
              <History size={28} className="text-zinc-700" />
              <span>No transactions registered for Rahul Sharma.</span>
            </div>
          ) : (
            <div className="overflow-x-auto border border-zinc-900/80 rounded-xl bg-zinc-950/40 shadow-md">
              <table className="w-full text-left font-mono text-[11px] border-collapse">
                <thead>
                  <tr className="bg-zinc-900/30 border-b border-zinc-900 text-zinc-500 uppercase tracking-wider text-[9px] select-none">
                    <th className="px-4.5 py-3">Timestamp</th>
                    <th className="px-4.5 py-3">Biller Reference</th>
                    <th className="px-4.5 py-3">Amount</th>
                    <th className="px-4.5 py-3">Status State</th>
                    <th className="px-4.5 py-3 text-right">Settlement Sweeps</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-900/60">
                  {transactions.map((tx) => {
                    const isReconciling = reconcilingId === tx.trace_id;
                    const isAmbiguous = tx.transaction_state === 'AMBIGUOUS_TIMEOUT';
                    const isSelected = selectedTx?.trace_id === tx.trace_id;
                    
                    return (
                      <tr
                        key={tx.trace_id}
                        className={`hover:bg-zinc-900/30 cursor-pointer transition-colors ${
                          isSelected ? 'bg-cyan-950/10 border-r-2 border-r-cyan-400' : ''
                        }`}
                        onClick={() => setSelectedTx(tx)}
                      >
                        <td className="px-4.5 py-3.5 text-zinc-550 whitespace-nowrap">
                          {new Date(tx.created_at).toLocaleString()}
                        </td>
                        <td className="px-4.5 py-3.5 text-zinc-200 font-extrabold font-display">{tx.biller_id}</td>
                        <td className="px-4.5 py-3.5 text-zinc-300 font-sans font-semibold">₹{tx.amount.toFixed(2)}</td>
                        <td className="px-4.5 py-3.5 whitespace-nowrap">
                          <span className={`badge-premium ${getBadgeStyle(tx.transaction_state)}`}>
                            {tx.transaction_state}
                          </span>
                        </td>
                        <td className="px-4.5 py-3.5 text-right whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                          {isAmbiguous ? (
                            role === 'ADMIN' || role === 'OPERATIONS' ? (
                              <button
                                onClick={() => handleReconcile(tx.trace_id)}
                                disabled={isReconciling}
                                className="bg-amber-500 hover:bg-amber-450 disabled:bg-zinc-900 text-black font-mono text-[9px] font-bold px-2.5 py-1.5 rounded transition-all cursor-pointer shadow-sm hover:shadow"
                              >
                                {isReconciling ? 'RUNNING...' : 'RECONCILE'}
                              </button>
                            ) : (
                              <span className="text-[9px] text-amber-500 font-bold bg-amber-950/20 border border-amber-900/20 px-2 py-0.5 rounded">
                                PENDING RESOLUTION
                              </span>
                            )
                          ) : (
                            <span className="text-[10px] text-zinc-650">TERMINAL</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Right Side: Payload Inspection Console (4 cols) */}
        <div className="lg:col-span-4 flex flex-col">
          {!selectedTx ? (
            <div className="border border-dashed border-zinc-900 rounded-xl p-16 text-center text-zinc-500 font-sans text-xs bg-zinc-950/10 flex-1 flex flex-col items-center justify-center gap-3">
              <Search size={32} className="text-zinc-700" />
              <div className="max-w-xs leading-relaxed">
                Select a transaction row from the operations ledger table to inspect cryptographic header packets and timeline traces.
              </div>
            </div>
          ) : (
            <div className="glass-card rounded-xl p-5 space-y-5 font-mono text-xs border-zinc-800/80 bg-zinc-950/40 flex-1 overflow-y-auto">
              <div className="flex justify-between items-start border-b border-zinc-900 pb-3">
                <div>
                  <h3 className="font-display font-bold text-zinc-200 text-sm">Payload Inspector</h3>
                  <span className="text-[10px] text-zinc-500">Trace: {selectedTx.trace_id}</span>
                </div>
                <button
                  onClick={() => setSelectedTx(null)}
                  className="text-zinc-500 hover:text-zinc-300 font-mono text-[10px] cursor-pointer"
                >
                  Clear Selection
                </button>
              </div>

              {/* Status Section */}
              <div className="space-y-1.5">
                <span className="text-[9px] text-zinc-550 block font-bold uppercase tracking-wider">STATE MACHINE POSITION</span>
                <span className={`badge-premium ${getBadgeStyle(selectedTx.transaction_state)}`}>
                  {selectedTx.transaction_state}
                </span>
              </div>

              {/* Reconciliation & Recovery Activity Timeline */}
              <div className="bg-[#050507]/40 border border-zinc-900 p-5 rounded-xl space-y-4 overflow-hidden relative">
                <span className="text-[9px] text-zinc-500 font-bold block tracking-wider uppercase border-b border-zinc-900 pb-2">
                  🔄 Transaction Stage Timeline
                </span>
                
                <div className="flex justify-between items-center relative py-5 max-w-xs mx-auto">
                  {/* Connecting background line */}
                  <div className="absolute left-4 right-4 top-1/2 -translate-y-1/2 h-[2px] bg-zinc-800 rounded-full z-0">
                    <div 
                      className={`h-full rounded-full transition-all duration-1000 ease-out ${
                        selectedTx.transaction_state === 'SETTLED' ? 'bg-emerald-500/50 shadow-[0_0_10px_rgba(16,185,129,0.5)]' :
                        selectedTx.transaction_state === 'FAILED_DLQ' ? 'bg-rose-500/50 shadow-[0_0_10px_rgba(244,63,94,0.5)]' :
                        'bg-amber-500/50 shadow-[0_0_10px_rgba(245,158,11,0.5)]'
                      }`}
                      style={{
                        width: selectedTx.transaction_state === 'SETTLED' ? '100%' :
                               selectedTx.retry_attempts > 0 ? '75%' :
                               selectedTx.reconciliation_log ? '50%' :
                               '25%'
                      }}
                    ></div>
                  </div>

                  {/* Step 1: Initialized */}
                  <div className="relative z-10 flex flex-col items-center gap-1.5">
                    <div className="w-8 h-8 rounded-full bg-zinc-950 border border-emerald-500 flex items-center justify-center shadow-[0_0_8px_rgba(16,185,129,0.25)]">
                      <span className="text-emerald-400 text-[10px] font-extrabold">1</span>
                    </div>
                  </div>

                  {/* Step 2: In-Flight */}
                  <div className="relative z-10 flex flex-col items-center gap-1.5">
                    <div className={`w-8 h-8 rounded-full bg-zinc-950 border flex items-center justify-center ${
                      selectedTx.transaction_state !== 'INITIALIZED' ? 'border-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.25)]' : 'border-zinc-800'
                    }`}>
                      <span className={`text-[10px] font-extrabold ${selectedTx.transaction_state !== 'INITIALIZED' ? 'text-emerald-400' : 'text-zinc-600'}`}>2</span>
                    </div>
                  </div>

                  {/* Step 3: Ambiguous */}
                  <div className="relative z-10 flex flex-col items-center gap-1.5">
                    <div className={`w-8 h-8 rounded-full bg-zinc-950 border flex items-center justify-center ${
                      selectedTx.transaction_state === 'AMBIGUOUS_TIMEOUT' || selectedTx.transaction_state === 'SETTLED' || selectedTx.transaction_state === 'FAILED_DLQ'
                        ? 'border-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.25)] animate-pulse'
                        : 'border-zinc-800'
                    }`}>
                      <span className={`text-[10px] font-extrabold ${selectedTx.transaction_state === 'AMBIGUOUS_TIMEOUT' || selectedTx.transaction_state === 'SETTLED' || selectedTx.transaction_state === 'FAILED_DLQ' ? 'text-amber-400' : 'text-zinc-600'}`}>3</span>
                    </div>
                  </div>

                  {/* Step 4: Terminal */}
                  <div className="relative z-10 flex flex-col items-center gap-1.5">
                    <div className={`w-8 h-8 rounded-full bg-zinc-950 border flex items-center justify-center ${
                      selectedTx.transaction_state === 'SETTLED' ? 'border-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' :
                      selectedTx.transaction_state === 'FAILED_DLQ' || selectedTx.transaction_state === 'FAILED' ? 'border-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.5)]' :
                      'border-zinc-800'
                    }`}>
                      <span className={`text-[10px] font-extrabold ${
                        selectedTx.transaction_state === 'SETTLED' ? 'text-emerald-400' :
                        selectedTx.transaction_state === 'FAILED_DLQ' || selectedTx.transaction_state === 'FAILED' ? 'text-rose-400' :
                        'text-zinc-650'
                      }`}>4</span>
                    </div>
                  </div>
                </div>

                <div className="flex justify-between text-[8px] text-zinc-600 font-mono tracking-widest pt-2">
                  <span>INIT</span>
                  <span>ROUTE</span>
                  <span>TIMEOUT</span>
                  <span>SETTLE</span>
                </div>
                
                {/* Details Section */}
                <div className="grid grid-cols-2 gap-4 text-[9px] pt-3.5 border-t border-zinc-900 bg-black/10 p-2.5 rounded-lg">
                  <div>
                    <span className="text-zinc-550 block mb-0.5">Sweep Iterations</span>
                    <span className="text-zinc-300 font-bold text-xs">{selectedTx.reconciliation_log?.polling_attempts ?? (selectedTx.transaction_state === 'SETTLED' ? 1 : 0)} sweeps</span>
                  </div>
                  <div>
                    <span className="text-zinc-550 block mb-0.5">Retries Executed</span>
                    <span className="text-zinc-300 font-bold text-xs">{selectedTx.retry_attempts} attempts</span>
                  </div>
                </div>
              </div>

              {/* Request Payload JSON */}
              <div className="space-y-1.5">
                <span className="text-[9px] text-zinc-550 block font-bold uppercase tracking-wider">X-API REQUEST METADATA</span>
                <pre className="bg-[#050507] border border-zinc-900 p-3 rounded-lg text-[9px] text-cyan-400/90 overflow-x-auto max-h-36 scrollbar-thin select-all">
                  {JSON.stringify(selectedTx.request_payload || {}, null, 2)}
                </pre>
              </div>

              {/* Response Payload JSON */}
              <div className="space-y-1.5">
                <span className="text-[9px] text-zinc-550 block font-bold uppercase tracking-wider">COU VERDICT BINDINGS</span>
                <pre className="bg-[#050507] border border-zinc-900 p-3 rounded-lg text-[9px] text-emerald-400/90 overflow-x-auto max-h-36 scrollbar-thin select-all">
                  {JSON.stringify(selectedTx.response_payload || {}, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default OneView;
