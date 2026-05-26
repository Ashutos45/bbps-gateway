# Supported Channels / Sources
ALLOWED_CHANNELS = ["mbanking", "upi", "fi", "feature-phone"]

# HTTP Header Defaults
CONTENT_TYPE_JSON = "application/json"
ACCEPT_JSON = "application/json"

# Currency Code (INR - Indian Rupee in ISO 4217 numeric code)
INR_CURRENCY_CODE = "356"

# Transaction / Operation Statuses
class TransactionStatus:
    INITIATED = "INITIATED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

# Error Codes
class BBPS_ErrorCodes:
    INVALID_CHANNEL = "ERR_INVALID_CHANNEL"
    HMAC_VERIFICATION_FAILED = "ERR_HMAC_VERIFICATION_FAILED"
    TRANSACTION_FAILED = "ERR_TRANSACTION_FAILED"
    DATABASE_ERROR = "ERR_DATABASE_ERROR"
    VALIDATION_ERROR = "ERR_VALIDATION_ERROR"
