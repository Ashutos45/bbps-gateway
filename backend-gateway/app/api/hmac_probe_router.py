from typing import Optional, List
from fastapi import APIRouter, Header, status, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.services.telemetry_service import TelemetryService
from app.services.hmac_service import HMACService
from app.utils.json_canonicalizer import canonicalize_bytes
from loguru import logger
import time

router = APIRouter()

# Global in-memory list to store verification attempt logs
audit_logs = []


class HMACProbeResponse(BaseModel):
    success: bool
    status: str
    message: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "status": "VALID",
                "message": "Payload integrity verified"
            }
        }
    }


class HMACProbeErrorResponse(BaseModel):
    success: bool
    status: str
    message: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": False,
                "status": "TAMPERED",
                "message": "HMAC verification failed"
            }
        }
    }


class HMACProbePayload(BaseModel):
    trace_id: str
    amount: float

    model_config = {
        "json_schema_extra": {
            "example": {
                "trace_id": "TXN-175137",
                "amount": 2500.00
            }
        }
    }


class AuditLogEntry(BaseModel):
    timestamp: str
    trace_id: str
    amount: float
    signature: str
    nonce: str
    status: str
    message: str


@router.post(
    "/demo/hmac-probe",
    tags=["HMAC Security Demo"],
    response_model=HMACProbeResponse,
    responses={
        401: {
            "model": HMACProbeErrorResponse,
            "description": "HMAC signature verification, skew check, or replay protection failed"
        }
    }
)
async def hmac_probe(
    request: Request,
    payload: HMACProbePayload,
    x_signature: str = Header(..., alias="X-Signature", description="HMAC-SHA256 cryptographic signature"),
    x_timestamp: str = Header(..., alias="X-Timestamp", description="Request timestamp (seconds since epoch)"),
    x_nonce: str = Header(..., alias="X-Nonce", description="Unique request nonce (UUID)"),
    x_source_id: str = Header("mbanking", alias="X-Source-Id", description="Source channel identifier"),
):
    """
    Pure stateless HMAC validation probe endpoint.
    Recalculates and verifies HMAC-SHA256 signature using the provided payload, timestamp, nonce, and source ID.
    Checks for replay attacks and timestamp skew.
    """
    # Get raw body bytes for canonical signature validation
    body_bytes = await request.body()
    canonical_body = b""
    if body_bytes:
        try:
            canonical_body = canonicalize_bytes(body_bytes)
        except Exception as e:
            logger.error(f"[HMAC-PROBE] JSON canonicalization failed: {e}")
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "status": "TAMPERED",
                    "message": "The request body is not a valid JSON structure."
                }
            )

    try:
        HMACService.verify_incoming_request(
            raw_body_bytes=canonical_body,
            timestamp=x_timestamp,
            nonce=x_nonce,
            signature=x_signature.strip().upper(),
            source_id=x_source_id
        )
        # Log success and update metrics
        TelemetryService.record_request()
        logger.info(f"[HMAC-PROBE] Dynamic verification succeeded for source '{x_source_id}' with nonce '{x_nonce}'")

        # Append to audit logs
        audit_logs.append({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "trace_id": payload.trace_id,
            "amount": payload.amount,
            "signature": x_signature,
            "nonce": x_nonce,
            "status": "VALID",
            "message": "Payload integrity verified"
        })

        return {
            "success": True,
            "status": "VALID",
            "message": "Payload integrity verified"
        }
    except Exception as exc:
        from app.core.exceptions import ReplayAttackError, InvalidTimestampError
        
        TelemetryService.record_unauthorized_attempt()
        if isinstance(exc, ReplayAttackError):
            TelemetryService.record_rejected_duplicate_nonce()
            status_str = "REPLAY_ATTACK"
            msg_str = "Replay attack detected: Nonce already used"
        elif isinstance(exc, InvalidTimestampError):
            TelemetryService.record_hmac_failure()
            status_str = "EXPIRED_TIMESTAMP"
            msg_str = "Request timestamp expired or skewed"
        else:
            TelemetryService.record_hmac_failure()
            status_str = "TAMPERED"
            msg_str = "HMAC verification failed"

        # Append to audit logs
        audit_logs.append({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "trace_id": payload.trace_id,
            "amount": payload.amount,
            "signature": x_signature,
            "nonce": x_nonce,
            "status": status_str,
            "message": msg_str
        })

        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "success": False,
                "status": status_str,
                "message": msg_str
            }
        )


@router.get(
    "/demo/hmac-probe/audit-logs",
    tags=["HMAC Security Demo"],
    response_model=List[AuditLogEntry]
)
async def get_audit_logs():
    """
    Returns the immutable audit logs list.
    """
    return audit_logs
