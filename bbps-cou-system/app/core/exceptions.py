from typing import Any, Dict, List, Optional
import time

class BBPSBaseException(Exception):
    """
    Base Exception for all BBPS COU System errors.
    """
    def __init__(
        self,
        status_code: int = 400,
        message: str = "An error occurred",
        error_code: str = "ERR_GENERIC",
        error_type: str = "generic_error",
        metadata: Optional[List[Dict[str, str]]] = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.error_code = error_code
        self.error_type = error_type
        self.metadata = metadata or []

    def to_response_dict(self, trace_id: str) -> Dict[str, Any]:
        """
        Formats exception as a standard BBPS error format.
        """
        # Ensure traceId is present in metadata if not already there
        trace_meta_exists = any(item.get("name") == "traceId" for item in self.metadata)
        meta = list(self.metadata)
        if not trace_meta_exists:
            meta.append({"name": "traceId", "value": trace_id})
            
        return {
            "status": self.status_code,
            "error_type": self.error_type,
            "error_code": self.error_code,
            "message": self.message,
            "metadata": meta
        }


class FavoriteBillerException(Exception):
    """
    Exception specifically designed for the Favorite Biller operations
    which use a different error payload layout.
    """
    def __init__(
        self,
        status_code: int = 400,
        status_code_str: str = "1",
        status_description: str = "Biller error occurred",
        trace_id: str = ""
    ):
        super().__init__(status_description)
        self.status_code = status_code
        self.status_code_str = status_code_str
        self.status_description = status_description
        self.trace_id = trace_id

    def to_response_dict(self, trace_id: str) -> Dict[str, Any]:
        """
        Formats as a Favorite Biller specific error payload.
        """
        return {
            "status": "FAILED",
            "statusCode": self.statusCode_str if hasattr(self, 'statusCode_str') else self.status_code_str,
            "statusDescription": self.status_description,
            "timeStamp": int(time.time() * 1000),
            "traceId": self.trace_id or trace_id,
            "data": None
        }


# Concrete Exception Classes

class HMACVerificationError(BBPSBaseException):
    def __init__(self, message: str = "HMAC Signature Verification Failed"):
        super().__init__(
            status_code=401,
            message=message,
            error_code="ERR01HMAC",
            error_type="hmac_verification_error"
        )


class InvalidChannelError(BBPSBaseException):
    def __init__(self, channel: str):
        super().__init__(
            status_code=400,
            message=f"Invalid channel '{channel}'. Supported: mbanking, upi, fi, feature-phone",
            error_code="ERR01CHAN",
            error_type="invalid_channel_error"
        )


class BillerNotFoundError(BBPSBaseException):
    def __init__(self, biller_id: str):
        super().__init__(
            status_code=404,
            message=f"Biller '{biller_id}' was not found.",
            error_code="ERR01FBB",
            error_type="fetch_biller_by_billerid_error"
        )


class PrepaidPlanNotFoundError(BBPSBaseException):
    def __init__(self, message: str = "No prepaid plans found for the given criteria."):
        super().__init__(
            status_code=404,
            message=message,
            error_code="ERR01FPP",
            error_type="no_plans_found"
        )


class TransactionFailedError(BBPSBaseException):
    def __init__(self, message: str = "Transaction processing failed"):
        super().__init__(
            status_code=400,
            message=message,
            error_code="ERR01TXN",
            error_type="transaction_failed_error"
        )


class DatabaseError(BBPSBaseException):
    def __init__(self, message: str = "Internal database operational error"):
        super().__init__(
            status_code=500,
            message=message,
            error_code="ERR01DB",
            error_type="database_error"
        )
