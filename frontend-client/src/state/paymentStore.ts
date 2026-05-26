import { create } from 'zustand';
import apiClient from '../api/apiClient';
import { Biller, Authenticator, Customer, PayBillResponse, FavoriteBiller, TransactionLog } from '../types';
import { useToastStore } from './toastStore';
import { useReconciliationStore } from './reconciliationStore';

interface PaymentState {
  activeBiller: Biller | null;
  activeBillDetails: any | null;
  billFetchStatus: 'IDLE' | 'LOADING' | 'SUCCESS' | 'ERROR';
  billFetchError: string | null;
  
  paymentStatus: 'IDLE' | 'PENDING' | 'SUCCESS' | 'ERROR';
  paymentError: string | null;
  paymentResponse: PayBillResponse | null;
  currentTransaction: TransactionLog | null;
  
  favoriteBillers: FavoriteBiller[];
  favoriteBillersLoading: boolean;
  
  simulateFailure: boolean;
  
  // Actions
  setActiveBiller: (biller: Biller | null) => void;
  setSimulateFailure: (simulate: boolean) => void;
  resetBillFetch: () => void;
  resetPayment: () => void;
  
  fetchBill: (
    customerId: string,
    authenticators: Authenticator[],
    customer: Customer
  ) => Promise<any>;
  
  payBill: (params: {
    customerId: string;
    customer: Customer;
    validationId: string;
    paymentAmount: string;
    paymentType: string;
    paymentMethod: string;
    cardholderName?: string;
    authenticators: Authenticator[];
  }) => Promise<PayBillResponse>;
  
  loadFavoriteBillers: (customerId: string) => Promise<void>;
  addFavoriteBiller: (params: {
    customerId: string;
    billerId: string;
    shortName: string;
    authenticators: Authenticator[];
    autopayStatus: string;
    autopayAmount?: number;
    paymentAccount?: any;
    frequency?: string;
  }) => Promise<void>;
  deleteFavoriteBiller: (customerId: string, billerAccountId: string) => Promise<void>;
}

export const usePaymentStore = create<PaymentState>((set, get) => ({
  activeBiller: null,
  activeBillDetails: null,
  billFetchStatus: 'IDLE',
  billFetchError: null,
  
  paymentStatus: 'IDLE',
  paymentError: null,
  paymentResponse: null,
  currentTransaction: null,
  
  favoriteBillers: [],
  favoriteBillersLoading: false,
  
  simulateFailure: false,

  setActiveBiller: (biller) => set({ activeBiller: biller, activeBillDetails: null, billFetchStatus: 'IDLE', billFetchError: null }),
  setSimulateFailure: (simulate) => set({ simulateFailure: simulate }),
  resetBillFetch: () => set({ activeBillDetails: null, billFetchStatus: 'IDLE', billFetchError: null }),
  resetPayment: () => set({ paymentStatus: 'IDLE', paymentError: null, paymentResponse: null, currentTransaction: null }),

  fetchBill: async (customerId, authenticators, customer) => {
    const { activeBiller } = get();
    if (!activeBiller) {
      throw new Error('No active biller selected.');
    }
    
    set({ billFetchStatus: 'LOADING', billFetchError: null });
    const sourceId = import.meta.env.VITE_SOURCE_ID || 'mbanking';

    try {
      const response = await apiClient.post(
        `/BOBCOU/BBPS/${sourceId}/customers/${customerId}/billpay/validate`,
        {
          billerid: activeBiller.biller_id,
          billeraccountid: authenticators[0]?.value || 'ELEC987654321',
        }
      );
      set({ activeBillDetails: response.data, billFetchStatus: 'SUCCESS' });
      useToastStore.getState().addToast('success', 'Bill fetched successfully.');
      return response.data;
    } catch (err: any) {
      const errMsg = err.response?.data?.message || err.message || 'Failed to fetch bill.';
      set({ billFetchStatus: 'ERROR', billFetchError: errMsg });
      useToastStore.getState().addToast('error', `Bill fetch failed: ${errMsg}`);
      throw new Error(errMsg);
    }
  },

  payBill: async (params) => {
    const { activeBiller, simulateFailure } = get();
    if (!activeBiller) {
      throw new Error('No active biller selected.');
    }

    set({ paymentStatus: 'PENDING', paymentError: null, paymentResponse: null, currentTransaction: null });
    const sourceId = import.meta.env.VITE_SOURCE_ID || 'mbanking';

    const paymentAmount = params.paymentAmount;

    // Send minimal request payload as required by enterprise BBPS architecture
    const requestBody = {
      validationid: params.validationId,
      payment_amount: paymentAmount,
      payment_method: params.paymentMethod
    };

    // Prepare simulated failure header if toggled
    const headers: Record<string, string> = {};
    if (simulateFailure) {
      headers['X-Simulate-Failure'] = 'true';
    }

    try {
      const response = await apiClient.post(
        `/BOBCOU/BBPS/${sourceId}/customers/${params.customerId}/billpay/payments`,
        requestBody,
        { headers }
      );
      
      set({ 
        paymentStatus: 'SUCCESS', 
        paymentResponse: response.data 
      });
      useToastStore.getState().addToast('success', 'Payment successful.');
      return response.data;
    } catch (err: any) {
      const errMsg = err.response?.data?.message || err.message || 'Payment execution failed.';
      const status = err.response?.status;
      
      // If we received a 504 Gateway Timeout or an ambiguous state payload
      if (status === 504 || errMsg.toLowerCase().includes('timeout') || errMsg.toLowerCase().includes('ambiguous')) {
        let traceId = '';
        try {
          await useReconciliationStore.getState().loadOneView(params.customerId);
          const txs = useReconciliationStore.getState().transactions;
          if (txs.length > 0) {
            traceId = txs[0].trace_id;
          }
        } catch (ovErr) {
          console.error('Failed to retrieve trace ID from OneView:', ovErr);
        }

        set({
          paymentStatus: 'ERROR',
          paymentError: `AMBIGUOUS TIMEOUT: ${errMsg}. Polling active for recovery...`,
          currentTransaction: {
            id: '',
            trace_id: traceId || 'UNKNOWN',
            customer_id: params.customerId,
            biller_id: activeBiller.biller_id,
            amount: parseFloat(paymentAmount),
            transaction_state: 'AMBIGUOUS_TIMEOUT',
            request_payload: requestBody,
            response_payload: err.response?.data || null,
            retry_attempts: 0,
            next_retry_at: null,
            worker_last_execution: null,
            reconciliation_version: 0,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          }
        });
      } else {
        set({ paymentStatus: 'ERROR', paymentError: errMsg });
      }
      throw err;
    }
  },

  loadFavoriteBillers: async (customerId) => {
    set({ favoriteBillersLoading: true });
    const sourceId = import.meta.env.VITE_SOURCE_ID || 'mbanking';
    try {
      const response = await apiClient.get(`/BOBCOU/BBPS/${sourceId}/customers/${customerId}/billpay/billeraccounts`);
      set({ favoriteBillers: response.data, favoriteBillersLoading: false });
    } catch (err) {
      console.error('Failed to load favorite billers', err);
      set({ favoriteBillersLoading: false });
    }
  },

  addFavoriteBiller: async (params) => {
    const sourceId = import.meta.env.VITE_SOURCE_ID || 'mbanking';
    try {
      await apiClient.post(
        `/BOBCOU/BBPS/${sourceId}/customers/${params.customerId}/billpay/billeraccounts`,
        {
          billerid: params.billerId
        }
      );
      await get().loadFavoriteBillers(params.customerId);
    } catch (err: any) {
      console.error('Failed to add favorite biller', err);
      throw new Error(err.response?.data?.message || 'Failed to register favorite biller.');
    }
  },

  deleteFavoriteBiller: async (customerId, billerAccountId) => {
    const sourceId = import.meta.env.VITE_SOURCE_ID || 'mbanking';
    try {
      await apiClient.delete(
        `/BOBCOU/BBPS/${sourceId}/customers/${customerId}/billpay/billeraccounts/${billerAccountId}`
      );
      await get().loadFavoriteBillers(customerId);
    } catch (err) {
      console.error('Failed to delete favorite biller', err);
      throw err;
    }
  }
}));
