from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.models import Biller
from typing import List, Optional
from loguru import logger
import uuid

class BillerRepository:
    """
    Repository class to manage biller records in PostgreSQL.
    """
    
    @staticmethod
    async def get_by_biller_id(session: AsyncSession, biller_id: str) -> Optional[Biller]:
        """
        Retrieves a biller by its unique biller_id.
        """
        stmt = select(Biller).filter_by(biller_id=biller_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_billers(
        session: AsyncSession,
        category: Optional[str] = None,
        region: Optional[str] = None
    ) -> List[Biller]:
        """
        Lists all billers, optionally filtered by category and region.
        """
        stmt = select(Biller)
        if category:
            stmt = stmt.filter_by(category=category)
        if region:
            stmt = stmt.filter_by(region=region)
            
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def seed_billers(session: AsyncSession, billers_data: List[dict]) -> None:
        """
        Seeds multiple billers if they don't already exist.
        """
        for item in billers_data:
            exists = await BillerRepository.get_by_biller_id(session, item["biller_id"])
            if not exists:
                biller = Biller(
                    id=uuid.uuid4(),
                    biller_id=item["biller_id"],
                    biller_name=item["biller_name"],
                    category=item["category"],
                    region=item["region"],
                    biller_metadata=item.get("metadata", {})

                )
                session.add(biller)
        await session.flush()
        logger.info(f"Seeded {len(billers_data)} billers.")
