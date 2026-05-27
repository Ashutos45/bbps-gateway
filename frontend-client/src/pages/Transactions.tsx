import React, { useEffect, useState } from 'react';
import { 
  ScrollText, 
  RotateCw, 
  Search, 
  SlidersHorizontal,
  XCircle,
  Database,
  Calendar,
  DollarSign
} from 'lucide-react';
import { useReconciliationStore } from '../state/reconciliationStore';
import { useAuthStore } from '../state/authStore';

export const Transactions: React.FC = () => {
  const { transactions, loading, loadOneView } = useReconciliationStore();
  const { role } = useAuthStore();
  const [customerId] = useState('cust123');
  
  const [searchTrace, setSearchTrace] = useState('');
  const [filterState, setFilterState] = useState('');
  const [filterBiller, setFilterBiller] = useState('');

  useEffect(() => {
    loadOneView(customerId);
  }, [loadOneView, customerId]);

  const handleRefresh = () => {
    loadOneView(customerId);
  };

  const uniqueBillers = Array.from(new Set(transactions.map((tx) => tx.biller_id))).sort();

  const filtered = transactions.filter((tx) => {
    const matchesTrace = !searchTrace || tx.trace_id.toLowerCase().includes(searchTrace.toLowerCase());
    const matchesState = !filterState || tx.transaction_state === filterState;
    const matchesBiller = !filterBiller || tx.biller_id === filterBiller;
    return matchesTrace && matchesState && matchesBiller;
  });

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
      {/* HEADER */}
      <div className="flex flex-col md:flex-row md:justify-between md:items-center border-b border-zinc-900/60 pb-4 gap-4">
        <div>
          <h1 className="text-2xl font-extrabold font-display text-zinc-100 tracking-tight flex items-center gap-2">
            <ScrollText className="text-cyan-400 w-6 h-6 stroke-[2]" />
            Transactions Audit Ledger
            {role === 'AUDITOR' && (
              <span className="px-2 py-0.5 text-[9px] font-extrabold uppercase font-mono tracking-widest bg-purple-950/40 text-purple-400 border border-purple-800/40 rounded">
                Read-Only Audit
              </span>
            )}
          </h1>
          <p className="text-xs text-zinc-550 mt-1">
            FILTER, SEARCH, AND AUDIT FULL HISTORIES OF Nodal PAYMENTS UNDER SYSTEM CUSTOMER ID: <span className="font-mono text-cyan-400 bg-cyan-950/20 px-1.5 py-0.2 rounded border border-cyan-900/30">{customerId}</span>
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={loading}
          className="border border-zinc-800 bg-zinc-900/60 hover:bg-zinc-800 text-zinc-300 rounded-lg px-3.5 py-1.5 text-[11px] cursor-pointer transition-colors font-mono flex items-center gap-1.5"
        >
          <RotateCw size={12} className={loading ? 'animate-spin' : ''} />
          <span>{loading ? 'Querying...' : 'Reload Ledger'}</span>
        </button>
      </div>

      {/* Filter Options Console */}
      <div className="glass-card rounded-xl p-5 border-zinc-800/80 bg-zinc-950/40 grid grid-cols-1 sm:grid-cols-3 gap-5 font-mono text-xs shadow-sm">
        {/* Search by Trace ID */}
        <div>
          <label className="block text-[10px] text-zinc-550 mb-2 font-bold uppercase tracking-wider">Search Trace Ref</label>
          <div className="relative">
            <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-zinc-500 pointer-events-none">
              <Search size={12} />
            </span>
            <input
              type="text"
              value={searchTrace}
              onChange={(e) => setSearchTrace(e.target.value)}
              placeholder="Search trace ID..."
              className="input-premium pl-9 font-mono"
            />
          </div>
        </div>

        {/* Filter by Biller */}
        <div>
          <label className="block text-[10px] text-zinc-550 mb-2 font-bold uppercase tracking-wider">Select Biller ID</label>
          <div className="relative">
            <select
              value={filterBiller}
              onChange={(e) => setFilterBiller(e.target.value)}
              className="input-premium appearance-none bg-zinc-950 font-mono pr-8"
            >
              <option value="">All Operators</option>
              {uniqueBillers.map((b) => (
                <option key={b} value={b}>
                  {b}
                </option>
              ))}
            </select>
            <span className="absolute inset-y-0 right-0 pr-3 flex items-center text-zinc-500 pointer-events-none">
              <SlidersHorizontal size={12} />
            </span>
          </div>
        </div>

        {/* Filter by State */}
        <div>
          <label className="block text-[10px] text-zinc-550 mb-2 font-bold uppercase tracking-wider">Transaction State</label>
          <div className="relative">
            <select
              value={filterState}
              onChange={(e) => setFilterState(e.target.value)}
              className="input-premium appearance-none bg-zinc-950 font-mono pr-8"
            >
              <option value="">All States</option>
              <option value="INITIALIZED">INITIALIZED</option>
              <option value="PENDING_SUBMISSION">PENDING_SUBMISSION</option>
              <option value="NETWORK_IN_FLIGHT">NETWORK_IN_FLIGHT</option>
              <option value="AMBIGUOUS_TIMEOUT">AMBIGUOUS_TIMEOUT</option>
              <option value="SETTLED">SETTLED</option>
              <option value="FAILED">FAILED</option>
              <option value="FAILED_DLQ">FAILED_DLQ</option>
            </select>
            <span className="absolute inset-y-0 right-0 pr-3 flex items-center text-zinc-500 pointer-events-none">
              <SlidersHorizontal size={12} />
            </span>
          </div>
        </div>
      </div>

      {/* Results Overview */}
      <div className="flex justify-between items-center text-[10px] text-zinc-500 px-1 font-mono">
        <span>Ledger query compiled {filtered.length} matching rows</span>
        {(searchTrace || filterState || filterBiller) && (
          <button
            onClick={() => {
              setSearchTrace('');
              setFilterState('');
              setFilterBiller('');
            }}
            className="text-cyan-400 hover:text-cyan-300 transition-colors flex items-center gap-1 cursor-pointer underline underline-offset-2"
          >
            <XCircle size={10} />
            <span>Reset Filters</span>
          </button>
        )}
      </div>

      {/* Ledger Table */}
      {loading && filtered.length === 0 ? (
        <div className="text-zinc-650 text-xs font-mono py-16 text-center flex items-center justify-center gap-2">
          <RotateCw className="animate-spin text-zinc-600" size={16} />
          Accessing ledger registries...
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-zinc-500 text-xs font-sans py-16 border border-dashed border-zinc-900 rounded-xl text-center bg-zinc-950/10 flex flex-col items-center justify-center gap-2">
          <Database size={24} className="text-zinc-700" />
          <span>No records match current query configurations.</span>
        </div>
      ) : (
        <div className="overflow-x-auto border border-zinc-900/80 rounded-xl bg-zinc-950/40 shadow-md">
          <table className="w-full text-left border-collapse font-mono text-[11px]">
            <thead>
              <tr className="bg-zinc-900/30 border-b border-zinc-900 text-zinc-500 uppercase tracking-wider text-[9px] select-none">
                <th className="px-4.5 py-3 flex items-center gap-1"><Calendar size={11} />Timestamp</th>
                <th className="px-4.5 py-3">Trace Reference</th>
                <th className="px-4.5 py-3">Operator ID</th>
                <th className="px-4.5 py-3 flex items-center gap-1"><DollarSign size={11} />Settlement</th>
                <th className="px-4.5 py-3">Recovery Sweeps</th>
                <th className="px-4.5 py-3 text-right">Status State</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-900/60">
              {filtered.map((tx) => {
                return (
                  <tr key={tx.trace_id} className="hover:bg-zinc-900/20">
                    <td className="px-4.5 py-3.5 text-zinc-550 whitespace-nowrap">
                      {new Date(tx.created_at).toLocaleString()}
                    </td>
                    <td className="px-4.5 py-3.5 text-zinc-300 font-extrabold select-all">
                      {tx.trace_id}
                    </td>
                    <td className="px-4.5 py-3.5 text-zinc-400 font-bold font-display">{tx.biller_id}</td>
                    <td className="px-4.5 py-3.5 text-zinc-200 font-sans font-semibold">₹{tx.amount.toFixed(2)}</td>
                    <td className="px-4.5 py-3.5 text-zinc-500 font-bold">{tx.reconciliation_log?.polling_attempts || 0}</td>
                    <td className="px-4.5 py-3.5 text-right whitespace-nowrap">
                      <span className={`badge-premium ${getBadgeStyle(tx.transaction_state)}`}>
                        {tx.transaction_state}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default Transactions;
