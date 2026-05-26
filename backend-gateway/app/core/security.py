import hmac
import hashlib
from typing import Union
from loguru import logger

def calculate_hmac_sha256(payload: bytes, secret_key: str) -> str:
    """
    Computes HMAC-SHA256 signature over bytes payload and returns the uppercase hex digest.
    """
    key_bytes = secret_key.encode("utf-8")
    signature = hmac.new(key_bytes, payload, hashlib.sha256).hexdigest()
    return signature.upper()

def verify_request_signature(
    raw_body_bytes: bytes,
    timestamp: str,
    nonce: str,
    signature: str,
    secret_key: str
) -> bool:
    """
    Verifies request signature against calculated HMAC.
    Signature payload: raw_body_bytes + X-Timestamp + X-Nonce
    """
    if not signature:
        return False
        
    payload_bytes = raw_body_bytes + timestamp.encode("utf-8") + nonce.encode("utf-8")
    calculated = calculate_hmac_sha256(payload_bytes, secret_key)
    
    # Use hmac.compare_digest for constant-time comparison to prevent timing attacks
    is_valid = hmac.compare_digest(calculated.upper(), signature.upper())
    if not is_valid:
        logger.warning(
            f"Signature mismatch. Calculated: {calculated.upper()} vs Provided: {signature.upper()}"
        )
    return is_valid

def sign_response_body(
    response_body_bytes: bytes,
    secret_key: str
) -> str:
    """
    Signs the outbound response body bytes.
    Returns the uppercase HMAC-SHA256 signature string.
    """
    return calculate_hmac_sha256(response_body_bytes, secret_key)
