from pydantic import BaseModel, Field
from typing import Optional

class ReconciliationRequest(BaseModel):
    trace_id: str = Field(..., description="The transaction trace_id to reconcile")

class ReconciliationResponse(BaseModel):
    trace_id: str
    polling_attempts: int
    resolved_state: Optional[str] = None
    reconciliation_status: str  # PENDING, RESOLVED, UNRESOLVED
    message: str
