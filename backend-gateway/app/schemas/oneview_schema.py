from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class ReconciliationLogSchema(BaseModel):
    polling_attempts: int
    resolved_state: Optional[str] = None
    reconciliation_status: str
    created_at: datetime

    class Config:
        from_attributes = True

class OneViewTransactionItem(BaseModel):
    trace_id: str
    biller_id: str
    amount: float
    transaction_state: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    request_payload: Optional[Dict[str, Any]] = None
    response_payload: Optional[Dict[str, Any]] = None
    reconciliation_log: Optional[ReconciliationLogSchema] = None

    class Config:
        from_attributes = True

class OneViewResponse(BaseModel):
    customerid: str
    total_transactions: int
    transactions: List[OneViewTransactionItem]
