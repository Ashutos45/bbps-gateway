export interface Biller {
  biller_id: string;
  biller_name: string;
  category: string;
  region: string;
  metadata?: {
    min_amount?: string;
    max_amount?: string;
    [key: string]: any;
  };
}

export interface Authenticator {
  seq: string;
  parameter_name: string;
  value: string;
}

export interface Customer {
  firstname: string;
  lastname: string;
  mobile: string;
}

export interface PaymentAccount {
  payment_method: string;
  cardholder_name?: string;
  [key: string]: any;
}

export interface PayBillRequest {
  billerid: string;
  validationid: string;
  payment_amount: string;
  debit_amount: string;
  payment_type: string;
  source_ref_no: string;
  customer: Customer;
  metadata: {
    agent: { agentid: string };
    device: { init_channel: string };
    [key: string]: any;
  };
  payment_account: PaymentAccount;
  authenticators: Authenticator[];
}

export interface PayBillResponse {
  sourceid: string;
  customerid: string;
  billerid: string;
  biller_name: string;
  biller_category: string;
  billeraccountid: string;
  authenticators: Authenticator[];
  validationid: string;
  payment_amount: string;
  debit_amount: string;
  payment_type: string;
  source_ref_no: string;
  payment_reference: string;
  status: string; // SETTLED, FAILED, PENDING_RETRY, FAILED_DLQ, AMBIGUOUS_TIMEOUT
  payment_date: string;
}

export interface TransactionLog {
  id: string;
  trace_id: string;
  customer_id: string;
  biller_id: string;
  amount: number;
  transaction_state: string; // INITIALIZED, PENDING_SUBMISSION, NETWORK_IN_FLIGHT, AMBIGUOUS_TIMEOUT, SETTLED, FAILED, FAILED_DLQ
  request_payload: any;
  response_payload: any;
  retry_attempts: number;
  next_retry_at: string | null;
  worker_last_execution: string | null;
  reconciliation_version: number;
  created_at: string;
  updated_at: string;
}

export interface ReconciliationLog {
  id: string;
  trace_id: string;
  polling_attempts: number;
  resolved_state: string | null;
  reconciliation_status: string; // PENDING, RESOLVED, UNRESOLVED
  created_at: string;
}

export interface FavoriteBiller {
  billeraccountid: string;
  customer_id: string;
  biller_id: string;
  short_name: string;
  authenticators: Authenticator[];
  status: string; // ACTIVE, DELETED
  registration_date: string;
  deletion_date: string | null;
  autopay_status: string; // Y, N
  autopay_amount: number | null;
  frequency: string | null;
  payment_account: any;
}

export interface TelemetryMetric {
  name: string;
  value: any;
}

export interface TelemetryReport {
  total_requests: number;
  hmac_failures: number;
  replay_attacks: number;
  duplicate_payments: number;
  ambiguous_transactions: number;
  average_latency_ms: number;
  success_rate: number;
  reconciliation_recoveries: number;
  network_simulation_failures: number;
  retry_executions: number;
  reconciliation_failures: number;
  dlq_transitions: number;
  ambiguous_recovery_resolutions: number;
  
  // Worker latencies
  reconciliation_worker_latency_ms: number;
  ambiguous_state_worker_latency_ms: number;
  retry_worker_latency_ms: number;
  file_generation_worker_latency_ms: number;

  // Resilience metrics
  injected_failures: number;
  simulated_latency_durations_ms: number;
  timeout_counts: number;
  recovery_success_rate: number;
  unresolved_ambiguity_counts: number;
  downstream_degradation_events: number;
  retry_escalation_metrics: number;

  unauthorized_access_attempts?: number;
  jwt_validation_failures?: number;
  expired_token_usage?: number;
  dataset_download_audits?: number;

  metrics: TelemetryMetric[];
}
