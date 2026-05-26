from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.models import FavoriteBiller, Biller
from app.core.exceptions import FavoriteBillerException
from app.database.repositories.biller_repository import BillerRepository
from loguru import logger
from typing import List, Optional, Dict, Any
import uuid
import time
from datetime import datetime

class FavoriteBillerService:
    """
    Service to manage customer-registered Favorite Billers.
    Strictly conforms to spec formats for success and error responses.
    """

    @staticmethod
    async def add_favorite_biller(
        session: AsyncSession,
        customer_id: str,
        biller_id: str,
        short_name: Optional[str] = None,
        authenticators: Optional[list] = None,
        autopay_status: str = "N",
        autopay_amount: float = None,
        payment_account: dict = None,
        frequency: str = None
    ) -> dict:
        logger.info(f"Adding favorite biller '{biller_id}' for customer '{customer_id}'")

        # 1. Check if Biller exists
        biller = await BillerRepository.get_by_biller_id(session, biller_id)
        # If not exists, construct mock name
        biller_name = biller.biller_name if biller else "Mock Operator"

        if not short_name:
            short_name = biller_name

        if not authenticators:
            category = biller.category if biller else "Utility"
            if category == "Electricity":
                authenticators = [{"seq": "1", "parameter_name": "Consumer Number", "value": "123456789"}]
            elif category == "Telecom":
                authenticators = [{"seq": "1", "parameter_name": "Mobile Number", "value": "9876543210"}]
            elif category == "Water":
                authenticators = [{"seq": "1", "parameter_name": "Consumer ID", "value": "987654321"}]
            elif category == "Gas":
                authenticators = [{"seq": "1", "parameter_name": "Gas Account Number", "value": "GAS9876543"}]
            else:
                authenticators = [{"seq": "1", "parameter_name": "Consumer Number", "value": "1234567890"}]

        # 2. Check if already exists for this customer (where status = ACTIVE)
        stmt = select(FavoriteBiller).filter_by(
            customer_id=customer_id,
            biller_id=biller_id,
            status="ACTIVE"
        )
        res = await session.execute(stmt)
        if res.scalar_one_or_none():
            logger.warning(f"Biller '{biller_id}' already marked as favorite for customer '{customer_id}'")
            raise FavoriteBillerException(
                status_code=400,
                status_code_str="1",
                status_description="This biller is already marked as a favorite."
            )

        # 3. Create new registered FavoriteBiller
        biller_account_id = str(uuid.uuid4().int)[:16]  # 16-digit numeric ID
        now = datetime.now()
        
        reg_biller = FavoriteBiller(
            id=uuid.uuid4(),
            billeraccountid=biller_account_id,
            customer_id=customer_id,
            biller_id=biller_id,
            short_name=short_name,
            authenticators=authenticators,
            status="ACTIVE",
            registration_date=now,
            autopay_status=autopay_status,
            autopay_amount=autopay_amount,
            payment_account=payment_account,
            frequency=frequency,
            cprn=f"ISU{str(uuid.uuid4().int)[:8]}"
        )

        session.add(reg_biller)
        await session.commit()

        logger.info(f"Added Favorite Biller. Biller Account ID: {biller_account_id}")
        return FavoriteBillerService._to_response_format(reg_biller)

    @staticmethod
    async def update_favorite_biller(
        session: AsyncSession,
        customer_id: str,
        biller_account_id: str,
        short_name: str = None,
        autopay_status: str = None,
        autopay_amount: float = None,
        payment_account: dict = None,
        frequency: str = None
    ) -> dict:
        logger.info(f"Updating favorite biller account '{biller_account_id}' for customer '{customer_id}'")

        # 1. Fetch record
        stmt = select(FavoriteBiller).filter_by(
            billeraccountid=biller_account_id,
            customer_id=customer_id,
            status="ACTIVE"
        )
        res = await session.execute(stmt)
        record = res.scalar_one_or_none()

        if not record:
            logger.warning(f"Biller account '{biller_account_id}' not found.")
            raise FavoriteBillerException(
                status_code=404,
                status_code_str="1",
                status_description="Active favorite biller account not found."
            )

        # 2. Update fields
        if short_name is not None:
            record.short_name = short_name
        if autopay_status is not None:
            record.autopay_status = autopay_status
        if autopay_amount is not None:
            record.autopay_amount = autopay_amount
        if payment_account is not None:
            record.payment_account = payment_account
        if frequency is not None:
            record.frequency = frequency

        await session.commit()
        logger.info(f"Updated favorite biller account '{biller_account_id}' successfully.")
        return FavoriteBillerService._to_response_format(record)

    @staticmethod
    async def get_favorite_billers(
        session: AsyncSession,
        customer_id: str
    ) -> List[dict]:
        logger.info(f"Retrieving active favorite billers for customer '{customer_id}'")
        
        stmt = select(FavoriteBiller).filter_by(
            customer_id=customer_id,
            status="ACTIVE"
        )
        res = await session.execute(stmt)
        records = res.scalars().all()

        if not records:
            logger.warning(f"No favorite billers found for customer: {customer_id}")
            # Raise FavoriteBillerException with specific ERR01FFBA error code as shown on Page 77
            raise FavoriteBillerException(
                status_code=400,
                status_code_str="ERR01FFBA",
                status_description="No favorite billers have been added for this customer."
            )

        return [FavoriteBillerService._to_response_format(r) for r in records]

    @staticmethod
    async def delete_favorite_biller(
        session: AsyncSession,
        customer_id: str,
        biller_account_id: str
    ) -> dict:
        logger.info(f"Deleting favorite biller account '{biller_account_id}' for customer '{customer_id}'")

        # 1. Fetch active record
        stmt = select(FavoriteBiller).filter_by(
            billeraccountid=biller_account_id,
            customer_id=customer_id,
            status="ACTIVE"
        )
        res = await session.execute(stmt)
        record = res.scalar_one_or_none()

        if not record:
            logger.warning(f"Biller account '{biller_account_id}' is already deleted or inactive.")
            raise FavoriteBillerException(
                status_code=400,
                status_code_str="1",
                status_description="Biller is already deleted or inactive."
            )

        # 2. Transition status to DELETED
        record.status = "DELETED"
        record.deletion_date = datetime.now()
        await session.commit()

        logger.info(f"Deleted favorite biller account '{biller_account_id}' successfully.")
        return {
            "billeraccountid": record.billeraccountid,
            "objectid": "billeraccount",
            "sourceid": "SRC01",
            "billerid": record.biller_id,
            "short_name": record.short_name,
            "authenticators": record.authenticators,
            "status": "DELETED",
            "registration_date": record.registration_date.strftime("%d-%m-%Y %H:%M:%S"),
            "deletion_date": record.deletion_date.strftime("%d-%m-%Y %H:%M:%S")
        }

    @staticmethod
    def _to_response_format(record: FavoriteBiller) -> dict:
        """
        Formats db record into spec-mandated favorite biller format (Page 41).
        """
        return {
            "billeraccountid": record.billeraccountid,
            "objectid": "billeraccount",
            "sourceid": "SRC01",  # Static placeholder matching spec response
            "billerid": record.biller_id,
            "short_name": record.short_name,
            "authenticators": record.authenticators,
            "status": record.status,
            "registration_date": record.registration_date.strftime("%d-%m-%Y %H:%M:%S"),
            "autopay_status": record.autopay_status,
            "autopay_start_date": record.autopay_start_date.strftime("%d-%m-%Y %H:%M:%S") if record.autopay_start_date else None,
            "autopay_end_date": record.autopay_end_date.strftime("%d-%m-%Y %H:%M:%S") if record.autopay_end_date else None,
            "autopay_amount": float(record.autopay_amount) if record.autopay_amount else None,
            "currency": record.currency,
            "frequency": record.frequency,
            "payment_account": record.payment_account,
            "activation_date": record.registration_date.strftime("%d-%m-%Y %H:%M:%S"),
            "cprn": record.cprn,
            "customer": {
                "mobile": record.customer_id
            }
        }
