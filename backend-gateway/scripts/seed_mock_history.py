import os
import sys
import asyncio
import random
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

# Setup PYTHONPATH to include backend root directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.db import AsyncSessionLocal, engine
from app.database.models import TransactionLog, ReconciliationLog, PaymentIdempotency
from app.core.constants import TransactionState
from loguru import logger

async def seed_mock_history():
    logger.info("Starting database seeding for transaction history, reconciliation, and idempotency...")
    
    # 1. Clear existing history to make it fresh and clean
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # We don't necessarily need to truncate, but it ensures clean seeding
            logger.info("Clearing existing transaction logs, reconciliation logs, and idempotency records...")
            await session.execute(TransactionLog.__table__.delete())
            await session.execute(ReconciliationLog.__table__.delete())
            await session.execute(PaymentIdempotency.__table__.delete())
            
    billers = [
        ("MOCKEDU00001NAT", "National Education Services 1"),
        ("MOCKTEL00002RAJ", "Rajasthan Telecom Board 2"),
        ("MOCKBRO00003DEL", "Delhi Broadband Board 3"),
        ("MOCKWAT00004WES", "West Bengal Water Board 4"),
        ("MOCKWAT00005ODI", "Odisha Water Board 5")
    ]
    
    states = [
        TransactionState.SETTLED,
        TransactionState.SETTLED,
        TransactionState.SETTLED,
        TransactionState.FAILED,
        TransactionState.AMBIGUOUS_TIMEOUT,
        TransactionState.FAILED_DLQ,
        TransactionState.PENDING_RETRY,
        TransactionState.SETTLED,
        TransactionState.FAILED,
        TransactionState.SETTLED
    ]
    
    now = datetime.utcnow()
    
    tx_logs = []
    recon_logs = []
    idem_keys = []
    
    for i in range(15):
        biller_id, biller_name = random.choice(billers)
        state = states[i % len(states)]
        amount = Decimal(f"{random.randint(50, 5000)}.00")
        trace_id = f"TXN{random.randint(10000000, 99999999)}"
        cust_id = "cust123"
        
        # Create timestamps going back in time
        created_time = now - timedelta(minutes=(15 - i) * 25 + random.randint(1, 15))
        
        retry_attempts = 0
        next_retry = None
        if state == TransactionState.PENDING_RETRY:
            retry_attempts = random.randint(1, 3)
            next_retry = created_time + timedelta(seconds=60)
        elif state == TransactionState.FAILED_DLQ:
            retry_attempts = 5
            
        request_payload = {
            "billerid": biller_id,
            "payment_amount": str(amount),
            "customer": {"firstname": "Rahul", "lastname": "Sharma", "mobile": "9876543210"}
        }
        
        response_payload = None
        if state == TransactionState.SETTLED:
            response_payload = {
                "status": "SETTLED",
                "payment_reference": f"REF{random.randint(1000000, 9999999)}",
                "payment_date": created_time.isoformat()
            }
        elif state == TransactionState.FAILED:
            response_payload = {
                "status": "FAILED",
                "error_code": "ERR_INSUFFICIENT_FUNDS",
                "message": "Payment failed: Insufficient account balance."
            }
            
        tx = TransactionLog(
            trace_id=trace_id,
            customer_id=cust_id,
            biller_id=biller_id,
            amount=amount,
            transaction_state=state,
            request_payload=request_payload,
            response_payload=response_payload,
            retry_attempts=retry_attempts,
            next_retry_at=next_retry,
            worker_last_execution=created_time + timedelta(seconds=1) if retry_attempts > 0 else None,
            created_at=created_time,
            updated_at=created_time + timedelta(seconds=2)
        )
        tx_logs.append(tx)
        
        # If it is settled, add an idempotency mapping
        if state == TransactionState.SETTLED:
            ref = response_payload["payment_reference"]
            idem = PaymentIdempotency(
                idempotency_key=f"idem_key_{trace_id}",
                payment_reference=ref,
                transaction_status="SUCCESS",
                created_at=created_time
            )
            idem_keys.append(idem)
            
        # If state is AMBIGUOUS_TIMEOUT or FAILED_DLQ, add a reconciliation log
        if state in (TransactionState.AMBIGUOUS_TIMEOUT, TransactionState.FAILED_DLQ) or (state == TransactionState.SETTLED and random.random() < 0.3):
            recon_status = "PENDING"
            resolved_state = None
            if state == TransactionState.SETTLED:
                recon_status = "RESOLVED"
                resolved_state = "SETTLED"
            elif state == TransactionState.FAILED_DLQ:
                recon_status = "UNRESOLVED"
                
            recon = ReconciliationLog(
                trace_id=trace_id,
                polling_attempts=retry_attempts if retry_attempts > 0 else random.randint(1, 4),
                resolved_state=resolved_state,
                reconciliation_status=recon_status,
                created_at=created_time + timedelta(seconds=10)
            )
            recon_logs.append(recon)

    async with AsyncSessionLocal() as session:
        async with session.begin():
            session.add_all(tx_logs)
            session.add_all(idem_keys)
            session.add_all(recon_logs)
            logger.info("Successfully seeded transaction logs, reconciliation records, and idempotency states.")
            
    await engine.dispose()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_mock_history())
