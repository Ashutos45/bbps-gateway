from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.db import get_db
from app.schemas.reconciliation_schema import ReconciliationRequest, ReconciliationResponse
from app.services.reconciliation_service import ReconciliationService
from app.auth.auth_middleware import get_hmac_headers, require_roles
from app.auth.role_manager import Role
from loguru import logger

router = APIRouter()

@router.post(
    "/{sourceid}/billpay/reconcile",
    response_model=ReconciliationResponse,
    tags=["Reconciliation"]
)
async def reconcile_transaction(
    sourceid: str,
    request_data: ReconciliationRequest,
    db: AsyncSession = Depends(get_db),
    hmac_headers: dict = Depends(get_hmac_headers),
    user: dict = Depends(require_roles([Role.ADMIN, Role.OPERATIONS]))
):
    """
    Manually reconciles an ambiguous transaction, transitioning it to a terminal state.
    """
    logger.info(f"Incoming Manual Reconciliation request for source: {sourceid}, trace: {request_data.trace_id}")
    response = await ReconciliationService.reconcile_transaction(
        session=db,
        trace_id=request_data.trace_id
    )
    return response
