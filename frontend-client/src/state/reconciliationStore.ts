import { create } from 'zustand';
import apiClient from '../api/apiClient';

export interface ReconciliationLogSchema {
  polling_attempts: number;
  resolved_state: string | null;
  reconciliation_status: string;
  created_at: string;
}

export interface OneViewTransactionItem {
  trace_id: string;
  biller_id: string;
  amount: number;
  transaction_state: string; // INITIALIZED, PENDING_SUBMISSION, NETWORK_IN_FLIGHT, AMBIGUOUS_TIMEOUT, SETTLED, FAILED, FAILED_DLQ
  created_at: string;
  updated_at: string | null;
  request_payload: any | null;
  response_payload: any | null;
  retry_attempts: number;
  reconciliation_log: ReconciliationLogSchema | null;
}

interface ReconciliationState {
  transactions: OneViewTransactionItem[];
  loading: boolean;
  error: string | null;
  reconcilingTraceIds: Record<string, boolean>;

  loadOneView: (customerId: string) => Promise<void>;
  reconcileTransaction: (traceId: string, customerId: string) => Promise<any>;
}

export const useReconciliationStore = create<ReconciliationState>((set, get) => ({
  transactions: [],
  loading: false,
  error: null,
  reconcilingTraceIds: {},

  loadOneView: async (customerId) => {
    set({ loading: true, error: null });
    const sourceId = import.meta.env.VITE_SOURCE_ID || 'mbanking';

    try {
      const response = await apiClient.get(`/BOBCOU/BBPS/${sourceId}/customers/${customerId}/billpay/oneview`);
      // Sort transactions by created_at descending
      const txs = (response.data.transactions || []).sort(
        (a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
      set({ transactions: txs, loading: false });
    } catch (err: any) {
      console.error('Failed to load OneView transactions', err);
      set({ 
        error: err.response?.data?.message || err.message || 'Failed to fetch transaction logs.', 
        loading: false 
      });
    }
  },

  reconcileTransaction: async (traceId, customerId) => {
    const { reconcilingTraceIds } = get();
    set({ 
      reconcilingTraceIds: { ...reconcilingTraceIds, [traceId]: true } 
    });

    const sourceId = import.meta.env.VITE_SOURCE_ID || 'mbanking';

    try {
      const response = await apiClient.post(`/BOBCOU/BBPS/${sourceId}/billpay/reconcile`, {
        trace_id: traceId
      });
      
      // Reload history to show updated state
      await get().loadOneView(customerId);
      return response.data;
    } catch (err: any) {
      console.error('Manual reconciliation failed', err);
      throw new Error(err.response?.data?.message || 'Manual reconciliation failed.');
    } finally {
      // Clean up reconciling state
      const updatedIds = { ...get().reconcilingTraceIds };
      delete updatedIds[traceId];
      set({ reconcilingTraceIds: updatedIds });
    }
  }
}));
