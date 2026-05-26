from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ErrorMetadata(BaseModel):
    name: str
    value: str

class StandardErrorResponse(BaseModel):
    status: int
    error_type: str
    error_code: str
    message: str
    metadata: List[ErrorMetadata] = []

class FavoriteBillerErrorResponse(BaseModel):
    status: str = "FAILED"
    statusCode: str
    statusDescription: str
    timeStamp: int
    traceId: str
    data: Optional[Any] = None

class GenericSuccessResponse(BaseModel):
    status: str = "success"
    message: str
    data: Optional[Any] = None
