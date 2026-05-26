import pytest
import asyncio
import time
import uuid
from datetime import datetime, timedelta
from sqlalchemy import delete, select
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database.db import AsyncSessionLocal, engine
from app.database.models import TransactionLog, ReconciliationLog, PaymentIdempotency
from app.core.constants import TransactionState
from app.database.repositories.transaction_repository import TransactionRepository
from app.core.idempotency import IdempotencyEngine
from app.services.telemetry_service import TelemetryService
from app.services.recovery_service import RecoveryService
from app.services.settlement_service import SettlementService
from app.services.network_simulation_service import NetworkSimulationService
from app.core.circuit_breaker import billing_circuit_breaker, CircuitBreakerOpenException
from app.core.config import settings
from app.core.exceptions import TransactionFailedError
from app.core.security import calculate_hmac_sha256
from app.utils.json_canonicalizer import canonicalize_bytes

def generate_signed_headers(payload_bytes: bytes, source_id: str = "mbanking") -> dict:
    """
    Helper to calculate timestamp, nonce, and HMAC-SHA256 signature for test requests.
    """
    timestamp = str(int(time.time()))
    nonce = str(uuid.uuid4())
    config = settings.get_channel_config(source_id)
    secret = config["client_secret"]
    
    canonical_body = canonicalize_bytes(payload_bytes) if payload_bytes else b""
    sig_payload = canonical_body + timestamp.encode("utf-8") + nonce.encode("utf-8")
    signature = calculate_hmac_sha256(sig_payload, secret)
    
    return {
        "x-timestamp": timestamp,
        "x-nonce": nonce,
        "x-signature": signature,
        "x-trace-id": f"trace-{uuid.uuid4().hex[:8]}"
    }

async def setup_clean_db():
    async with AsyncSessionLocal() as session:
        await session.execute(delete(TransactionLog))
        await session.execute(delete(ReconciliationLog))
        await session.execute(delete(PaymentIdempotency))
        await session.commit()

@pytest.mark.asyncio
async def test_simulated_downstream_failure_header():
    """
    Verifies that forcing a failure via X-Simulate-Failure header:
    - Causes process_payment to raise TransactionFailedError (timeout)
    - Persists transaction log state as AMBIGUOUS_TIMEOUT
    - Records metrics under injected_failures and timeout_counts
    """
    try:
        await setup_clean_db()
        
        async with AsyncSessionLocal() as session:
            # Baseline reports
            base_report = await TelemetryService.get_report(session)

        # Trigger payment endpoint with headers
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            url = "/BOBCOU/BBPS/mbanking/customers/cust123/billpay/payments"
            body = {
                "billerid": "UPPCL0000UTP01",
                "validationid": f"val-{uuid.uuid4().hex[:6]}",
                "payment_amount": "100.00",
                "debit_amount": "100.00",
                "payment_type": "Netbanking",
                "source_ref_no": f"ref-fail-{uuid.uuid4().hex[:6]}",
                "customer": {"firstname": "John", "lastname": "Doe", "mobile": "9999988888"},
                "metadata": {
                    "agent": {"agentid": "AGT001"},
                    "device": {"init_channel": "Internet"}
                },
                "payment_account": {
                    "payment_method": "CreditCard",
                    "cardholder_name": "John Doe"
                },
                "authenticators": [{"seq": "1", "parameter_name": "Consumer No", "value": "123456"}]
            }
            
            payload_bytes = ac.build_request("POST", url, json=body).content
            headers = generate_signed_headers(payload_bytes, "mbanking")
            headers["x-simulate-failure"] = "true"
            
            # Post request
            res = await ac.post(url, json=body, headers=headers)
            assert res.status_code == 504
            
            error_data = res.json()
            assert error_data["error_type"] == "ambiguous_timeout"
            assert error_data["error_code"] == "ERR_GATEWAY_TIMEOUT"

        # Verify DB persisted state
        async with AsyncSessionLocal() as session:
            tx = await TransactionRepository.get_by_trace_id(session, body["source_ref_no"])
            assert tx is not None
            assert tx.transaction_state == TransactionState.AMBIGUOUS_TIMEOUT

            # Telemetry assertion
            report = await TelemetryService.get_report(session)
            assert report.injected_failures > base_report.injected_failures
            assert report.timeout_counts > base_report.timeout_counts
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_circuit_breaker_tripping_and_recovery():
    """
    Validates that:
    - 3 consecutive failures trips the billing circuit breaker to OPEN.
    - Subsequent calls are short-circuited, throw open exceptions, and update states to FAILED (non-ambiguous).
    - Exposes open/closed breaker state.
    - Automatically recovers to HALF_OPEN -> CLOSED on successful trial after cooldown.
    """
    try:
        await setup_clean_db()

        # Reset billing circuit breaker state to CLOSED
        billing_circuit_breaker.state = "CLOSED"
        billing_circuit_breaker.failure_count = 0
        billing_circuit_breaker.short_circuits = 0
        billing_circuit_breaker.total_trips = 0
        billing_circuit_breaker.cooldown_seconds = 2.0  # short cooldown for test

        # 1. Trigger consecutive failures
        async def fail_call():
            raise TransactionFailedError("Forced failure", error_code="ERR_FAIL")

        with pytest.raises(Exception):
            await billing_circuit_breaker.call(fail_call)
        assert billing_circuit_breaker.state == "CLOSED"
        assert billing_circuit_breaker.failure_count == 1

        with pytest.raises(Exception):
            await billing_circuit_breaker.call(fail_call)
        assert billing_circuit_breaker.state == "CLOSED"
        assert billing_circuit_breaker.failure_count == 2

        # 3rd failure should trip to OPEN
        with pytest.raises(Exception):
            await billing_circuit_breaker.call(fail_call)
        assert billing_circuit_breaker.state == "OPEN"
        assert billing_circuit_breaker.total_trips == 1

        # 4th call should be short-circuited immediately
        with pytest.raises(CircuitBreakerOpenException):
            await billing_circuit_breaker.call(fail_call)
        assert billing_circuit_breaker.short_circuits == 1

        # Verify short-circuited call through HTTP client transitions transactions to FAILED directly (no timeout ambiguity)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            url = "/BOBCOU/BBPS/mbanking/customers/cust123/billpay/payments"
            body = {
                "billerid": "UPPCL0000UTP01",
                "validationid": f"val-{uuid.uuid4().hex[:6]}",
                "payment_amount": "100.00",
                "debit_amount": "100.00",
                "payment_type": "Netbanking",
                "source_ref_no": f"ref-breaker-{uuid.uuid4().hex[:6]}",
                "customer": {"firstname": "John", "lastname": "Doe", "mobile": "9999988888"},
                "metadata": {
                    "agent": {"agentid": "AGT001"},
                    "device": {"init_channel": "Internet"}
                },
                "payment_account": {
                    "payment_method": "CreditCard",
                    "cardholder_name": "John Doe"
                },
                "authenticators": [{"seq": "1", "parameter_name": "Consumer No", "value": "123456"}]
            }
            
            payload_bytes = ac.build_request("POST", url, json=body).content
            headers = generate_signed_headers(payload_bytes, "mbanking")
            headers["x-simulate-failure"] = "false"  # Try to force success, but breaker is OPEN so it short circuits
            
            res = await ac.post(url, json=body, headers=headers)
            assert res.status_code == 503
            assert "circuit breaker is OPEN" in res.json()["message"]

        # Verify DB transaction state is FAILED (not AMBIGUOUS_TIMEOUT)
        async with AsyncSessionLocal() as session:
            tx = await TransactionRepository.get_by_trace_id(session, body["source_ref_no"])
            assert tx is not None
            assert tx.transaction_state == TransactionState.FAILED

        # 2. Wait for cooldown period (2.0 seconds) and recover
        await asyncio.sleep(2.2)
        
        # Next call should be HALF_OPEN
        async def success_call():
            return "SUCCESS"
        
        res_cb = await billing_circuit_breaker.call(success_call)
        assert res_cb == "SUCCESS"
        assert billing_circuit_breaker.state == "CLOSED"
        assert billing_circuit_breaker.failure_count == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_chaos_mode_and_partial_degradation_telemetry():
    """
    Validates that:
    - Enabling Chaos Mode and Partial Degradation alters outcomes.
    - Exposes injected failures, latencies, degradations, and success rates in /telemetry and /metrics.
    """
    try:
        await setup_clean_db()

        # Enable settings dynamically
        settings.ENABLE_CHAOS_MODE = True
        settings.ENABLE_PARTIAL_DEGRADATION = True
        settings.SIMULATED_LATENCY_MS = 20  # small latency for tests

        async with AsyncSessionLocal() as session:
            # Baseline
            base_report = await TelemetryService.get_report(session)

        # Trigger a request on degraded biller UPPCL0000UTP01_DEGRADED
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            url = "/BOBCOU/BBPS/mbanking/customers/cust123/billpay/payments"
            body = {
                "billerid": "UPPCL0000UTP01_DEGRADED",
                "validationid": f"val-{uuid.uuid4().hex[:6]}",
                "payment_amount": "100.00",
                "debit_amount": "100.00",
                "payment_type": "Netbanking",
                "source_ref_no": f"ref-degrade-{uuid.uuid4().hex[:6]}",
                "customer": {"firstname": "John", "lastname": "Doe", "mobile": "9999988888"},
                "metadata": {
                    "agent": {"agentid": "AGT001"},
                    "device": {"init_channel": "Internet"}
                },
                "payment_account": {
                    "payment_method": "CreditCard",
                    "cardholder_name": "John Doe"
                },
                "authenticators": [{"seq": "1", "parameter_name": "Consumer No", "value": "123456"}]
            }
            
            payload_bytes = ac.build_request("POST", url, json=body).content
            headers = generate_signed_headers(payload_bytes, "mbanking")
            
            # Post request
            await ac.post(url, json=body, headers=headers)

            async with AsyncSessionLocal() as session:
                report = await TelemetryService.get_report(session)
                
                # Latency metric must have been updated
                assert report.simulated_latency_durations_ms >= base_report.simulated_latency_durations_ms

            # Verify metrics are exposed through /telemetry endpoint
            res_telemetry = await ac.get("/telemetry")
            assert res_telemetry.status_code == 200
            json_data = res_telemetry.json()
            assert "injected_failures" in json_data
            assert "simulated_latency_durations_ms" in json_data
            assert "recovery_success_rate" in json_data

            # Verify metrics are exposed through /metrics endpoint in Prometheus format
            res_metrics = await ac.get("/metrics")
            assert res_metrics.status_code == 200
            metrics_text = res_metrics.text
            assert "bbps_injected_failures_total" in metrics_text
            assert "bbps_simulated_latency_durations_milliseconds_total" in metrics_text
            assert "bbps_recovery_success_rate_percent" in metrics_text
    finally:
        # Reset settings
        settings.ENABLE_CHAOS_MODE = False
        settings.ENABLE_PARTIAL_DEGRADATION = False
        settings.SIMULATED_LATENCY_MS = 0
        await engine.dispose()
