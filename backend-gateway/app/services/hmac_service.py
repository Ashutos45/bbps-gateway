from app.core.config import settings
from app.core.nonce_cache import nonce_cache
from app.core.timestamp_validator import validate_request_timestamp
from app.core.security import verify_request_signature, sign_response_body
from app.core.exceptions import HMACVerificationError, ReplayAttackError, InvalidChannelError
from app.services.telemetry_service import TelemetryService
from loguru import logger

class HMACService:
    """
    Service layer coordinator for security operations.
    Handles HMAC validation for requests and signature generation for responses.
    """
    
    @staticmethod
    def verify_incoming_request(
        raw_body_bytes: bytes,
        timestamp: str,
        nonce: str,
        signature: str,
        source_id: str
    ) -> None:
        """
        Orchestrates request validation:
        1. Validates the source_id/channel channel exists.
        2. Validates timestamp freshness (prevents timing attacks).
        3. Audits the nonce (prevents replay attacks).
        4. Verifies the cryptographic HMAC signature.
        5. Registers the nonce on success.
        """
        # 1. Resolve channel settings
        try:
            chan_config = settings.get_channel_config(source_id)
            client_secret = chan_config["client_secret"]
        except ValueError as e:
            logger.error(f"Channel resolution failed: {e}")
            raise InvalidChannelError(source_id)

        # 2. Validate timestamp
        validate_request_timestamp(timestamp)

        # 3. Check for replay attack — record total nonces checked before the test
        TelemetryService.record_nonce_checked()
        if nonce_cache.is_nonce_used(nonce):
            logger.warning(f"Replay attack detected. Nonce '{nonce}' has already been used.")
            raise ReplayAttackError(f"Replay attack detected. Nonce '{nonce}' has already been used.")

        # 4. Verify signature
        is_valid = verify_request_signature(
            raw_body_bytes=raw_body_bytes,
            timestamp=timestamp,
            nonce=nonce,
            signature=signature,
            secret_key=client_secret
        )
        if not is_valid:
            logger.warning("HMAC signature verification failed.")
            raise HMACVerificationError("HMAC signature verification failed. Payload may be tampered or credentials invalid.")

        # 5. Add to nonce cache on successful authentication
        nonce_cache.add_nonce(nonce)
        logger.info(f"Successfully authenticated request for source '{source_id}' with nonce '{nonce}'")

    @staticmethod
    def generate_response_signature(
        response_body_bytes: bytes,
        source_id: str
    ) -> str:
        """
        Generates the X-Response-Signature header for a response body.
        """
        try:
            chan_config = settings.get_channel_config(source_id)
            client_secret = chan_config["client_secret"]
        except ValueError as e:
            logger.error(f"Channel resolution failed: {e}")
            # Fallback to a default key if the channel is unknown (e.g. error responses)
            client_secret = settings.MBANKING_CLIENT_SECRET

        return sign_response_body(response_body_bytes, client_secret)
