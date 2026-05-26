from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database.models import TransactionLog, PaymentIdempotency, NonceRegistry, ReconciliationLog
from app.core.constants import TransactionState
from app.schemas.telemetry_schema import TelemetryReport, TelemetryMetric
from loguru import logger
import threading
import time

class TelemetryService:
    """
    Thread-safe engine to capture runtime metrics and compile audit logs.
    Combines in-memory counters (for validation failures/latencies)
    and live PostgreSQL database queries.
    """
    # In-memory metrics storage
    _lock = threading.Lock()
    _total_requests = 0
    _hmac_failures = 0
    _replay_attacks = 0
    _duplicate_payments = 0
    _network_simulation_failures = 0
    _retry_executions = 0
    _reconciliation_failures = 0
    _dlq_transitions = 0
    _ambiguous_recovery_resolutions = 0
    _reconciliation_worker_latency_ms = 0.0
    _ambiguous_state_worker_latency_ms = 0.0
    _retry_worker_latency_ms = 0.0
    _file_generation_worker_latency_ms = 0.0
    _total_latency = 0.0
    _latency_count = 0

    # Network Resilience & Chaos variables
    _injected_failures = 0
    _simulated_latency_durations_ms = 0.0
    _timeout_counts = 0
    _downstream_degradation_events = 0

    # Security audit counters — promoted from dynamic attributes to proper class-level state
    # so they are always present regardless of import order.
    _unauthorized_access_attempts = 0
    _jwt_validation_failures = 0
    _expired_token_usage = 0
    _dataset_download_audits = 0
    _nonces_total_checked = 0
    _rejected_duplicate_nonces = 0

    @classmethod
    def record_request(cls) -> None:
        with cls._lock:
            cls._total_requests += 1

    @classmethod
    def record_hmac_failure(cls) -> None:
        with cls._lock:
            cls._hmac_failures += 1

    @classmethod
    def record_replay_attack(cls) -> None:
        with cls._lock:
            cls._replay_attacks += 1

    @classmethod
    def record_duplicate_payment(cls) -> None:
        with cls._lock:
            cls._duplicate_payments += 1

    @classmethod
    def record_network_simulation_failure(cls) -> None:
        with cls._lock:
            cls._network_simulation_failures += 1

    @classmethod
    def record_retry_execution(cls) -> None:
        with cls._lock:
            cls._retry_executions += 1

    @classmethod
    def record_reconciliation_failure(cls) -> None:
        with cls._lock:
            cls._reconciliation_failures += 1

    @classmethod
    def record_dlq_transition(cls) -> None:
        with cls._lock:
            cls._dlq_transitions += 1

    @classmethod
    def record_ambiguous_recovery_resolution(cls) -> None:
        with cls._lock:
            cls._ambiguous_recovery_resolutions += 1

    @classmethod
    def record_worker_latency(cls, worker_name: str, duration_ms: float) -> None:
        with cls._lock:
            if worker_name == "reconciliation_worker":
                cls._reconciliation_worker_latency_ms = duration_ms
            elif worker_name == "ambiguous_state_worker":
                cls._ambiguous_state_worker_latency_ms = duration_ms
            elif worker_name == "retry_worker":
                cls._retry_worker_latency_ms = duration_ms
            elif worker_name == "file_generation_worker":
                cls._file_generation_worker_latency_ms = duration_ms

    @classmethod
    def record_latency(cls, duration_seconds: float) -> None:
        with cls._lock:
            cls._total_latency += (duration_seconds * 1000.0)  # convert to ms
            cls._latency_count += 1

    @classmethod
    def record_injected_failure(cls) -> None:
        with cls._lock:
            cls._injected_failures += 1

    @classmethod
    def record_simulated_latency(cls, duration_ms: float) -> None:
        with cls._lock:
            cls._simulated_latency_durations_ms += duration_ms

    @classmethod
    def record_timeout_count(cls) -> None:
        with cls._lock:
            cls._timeout_counts += 1

    @classmethod
    def record_downstream_degradation(cls) -> None:
        with cls._lock:
            cls._downstream_degradation_events += 1

    @classmethod
    def record_unauthorized_attempt(cls) -> None:
        """Increments the unauthorized access counter. Called on every security rejection."""
        with cls._lock:
            cls._unauthorized_access_attempts += 1

    @classmethod
    def record_jwt_failure(cls) -> None:
        with cls._lock:
            cls._jwt_validation_failures += 1

    @classmethod
    def record_expired_token(cls) -> None:
        with cls._lock:
            cls._expired_token_usage += 1

    @classmethod
    def record_download_audit(cls) -> None:
        with cls._lock:
            cls._dataset_download_audits += 1

    @classmethod
    def record_nonce_checked(cls) -> None:
        """Increments total nonces checked counter (every HMAC request that reaches nonce validation)."""
        with cls._lock:
            cls._nonces_total_checked += 1

    @classmethod
    def record_rejected_duplicate_nonce(cls) -> None:
        """Increments rejected duplicate nonce counter on replay attack detection."""
        with cls._lock:
            cls._rejected_duplicate_nonces += 1
            cls._replay_attacks += 1  # keep replay_attacks in sync

    @classmethod
    async def get_report(cls, session: AsyncSession) -> TelemetryReport:
        """
        Compiles the telemetry metrics report by aggregating local counters
        and querying the active PostgreSQL database state.
        """
        logger.info("Compiling telemetry metrics report...")
        
        # 1. Read live transactional aggregates from PostgreSQL
        stmt_total_tx = select(func.count(TransactionLog.id))
        res_total = await session.execute(stmt_total_tx)
        total_db_transactions = res_total.scalar() or 0

        # Count of Settled
        stmt_settled = select(func.count(TransactionLog.id)).filter_by(transaction_state=TransactionState.SETTLED)
        res_settled = await session.execute(stmt_settled)
        settled_count = res_settled.scalar() or 0

        # Count of Ambiguous
        stmt_ambiguous = select(func.count(TransactionLog.id)).filter_by(transaction_state=TransactionState.AMBIGUOUS_TIMEOUT)
        res_ambiguous = await session.execute(stmt_ambiguous)
        ambiguous_count = res_ambiguous.scalar() or 0

        # Count of Reconciled logs
        stmt_reconciled = select(func.count(ReconciliationLog.id)).filter_by(reconciliation_status="RESOLVED")
        res_reconciled = await session.execute(stmt_reconciled)
        reconciled_count = res_reconciled.scalar() or 0

        # Count of DLQ logs in database
        stmt_dlq = select(func.count(TransactionLog.id)).filter_by(transaction_state=TransactionState.FAILED_DLQ)
        res_dlq = await session.execute(stmt_dlq)
        dlq_count = res_dlq.scalar() or 0

        # Total reconciliation attempts
        stmt_recon_total = select(func.count(ReconciliationLog.id))
        res_recon_total = await session.execute(stmt_recon_total)
        recon_total = res_recon_total.scalar() or 0

        recovery_success_rate = (reconciled_count / recon_total * 100.0) if recon_total > 0 else 0.0

        # Transactions that escalated: retry_attempts > 1 OR state is FAILED_DLQ
        stmt_escalated = select(func.count(TransactionLog.id)).where(
            (TransactionLog.retry_attempts > 1) | (TransactionLog.transaction_state == TransactionState.FAILED_DLQ)
        )
        res_escalated = await session.execute(stmt_escalated)
        escalated_count = res_escalated.scalar() or 0

        # 2. Compute safety statistics
        with cls._lock:
            local_total = cls._total_requests
            hmac_fail = cls._hmac_failures
            replay = cls._replay_attacks
            dup_pay = cls._duplicate_payments
            net_fail = cls._network_simulation_failures
            retries = cls._retry_executions
            recon_fail = cls._reconciliation_failures
            dlq_trans = cls._dlq_transitions
            ambig_resolutions = cls._ambiguous_recovery_resolutions
            recon_lat = cls._reconciliation_worker_latency_ms
            ambig_lat = cls._ambiguous_state_worker_latency_ms
            retry_lat = cls._retry_worker_latency_ms
            file_lat = cls._file_generation_worker_latency_ms
            avg_lat = (cls._total_latency / cls._latency_count) if cls._latency_count > 0 else 0.0
            
            inj_failures = cls._injected_failures
            sim_lat = cls._simulated_latency_durations_ms
            timeout_cnt = cls._timeout_counts
            degrad_cnt = cls._downstream_degradation_events

            # Security Audits — now read from proper class-level attributes
            unauth_attempts = cls._unauthorized_access_attempts
            jwt_validation_fails = cls._jwt_validation_failures
            expired_tokens = cls._expired_token_usage
            downloads_audited = cls._dataset_download_audits
            nonces_checked = cls._nonces_total_checked
            rejected_nonces = cls._rejected_duplicate_nonces

        success_rate = (settled_count / total_db_transactions * 100.0) if total_db_transactions > 0 else 0.0

        report = TelemetryReport(
            total_requests=local_total,
            hmac_failures=hmac_fail,
            replay_attacks=replay,
            duplicate_payments=dup_pay,
            ambiguous_transactions=ambiguous_count,
            average_latency_ms=round(avg_lat, 2),
            success_rate=round(success_rate, 2),
            reconciliation_recoveries=reconciled_count,
            network_simulation_failures=net_fail,
            retry_executions=retries,
            reconciliation_failures=recon_fail,
            dlq_transitions=dlq_count, # Use DB value
            ambiguous_recovery_resolutions=ambig_resolutions,
            reconciliation_worker_latency_ms=round(recon_lat, 2),
            ambiguous_state_worker_latency_ms=round(ambig_lat, 2),
            retry_worker_latency_ms=round(retry_lat, 2),
            file_generation_worker_latency_ms=round(file_lat, 2),
            
            # Resilience metrics
            injected_failures=inj_failures,
            simulated_latency_durations_ms=round(sim_lat, 2),
            timeout_counts=timeout_cnt,
            recovery_success_rate=round(recovery_success_rate, 2),
            unresolved_ambiguity_counts=ambiguous_count,
            downstream_degradation_events=degrad_cnt,
            retry_escalation_metrics=escalated_count,
            
            # Security Audits
            unauthorized_access_attempts=unauth_attempts,
            jwt_validation_failures=jwt_validation_fails,
            expired_token_usage=expired_tokens,
            dataset_download_audits=downloads_audited,
            metrics=[
                TelemetryMetric(name="Total_Database_Transactions", value=total_db_transactions),
                TelemetryMetric(name="Settled_Payments_Count", value=settled_count),
                TelemetryMetric(name="Ambiguous_Payments_Count", value=ambiguous_count),
                TelemetryMetric(name="Reconciliation_Recoveries_Count", value=reconciled_count),
                TelemetryMetric(name="Network_Simulation_Failures_Count", value=net_fail),
                TelemetryMetric(name="Retry_Executions_Count", value=retries),
                TelemetryMetric(name="Reconciliation_Failures_Count", value=recon_fail),
                TelemetryMetric(name="DLQ_Transitions_Count", value=dlq_count),
                TelemetryMetric(name="Ambiguous_Recovery_Resolutions", value=ambig_resolutions),
                TelemetryMetric(name="Reconciliation_Worker_Latency_Ms", value=round(recon_lat, 2)),
                TelemetryMetric(name="Ambiguous_State_Worker_Latency_Ms", value=round(ambig_lat, 2)),
                TelemetryMetric(name="Retry_Worker_Latency_Ms", value=round(retry_lat, 2)),
                TelemetryMetric(name="File_Generation_Worker_Latency_Ms", value=round(file_lat, 2)),
                TelemetryMetric(name="Injected_Failures", value=inj_failures),
                TelemetryMetric(name="Simulated_Latency_Durations_Ms", value=round(sim_lat, 2)),
                TelemetryMetric(name="Timeout_Counts", value=timeout_cnt),
                TelemetryMetric(name="Recovery_Success_Rate", value=round(recovery_success_rate, 2)),
                TelemetryMetric(name="Unresolved_Ambiguity_Counts", value=ambiguous_count),
                TelemetryMetric(name="Downstream_Degradation_Events", value=degrad_cnt),
                TelemetryMetric(name="Retry_Escalation_Metrics", value=escalated_count)
            ]
        )
        
        logger.info("Telemetry report compiled successfully.")
        return report
