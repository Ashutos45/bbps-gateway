import asyncio
import random
import time
from typing import Optional
from app.core.config import settings
from app.services.telemetry_service import TelemetryService
from app.core.exceptions import TransactionFailedError
from app.core.circuit_breaker import billing_circuit_breaker, CircuitBreakerOpenException
from loguru import logger

class NetworkSimulationService:
    """
    Production-grade Network Simulation & Resilience Service.
    Simulates latency, randomized drops, partial API degradation, temporary outages,
    and integrates with the billing circuit breaker.
    """

    @classmethod
    async def simulate_latency(cls, x_simulate_failure_header: Optional[str] = None) -> float:
        """
        Simulates downstream latency, incorporating randomized jitter under Chaos Mode.
        """
        # Bypass latency if forced success is specified
        if x_simulate_failure_header == "false":
            return 0.0

        latency_ms = float(settings.SIMULATED_LATENCY_MS)

        # Chaos mode: vary latency with randomized jitter between 50% and 200% of base
        if settings.ENABLE_CHAOS_MODE:
            jitter_factor = random.uniform(0.5, 2.0)
            latency_ms = latency_ms * jitter_factor

        if latency_ms > 0:
            logger.info(f"Injecting simulated downstream latency of {latency_ms:.2f} ms")
            TelemetryService.record_simulated_latency(latency_ms)
            await asyncio.sleep(latency_ms / 1000.0)

        return latency_ms

    @classmethod
    def should_fail(
        cls,
        x_simulate_failure_header: Optional[str] = None,
        request_path: Optional[str] = None,
        biller_id: Optional[str] = None
    ) -> bool:
        """
        Determines whether the request should fail based on configured failure rates,
        forced simulation headers, partial degradation, outages, or chaos mode.
        """
        # 1. Controlled forced failures via header
        if x_simulate_failure_header is not None:
            header_clean = x_simulate_failure_header.strip().lower()
            if header_clean == "true":
                logger.info("Forcing failure via X-Simulate-Failure header.")
                TelemetryService.record_injected_failure()
                return True
            elif header_clean == "false":
                logger.info("Bypassing failure simulation via X-Simulate-Failure header.")
                return False

        # 2. Temporary Upstream Outage (simulated window: e.g. 5 seconds of outage every 30 seconds)
        if settings.ENABLE_CHAOS_MODE:
            current_sec = int(time.time()) % 30
            if current_sec < 5:
                logger.warning("Simulating temporary upstream outage window (5s outage every 30s).")
                TelemetryService.record_injected_failure()
                return True

        # 3. Partial API Degradation
        if settings.ENABLE_PARTIAL_DEGRADATION and biller_id:
            # Degrade specific billers (e.g. any biller containing 'DEGRADED' or specifically UPPCL0000UTP01 under stress)
            if "degraded" in biller_id.lower() or biller_id == "UPPCL0000UTP01_DEGRADED":
                # 60% failure rate for degraded services
                if random.random() < 0.60:
                    logger.warning(f"Simulating partial service degradation for biller: '{biller_id}' (60% drop rate).")
                    TelemetryService.record_downstream_degradation()
                    TelemetryService.record_injected_failure()
                    return True

        # 4. Chaos Mode Randomized drop rate (dynamically scales failure rate)
        if settings.ENABLE_CHAOS_MODE:
            # dynamic failure rate between 10% and 60%
            chaos_failure_rate = random.uniform(0.10, 0.60)
            if random.random() < chaos_failure_rate:
                logger.warning(f"Simulating chaos mode random request drop (Dynamic rate: {chaos_failure_rate:.2f}).")
                TelemetryService.record_injected_failure()
                return True

        # 5. Default failure rate check
        failure_rate = float(settings.SIMULATED_FAILURE_RATE)
        if failure_rate > 0.0 and random.random() < failure_rate:
            logger.warning(f"Simulating default request drop (Rate: {failure_rate:.2f}).")
            TelemetryService.record_injected_failure()
            return True

        return False

    @classmethod
    async def apply_resilience_boundaries(
        cls,
        x_simulate_failure_header: Optional[str] = None,
        request_path: Optional[str] = None,
        biller_id: Optional[str] = None
    ) -> None:
        """
        Applies circuit breaker boundaries, simulates latency, checks for failure injection,
        and raises appropriate exceptions (simulating timeouts or general server outages).
        """
        # 1. Check Circuit Breaker state first (can raise CircuitBreakerOpenException)
        # We wrap the downstream execution check. In this simulation, we check the state.
        state = await billing_circuit_breaker.get_state()
        if state == "OPEN":
            # Circuit breaker short circuits directly
            raise CircuitBreakerOpenException("Circuit Breaker is OPEN. Short-circuiting request.")

        # 2. Inject latency
        await cls.simulate_latency(x_simulate_failure_header)

        # 3. Check for injected failures
        if cls.should_fail(x_simulate_failure_header, request_path, biller_id):
            # If header is explicitly "true", always raise a timeout (504). Otherwise randomly raise 504 vs 503.
            is_timeout = True if (x_simulate_failure_header and x_simulate_failure_header.strip().lower() == "true") else (random.random() < 0.50)
            
            # Let the circuit breaker record the failure
            async def force_fail():
                if is_timeout:
                    TelemetryService.record_timeout_count()
                    raise TransactionFailedError(
                        message="Downstream COU Gateway Timeout. Transaction status is ambiguous.",
                        status_code=504,
                        error_code="ERR_GATEWAY_TIMEOUT",
                        error_type="ambiguous_timeout"
                    )
                else:
                    raise TransactionFailedError(
                        message="Downstream billing server is temporarily unavailable.",
                        status_code=503,
                        error_code="ERR_DOWNSTREAM_UNAVAILABLE",
                        error_type="service_unavailable"
                    )

            try:
                # Wrap the forced failure in circuit breaker to count consecutive failures
                await billing_circuit_breaker.call(force_fail)
            except Exception as e:
                # Re-raise to trigger payment service timeout handling
                raise e

        # If call succeeds without failure, record success inside circuit breaker
        async def force_success():
            return True
        await billing_circuit_breaker.call(force_success)
