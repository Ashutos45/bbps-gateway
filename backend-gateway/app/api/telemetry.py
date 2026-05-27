from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.db import get_db
from app.schemas.telemetry_schema import TelemetryReport
from app.services.telemetry_service import TelemetryService
from app.auth.auth_middleware import require_roles
from app.auth.role_manager import Role
from loguru import logger

router = APIRouter()

@router.get(
    "/telemetry",
    response_model=TelemetryReport,
    tags=["Telemetry"]
)
async def get_telemetry(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_roles([Role.ADMIN]))
):
    """
    Exposes system telemetry metrics and transactional health aggregates in JSON format.
    """
    logger.info("Handling Telemetry JSON report request")
    report = await TelemetryService.get_report(db)
    return report

@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    tags=["Telemetry"]
)
async def get_prometheus_metrics(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_roles([Role.ADMIN]))
):
    """
    Exposes system telemetry formatted in Prometheus text exposition format.
    """
    logger.info("Handling Prometheus metrics text request")
    report = await TelemetryService.get_report(db)
    
    # Format as Prometheus-compatible plain text
    lines = [
        "# HELP bbps_requests_total Total requests processed by the BBPS gateway",
        "# TYPE bbps_requests_total counter",
        f"bbps_requests_total {report.total_requests}",
        "",
        "# HELP bbps_hmac_failures_total Total HMAC validation failures detected",
        "# TYPE bbps_hmac_failures_total counter",
        f"bbps_hmac_failures_total {report.hmac_failures}",
        "",
        "# HELP bbps_replay_attacks_total Replay attacks intercepted by the nonce registry",
        "# TYPE bbps_replay_attacks_total counter",
        f"bbps_replay_attacks_total {report.replay_attacks}",
        "",
        "# HELP bbps_duplicate_payments_total Blocked concurrent or duplicate payment request attempts",
        "# TYPE bbps_duplicate_payments_total counter",
        f"bbps_duplicate_payments_total {report.duplicate_payments}",
        "",
        "# HELP bbps_ambiguous_transactions_total Transactions currently stuck in ambiguous state",
        "# TYPE bbps_ambiguous_transactions_total counter",
        f"bbps_ambiguous_transactions_total {report.ambiguous_transactions}",
        "",
        "# HELP bbps_average_latency_milliseconds Average request latency in milliseconds",
        "# TYPE bbps_average_latency_milliseconds gauge",
        f"bbps_average_latency_milliseconds {report.average_latency_ms}",
        "",
        "# HELP bbps_success_rate_percent Percentage of database transactions successfully settled",
        "# TYPE bbps_success_rate_percent gauge",
        f"bbps_success_rate_percent {report.success_rate}",
        "",
        "# HELP bbps_reconciliation_recoveries_total Total transactions resolved by reconciliation worker",
        "# TYPE bbps_reconciliation_recoveries_total counter",
        f"bbps_reconciliation_recoveries_total {report.reconciliation_recoveries}",
        "",
        "# HELP bbps_network_simulation_failures_total Total simulated network timeouts",
        "# TYPE bbps_network_simulation_failures_total counter",
        f"bbps_network_simulation_failures_total {report.network_simulation_failures}",
        "",
        "# HELP bbps_retry_executions_total Total transaction retry attempts executed",
        "# TYPE bbps_retry_executions_total counter",
        f"bbps_retry_executions_total {report.retry_executions}",
        "",
        "# HELP bbps_reconciliation_failures_total Total failed background reconciliation loops",
        "# TYPE bbps_reconciliation_failures_total counter",
        f"bbps_reconciliation_failures_total {report.reconciliation_failures}",
        "",
        "# HELP bbps_dlq_transitions_total Total transactions transitioned to Dead-Letter state",
        "# TYPE bbps_dlq_transitions_total counter",
        f"bbps_dlq_transitions_total {report.dlq_transitions}",
        "",
        "# HELP bbps_ambiguous_recovery_resolutions_total Total recovery resolutions of ambiguous timeouts",
        "# TYPE bbps_ambiguous_recovery_resolutions_total counter",
        f"bbps_ambiguous_recovery_resolutions_total {report.ambiguous_recovery_resolutions}",
        "",
        "# HELP bbps_reconciliation_worker_latency_milliseconds Last execution latency of reconciliation worker in ms",
        "# TYPE bbps_reconciliation_worker_latency_milliseconds gauge",
        f"bbps_reconciliation_worker_latency_milliseconds {report.reconciliation_worker_latency_ms}",
        "",
        "# HELP bbps_ambiguous_state_worker_latency_milliseconds Last execution latency of ambiguous state worker in ms",
        "# TYPE bbps_ambiguous_state_worker_latency_milliseconds gauge",
        f"bbps_ambiguous_state_worker_latency_milliseconds {report.ambiguous_state_worker_latency_ms}",
        "",
        "# HELP bbps_retry_worker_latency_milliseconds Last execution latency of retry worker in ms",
        "# TYPE bbps_retry_worker_latency_milliseconds gauge",
        f"bbps_retry_worker_latency_milliseconds {report.retry_worker_latency_ms}",
        "",
        "# HELP bbps_file_generation_worker_latency_milliseconds Last execution latency of file generation worker in ms",
        "# TYPE bbps_file_generation_worker_latency_milliseconds gauge",
        f"bbps_file_generation_worker_latency_milliseconds {report.file_generation_worker_latency_ms}",
        "",
        "# HELP bbps_injected_failures_total Total simulated downstream failures injected",
        "# TYPE bbps_injected_failures_total counter",
        f"bbps_injected_failures_total {report.injected_failures}",
        "",
        "# HELP bbps_simulated_latency_durations_milliseconds_total Total simulated latency durations injected in ms",
        "# TYPE bbps_simulated_latency_durations_milliseconds_total counter",
        f"bbps_simulated_latency_durations_milliseconds_total {report.simulated_latency_durations_ms}",
        "",
        "# HELP bbps_timeout_counts_total Total simulated downstream timeout drop counts",
        "# TYPE bbps_timeout_counts_total counter",
        f"bbps_timeout_counts_total {report.timeout_counts}",
        "",
        "# HELP bbps_recovery_success_rate_percent Percentage of successfully resolved ambiguities over total recoveries",
        "# TYPE bbps_recovery_success_rate_percent gauge",
        f"bbps_recovery_success_rate_percent {report.recovery_success_rate}",
        "",
        "# HELP bbps_unresolved_ambiguity_counts Total transactions currently in unresolved AMBIGUOUS_TIMEOUT state",
        "# TYPE bbps_unresolved_ambiguity_counts gauge",
        f"bbps_unresolved_ambiguity_counts {report.unresolved_ambiguity_counts}",
        "",
        "# HELP bbps_downstream_degradation_events_total Total simulated downstream partial degradation events",
        "# TYPE bbps_downstream_degradation_events_total counter",
        f"bbps_downstream_degradation_events_total {report.downstream_degradation_events}",
        "",
        "# HELP bbps_retry_escalation_metrics_total Total retries that escalated",
        "# TYPE bbps_retry_escalation_metrics_total counter",
        f"bbps_retry_escalation_metrics_total {report.retry_escalation_metrics}"
    ]
    
    # Append custom submetrics
    for metric in report.metrics:
        name_clean = metric.name.lower()
        lines.extend([
            "",
            f"# HELP bbps_db_{name_clean} Live db transaction count metric: {metric.name}",
            f"# TYPE bbps_db_{name_clean} gauge",
            f"bbps_db_{name_clean} {metric.value}"
        ])

    return "\n".join(lines) + "\n"
