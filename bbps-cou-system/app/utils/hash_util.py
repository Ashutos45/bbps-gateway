import hashlib

def hash_sha256(payload: str) -> str:
    """
    Computes the SHA256 hash of a string payload and returns the uppercase hex digest.
    Used for request/response body hashing in the HMAC generation process.
    """
    payload_bytes = payload.encode("utf-8")
    return hashlib.sha256(payload_bytes).hexdigest().upper()

def hash_sha256_bytes(payload_bytes: bytes) -> str:
    """
    Computes the SHA256 hash of a bytes payload and returns the uppercase hex digest.
    """
    return hashlib.sha256(payload_bytes).hexdigest().upper()
