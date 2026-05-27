from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.db import get_db
from app.schemas.oneview_schema import OneViewResponse
from app.services.oneview_service import OneViewService
from app.auth.auth_middleware import get_hmac_headers, require_roles
from app.auth.role_manager import Role
from loguru import logger

router = APIRouter()

@router.get(
    "/{sourceid}/customers/{customerid}/billpay/oneview",
    response_model=OneViewResponse,
    tags=["OneView"]
)
async def get_customer_oneview(
    sourceid: str,
    customerid: str,
    db: AsyncSession = Depends(get_db),
    hmac_headers: dict = Depends(get_hmac_headers),
    user: dict = Depends(require_roles([Role.ADMIN, Role.CLIENT, Role.OPERATIONS, Role.AUDITOR]))
):
    """
    Retrieves a consolidated view of all transaction states and history for a customer.
    Automatically resolves any transactions in AMBIGUOUS_TIMEOUT state on-the-fly.
    """
    logger.info(f"Incoming OneView request for source: {sourceid}, customer: {customerid}")
    response = await OneViewService.get_customer_oneview(
        session=db,
        customer_id=customerid
    )
    return response
