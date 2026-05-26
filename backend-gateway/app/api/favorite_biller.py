from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database.db import get_db
from app.schemas.favorite_biller_schema import (
    FavoriteBillerAddRequest,
    FavoriteBillerUpdateRequest,
    FavoriteBillerResponse
)
from app.services.favorite_biller_service import FavoriteBillerService
from app.auth.auth_middleware import get_hmac_headers, require_roles
from app.auth.role_manager import Role
from loguru import logger

router = APIRouter()

@router.post(
    "/{sourceid}/customers/{customerid}/billpay/billeraccounts",
    response_model=FavoriteBillerResponse,
    tags=["Favorite Billers"]
)
async def add_favorite_biller(
    sourceid: str,
    customerid: str,
    request_data: FavoriteBillerAddRequest,
    db: AsyncSession = Depends(get_db),
    hmac_headers: dict = Depends(get_hmac_headers),
    user: dict = Depends(require_roles([Role.ADMIN, Role.CLIENT]))
):
    """
    Registers a new Favorite Biller for a customer.
    """
    logger.info(f"Adding favorite biller for customer {customerid}, biller: {request_data.billerid}")
    result = await FavoriteBillerService.add_favorite_biller(
        session=db,
        customer_id=customerid,
        biller_id=request_data.billerid,
        short_name=request_data.short_name,
        authenticators=[a.model_dump() for a in request_data.authenticators] if request_data.authenticators else None,
        autopay_status=request_data.autopay_status,
        autopay_amount=request_data.autopay_amount,
        payment_account=request_data.payment_account,
        frequency=request_data.frequency
    )
    return result

@router.get(
    "/{sourceid}/customers/{customerid}/billpay/billeraccounts",
    response_model=List[FavoriteBillerResponse],
    tags=["Favorite Billers"]
)
async def get_favorite_billers(
    sourceid: str,
    customerid: str,
    db: AsyncSession = Depends(get_db),
    hmac_headers: dict = Depends(get_hmac_headers),
    user: dict = Depends(require_roles([Role.ADMIN, Role.CLIENT]))
):
    """
    Retrieves all active registered Favorite Billers for a customer.
    """
    logger.info(f"Retrieving favorite billers for customer {customerid}")
    result = await FavoriteBillerService.get_favorite_billers(
        session=db,
        customer_id=customerid
    )
    return result

@router.put(
    "/{sourceid}/customers/{customerid}/billpay/billeraccounts/{billeraccountid}",
    response_model=FavoriteBillerResponse,
    tags=["Favorite Billers"]
)
async def update_favorite_biller(
    sourceid: str,
    customerid: str,
    billeraccountid: str,
    request_data: FavoriteBillerUpdateRequest,
    db: AsyncSession = Depends(get_db),
    hmac_headers: dict = Depends(get_hmac_headers),
    user: dict = Depends(require_roles([Role.ADMIN, Role.CLIENT]))
):
    """
    Updates registration details for an active Favorite Biller account.
    """
    logger.info(f"Updating favorite biller account {billeraccountid} for customer {customerid}")
    result = await FavoriteBillerService.update_favorite_biller(
        session=db,
        customer_id=customerid,
        biller_account_id=billeraccountid,
        short_name=request_data.short_name,
        autopay_status=request_data.autopay_status,
        autopay_amount=request_data.autopay_amount,
        payment_account=request_data.payment_account,
        frequency=request_data.frequency
    )
    return result

@router.delete(
    "/{sourceid}/customers/{customerid}/billpay/billeraccounts/{billeraccountid}",
    tags=["Favorite Billers"]
)
async def delete_favorite_biller(
    sourceid: str,
    customerid: str,
    billeraccountid: str,
    db: AsyncSession = Depends(get_db),
    hmac_headers: dict = Depends(get_hmac_headers),
    user: dict = Depends(require_roles([Role.ADMIN, Role.CLIENT]))
):
    """
    Deactivates/Deletes a registered Favorite Biller account.
    """
    logger.info(f"Deleting favorite biller account {billeraccountid} for customer {customerid}")
    result = await FavoriteBillerService.delete_favorite_biller(
        session=db,
        customer_id=customerid,
        biller_account_id=billeraccountid
    )
    return result
