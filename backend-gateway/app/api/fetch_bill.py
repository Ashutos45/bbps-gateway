from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.db import get_db
from app.schemas.fetch_bill_schema import FetchBillRequest, FetchBillResponse
from app.services.fetch_bill_service import FetchBillService
from app.auth.auth_middleware import get_hmac_headers, require_roles
from app.auth.role_manager import Role
from loguru import logger

router = APIRouter()

@router.post(
    "/{sourceid}/customers/{customerid}/billpay/validate",
    response_model=FetchBillResponse,
    tags=["Bill Fetch"]
)
async def fetch_bill(
    sourceid: str,
    customerid: str,
    request_data: FetchBillRequest,
    db: AsyncSession = Depends(get_db),
    hmac_headers: dict = Depends(get_hmac_headers),
    user: dict = Depends(require_roles([Role.ADMIN, Role.CLIENT]))
):
    """
    Validates customer and fetches outstanding bills from BOU/Biller.
    """
    logger.info(f"Incoming Fetch Bill request for source: {sourceid}, customer: {customerid}")
    response = await FetchBillService.fetch_bill(
        session=db,
        request=request_data,
        source_id=sourceid,
        customer_id=customerid
    )
    return response
