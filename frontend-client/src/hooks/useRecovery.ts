import { useState, useCallback } from 'react';
import { useReconciliationStore } from '../state/reconciliationStore';

export function useRecovery() {
  const reconcileTransaction = useReconciliationStore((state) => state.reconcileTransaction);
  const [reconcilingId, setReconcilingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const triggerRecovery = useCallback(
    async (traceId: string, customerId: string) => {
      setReconcilingId(traceId);
      setError(null);
      setSuccessMessage(null);
      try {
        const response = await reconcileTransaction(traceId, customerId);
        setSuccessMessage(
          response?.message || `Transaction ${traceId} successfully reconciled: resolved to ${response?.resolved_state || 'final state'}.`
        );
      } catch (err: any) {
        setError(err.message || 'Reconciliation trigger failed.');
      } finally {
        setReconcilingId(null);
      }
    },
    [reconcileTransaction]
  );

  return {
    triggerRecovery,
    reconcilingId,
    error,
    successMessage,
    clearStates: () => {
      setError(null);
      setSuccessMessage(null);
    },
  };
}
export default useRecovery;
