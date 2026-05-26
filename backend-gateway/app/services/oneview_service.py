from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.models import TransactionLog, ReconciliationLog
from app.services.reconciliation_service import ReconciliationService
from app.schemas.oneview_schema import OneViewResponse, OneViewTransactionItem, ReconciliationLogSchema
from loguru import logger

class OneViewService:
    """
    Consolidates transaction history for a customer.
    On query, it automatically reconciles any transaction still in AMBIGUOUS_TIMEOUT,
    and formats the response with transaction status details and reconciliation logs.
    """

    @staticmethod
    async def get_customer_oneview(
        session: AsyncSession,
        customer_id: str
    ) -> OneViewResponse:
        logger.info(f"Generating OneView summary for customer: {customer_id}")

        # 1. Query all transactions for customer
        stmt = select(TransactionLog).filter_by(customer_id=customer_id).order_by(TransactionLog.created_at.desc())
        res = await session.execute(stmt)
        transactions = list(res.scalars().all())

        # 2. Reconcile on-the-fly if in AMBIGUOUS_TIMEOUT state
        for tx in transactions:
            if tx.transaction_state == "AMBIGUOUS_TIMEOUT":
                logger.info(f"Reconciling ambiguous transaction '{tx.trace_id}' on-the-fly during OneView call")
                try:
                    # Reconcile using the shared session
                    await ReconciliationService.reconcile_transaction(session, tx.trace_id)
                    # Refresh the model from database to reflect the updated state
                    await session.refresh(tx)
                except Exception as e:
                    logger.error(f"Failed to reconcile trace '{tx.trace_id}' on-the-fly: {e}")

        # 3. Compile transaction items with reconciliation logs
        items = []
        for tx in transactions:
            # Query reconciliation log if any
            stmt_rec = select(ReconciliationLog).filter_by(trace_id=tx.trace_id)
            res_rec = await session.execute(stmt_rec)
            rec_log = res_rec.scalar_one_or_none()

            rec_schema = None
            if rec_log:
                rec_schema = ReconciliationLogSchema.model_validate(rec_log)

            items.append(OneViewTransactionItem(
                trace_id=tx.trace_id,
                biller_id=tx.biller_id,
                amount=float(tx.amount),
                transaction_state=tx.transaction_state,
                created_at=tx.created_at,
                updated_at=tx.updated_at,
                request_payload=tx.request_payload,
                response_payload=tx.response_payload,
                reconciliation_log=rec_schema
            ))

        return OneViewResponse(
            customerid=customer_id,
            total_transactions=len(items),
            transactions=items
        )
