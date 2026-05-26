from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class TelemetryMetric(BaseModel):
    name: str
    value: Any

class TelemetryReport(BaseModel):
    total_requests: int = Field(0, description="Total requests processed by gateway")
    hmac_failures: int = Field(0, description="Number of HMAC signature validation failures")
    replay_attacks: int = Field(0, description="Number of duplicate nonce/replay attacks blocked")
    duplicate_payments: int = Field(0, description="Number of concurrent/duplicate payment requests blocked")
    ambiguous_transactions: int = Field(0, description="Number of transactions that timed out or entered ambiguous state")
    average_latency_ms: float = Field(0.0, description="Average response latency in milliseconds")
    success_rate: float = Field(0.0, description="Percentage of successful payment settlements")
    reconciliation_recoveries: int = Field(0, description="Number of resolved ambiguous transactions")
    network_simulation_failures: int = Field(0, description="Number of simulated network failure timeouts")
    
    # Retry & Recovery worker metrics
    retry_executions: int = Field(0, description="Number of transaction retry attempts executed")
    reconciliation_failures: int = Field(0, description="Number of failed background reconciliation loops")
    dlq_transitions: int = Field(0, description="Number of transactions transitioned to Dead-Letter state")
    ambiguous_recovery_resolutions: int = Field(0, description="Number of recovery resolutions of ambiguous timeouts")
    
    # Worker latencies
    reconciliation_worker_latency_ms: float = Field(0.0, description="Last execution latency of reconciliation worker in ms")
    ambiguous_state_worker_latency_ms: float = Field(0.0, description="Last execution latency of ambiguous state worker in ms")
    retry_worker_latency_ms: float = Field(0.0, description="Last execution latency of retry worker in ms")
    file_generation_worker_latency_ms: float = Field(0.0, description="Last execution latency of file generation worker in ms")

    # Network Resilience & Chaos simulation telemetry
    injected_failures: int = Field(0, description="Total simulated downstream failures injected")
    simulated_latency_durations_ms: float = Field(0.0, description="Total simulated latency durations injected in ms")
    timeout_counts: int = Field(0, description="Total simulated downstream timeout drop counts")
    recovery_success_rate: float = Field(0.0, description="Percentage of successfully resolved ambiguities over total recoveries")
    unresolved_ambiguity_counts: int = Field(0, description="Total transactions currently in unresolved AMBIGUOUS_TIMEOUT state")
    downstream_degradation_events: int = Field(0, description="Total simulated downstream partial degradation events")
    retry_escalation_metrics: int = Field(0, description="Total retries that escalated (more than 1 retry attempt or sent to DLQ)")

    # Security Audits
    unauthorized_access_attempts: int = Field(0, description="Total unauthorized access attempts intercepted")
    jwt_validation_failures: int = Field(0, description="Total JWT validation failures detected")
    expired_token_usage: int = Field(0, description="Total expired signed download token access attempts")
    dataset_download_audits: int = Field(0, description="Total authenticated dataset downloads audited")

    metrics: List[TelemetryMetric] = Field(default_factory=list)


