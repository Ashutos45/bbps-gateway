import { create } from 'zustand';
import apiClient from '../api/apiClient';
import { TelemetryReport } from '../types';

interface TelemetryState {
  report: TelemetryReport | null;
  loading: boolean;
  error: string | null;
  fetchTelemetry: () => Promise<void>;
}

export const useTelemetryStore = create<TelemetryState>((set) => ({
  report: null,
  loading: false,
  error: null,

  fetchTelemetry: async () => {
    set({ loading: true, error: null });
    try {
      // Telemetry route is public in FastAPI, so we bypass signing in interceptor or keep it signed
      const response = await apiClient.get('/telemetry');
      set({ report: response.data, loading: false });
    } catch (err: any) {
      console.error('Failed to load telemetry metrics', err);
      set({ 
        error: err.response?.data?.message || err.message || 'Failed to fetch telemetry metrics.', 
        loading: false 
      });
    }
  }
}));
