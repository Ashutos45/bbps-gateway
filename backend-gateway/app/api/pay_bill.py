import random
from fastapi import APIRouter, Depends, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.db import get_db
from app.schemas.payment_schema import PayBillRequest, PayBillResponse
from app.services.payment_service import PaymentService
from app.auth.auth_middleware import get_hmac_headers, require_roles
from app.auth.role_manager import Role
from loguru import logger

router = APIRouter()

@router.post(
    "/{sourceid}/customers/{customerid}/billpay/payments",
    response_model=PayBillResponse,
    tags=["Bill Payment"]
)
async def pay_bill(
    sourceid: str,
    customerid: str,
    request_data: PayBillRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    hmac_headers: dict = Depends(get_hmac_headers),
    user: dict = Depends(require_roles([Role.ADMIN, Role.CLIENT]))
):
    """
    Submits a payment for the specified bill.
    Supports downstream simulation of 30% drops unless bypassed by Header.
    """
    logger.info(f"Incoming Pay Bill request for source: {sourceid}, customer: {customerid}, ref: {request_data.source_ref_no}")

    # Retrieve header and pass to process_payment
    simulate_header = request.headers.get("x-simulate-failure")

    response = await PaymentService.process_payment(
        session=db,
        request=request_data,
        source_id=sourceid,
        customer_id=customerid,
        trace_id=request_data.source_ref_no,
        x_simulate_failure=simulate_header
    )
    return response
