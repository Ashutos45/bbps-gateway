import time
from typing import Set, Dict
from loguru import logger

class NonceCache:
    """
    In-memory cache to store used nonces during Phase 2.
    Nonces are checked and stored to prevent replay attacks.
    Nonces older than 300 seconds are automatically expired to conserve memory.
    """
    def __init__(self, expiry_window_seconds: int = 300):
        self.expiry_window_seconds = expiry_window_seconds
        # Maps nonce -> time at which it was cached
        self._cache: Dict[str, float] = {}

    def is_nonce_used(self, nonce: str) -> bool:
        """
        Checks if the nonce has already been registered in the cache.
        """
        self._cleanup()
        return nonce in self._cache

    def add_nonce(self, nonce: str) -> None:
        """
        Registers a nonce in the cache with the current timestamp.
        """
        self._cache[nonce] = time.time()
        logger.debug(f"Nonce registered in cache: {nonce}")

    def _cleanup(self) -> None:
        """
        Removes nonces that have exceeded the 300-second validation window.
        """
        current_time = time.time()
        expired_keys = [
            nonce for nonce, cached_time in self._cache.items()
            if current_time - cached_time > self.expiry_window_seconds
        ]
        for key in expired_keys:
            del self._cache[key]
            
        if expired_keys:
            logger.debug(f"Expired {len(expired_keys)} nonces from cache.")

# Global instance for Phase 2
nonce_cache = NonceCache()
