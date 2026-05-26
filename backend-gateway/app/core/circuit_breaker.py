import asyncio
import time
from typing import Callable, Any, Optional
from loguru import logger

class CircuitBreakerOpenException(Exception):
    """Raised when the circuit breaker is OPEN and short-circuits requests."""
    pass

class CircuitBreaker:
    """
    Thread-safe and async-safe Circuit Breaker implementing the standard State Pattern:
    - CLOSED: Normal operations. Tracks consecutive failures.
    - OPEN: Short-circuits requests. Automatically transitions to HALF_OPEN after cooldown.
    - HALF_OPEN: Allows a single trial request. If successful, closes; otherwise, re-opens.
    """
    def __init__(
        self,
        name: str = "downstream-gateway",
        failure_threshold: int = 3,
        cooldown_seconds: float = 10.0
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        
        # State variables
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.failure_count = 0
        self.last_state_change = time.time()
        self.lock = asyncio.Lock()

        # Telemetry metrics
        self.total_trips = 0
        self.short_circuits = 0

    async def get_state(self) -> str:
        async with self.lock:
            await self._check_cooldown_expiry()
            return self.state

    async def _check_cooldown_expiry(self) -> None:
        """Helper to move from OPEN to HALF_OPEN if cooldown elapsed."""
        if self.state == "OPEN":
            elapsed = time.time() - self.last_state_change
            if elapsed >= self.cooldown_seconds:
                logger.info(f"Circuit Breaker '{self.name}' cooldown elapsed. Transitioning from OPEN -> HALF_OPEN.")
                self.state = "HALF_OPEN"
                self.last_state_change = time.time()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Executes the wrapped function inside the circuit breaker boundaries.
        """
        async with self.lock:
            await self._check_cooldown_expiry()

            if self.state == "OPEN":
                self.short_circuits += 1
                logger.warning(f"Circuit Breaker '{self.name}' is OPEN. Short-circuiting execution.")
                raise CircuitBreakerOpenException(f"Circuit Breaker '{self.name}' is OPEN. Request short-circuited.")

        try:
            # Execute execution block
            result = await func(*args, **kwargs)
            
            # If successful, reset failures
            async with self.lock:
                if self.state == "HALF_OPEN":
                    logger.info(f"Circuit Breaker '{self.name}' trial request succeeded. Transitioning HALF_OPEN -> CLOSED.")
                    self.state = "CLOSED"
                    self.failure_count = 0
                    self.last_state_change = time.time()
                elif self.state == "CLOSED":
                    self.failure_count = 0
            return result

        except Exception as e:
            # Handle failure
            async with self.lock:
                if self.state in ("CLOSED", "HALF_OPEN"):
                    self.failure_count += 1
                    logger.warning(f"Circuit Breaker '{self.name}' recorded failure #{self.failure_count}: {e}")
                    
                    if self.failure_count >= self.failure_threshold or self.state == "HALF_OPEN":
                        logger.error(f"Circuit Breaker '{self.name}' tripped. Transitioning to OPEN.")
                        self.state = "OPEN"
                        self.total_trips += 1
                        self.last_state_change = time.time()
            raise e

# Single global instance for downstream gateway calls
billing_circuit_breaker = CircuitBreaker(name="billing-downstream", failure_threshold=3, cooldown_seconds=8.0)
