from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.repositories.transaction_repository import TransactionRepository
from app.database.repositories.biller_repository import BillerRepository
from app.core.idempotency import IdempotencyEngine
from app.core.constants import TransactionState
from app.core.exceptions import TransactionFailedError, BillerNotFoundError, IdempotencyViolationError
from app.schemas.payment_schema import PayBillRequest, PayBillResponse
from app.schemas.common_schema import Authenticator
from app.database.models import PaymentIdempotency
from app.services.telemetry_service import TelemetryService
from app.core.config import settings
import random
import uuid
import asyncio
from datetime import datetime
from loguru import logger

class PaymentService:
    """
    Orchestrates transaction processing for bill payments:
    - Enforces idempotency locks
    - Persists state transition logs
    - Simulates network drops (30% failures) into AMBIGUOUS_TIMEOUT
    - Records telemetry metrics
    """

    @staticmethod
    async def process_payment(
        session: AsyncSession,
        request: PayBillRequest,
        source_id: str,
        customer_id: str,
        trace_id: str,
        x_simulate_failure: Optional[str] = None
    ) -> PayBillResponse:
        logger.info(f"Initiating payment processing for customer '{customer_id}' on channel '{source_id}'")

        # 0. Enrich from validation context if validationid is provided
        if request.validationid:
            from sqlalchemy import select
            from app.database.models import TransactionLog
            from app.core.exceptions import BBPSBaseException
            
            stmt = select(TransactionLog).where(
                TransactionLog.response_payload["validationid"].astext == request.validationid,
                TransactionLog.transaction_state == TransactionState.INITIALIZED
            )
            res = await session.execute(stmt)
            val_tx = res.scalar_one_or_none()
            
            if val_tx:
                val_req = val_tx.request_payload or {}
                if not request.payment_amount and val_tx.amount is not None:
                    # Retrieve the original decimal amount as string
                    request.payment_amount = str(int(val_tx.amount))
                if not request.billerid:
                    request.billerid = val_tx.biller_id
                if not request.billeraccountid:
                    request.billeraccountid = val_req.get("billeraccountid")
                if not request.customer:
                    from app.schemas.common_schema import Customer
                    cust_data = val_req.get("customer")
                    if cust_data:
                        request.customer = Customer(**cust_data)
                if not request.metadata:
                    from app.schemas.common_schema import Metadata
                    meta_data = val_req.get("metadata")
                    if meta_data:
                        request.metadata = Metadata(**meta_data)
            else:
                logger.warning(f"Validation ID '{request.validationid}' not found in database logs.")
                if not request.billerid:
                    from app.core.exceptions import BBPSBaseException
                    raise BBPSBaseException(
                        status_code=400,
                        message="Validation ID not found, and required fields are missing.",
                        error_code="ERR_VALIDATION_NOT_FOUND",
                        error_type="validation_error"
                    )

        if not request.payment_amount:
            from app.core.exceptions import BBPSBaseException
            raise BBPSBaseException(
                status_code=400,
                message="Validation failed: 'payment_amount' must be provided or resolved from validationid.",
                error_code="ERR_VALIDATION_FAILED",
                error_type="validation_error"
            )

        # Auto-enrich customer details if missing
        if not request.customer:
            from app.database.models import User
            from app.schemas.common_schema import Customer
            from sqlalchemy import select
            stmt = select(User).where(User.username.ilike(customer_id))
            res = await session.execute(stmt)
            db_user = res.scalar_one_or_none()
            if db_user:
                request.customer = Customer(
                    firstname=db_user.username.capitalize(),
                    lastname="Customer",
                    mobile="9876543210",
                    email=db_user.email
                )
            else:
                request.customer = Customer(
                    firstname="Ashutos",
                    lastname="Satapathy",
                    mobile="9876543210",
                    email="ashutos@test.com"
                )

        # Auto-enrich metadata if missing
        if not request.metadata:
            from app.schemas.common_schema import Metadata, Agent, Device
            request.metadata = Metadata(
                agent=Agent(agentid="AGENT001", sub_agentid="SUBAG001"),
                device=Device(
                    init_channel="MOBILE_APP",
                    ip="192.168.1.10",
                    mac="AA:BB:CC:DD:EE:FF",
                    os="Windows 11",
                    app="BBPS NextGen",
                    user_agent="Mozilla/5.0"
                ),
                additional_info=[]
            )

        import time
        if not request.source_ref_no:
            request.source_ref_no = f"REF-{str(uuid.uuid4().int)[:6]}-{str(int(time.time()))[-4:]}"
        
        trace_id = request.source_ref_no

        if not request.debit_amount:
            request.debit_amount = request.payment_amount

        if not request.payment_type:
            request.payment_type = "billpay"

        if not request.payment_account:
            from app.schemas.payment_schema import PaymentAccount
            method = request.payment_method or "CreditCard"
            method_mapped = "CreditCard"
            if str(method).strip().upper() in ("CARD", "CREDITCARD", "DEBITCARD"):
                method_mapped = "CreditCard"
            elif str(method).strip().upper() in ("UPI", "PAY"):
                method_mapped = "UPI"
            elif str(method).strip().upper() in ("NETBANKING", "BANK"):
                method_mapped = "NetBanking"
            
            cust_name = f"{request.customer.firstname} {request.customer.lastname}"
            request.payment_account = PaymentAccount(
                payment_method=method_mapped,
                cardholder_name=cust_name
            )

        # 1. Verify Biller exists
        biller = await BillerRepository.get_by_biller_id(session, request.billerid)
        if not biller:
            logger.warning(f"Biller '{request.billerid}' not found.")
            raise BillerNotFoundError(request.billerid)

        # Dynamic Authenticator Validation based on Biller Category
        biller_category = biller.category
        if request.validationid:
            pass
        elif request.billeraccountid or request.authenticators:
            category_upper = biller_category.upper()
            auths_to_check = request.authenticators or []
            for auth in auths_to_check:
                val = str(auth.value).strip()
                if "ELECT" in category_upper:
                    if not val.isdigit() or len(val) < 6:
                        logger.warning(f"Authenticator validation failed: Invalid Consumer Number '{val}' for Electricity biller '{request.billerid}'")
                        from app.core.exceptions import BBPSBaseException
                        raise BBPSBaseException(
                            status_code=400,
                            message=f"Validation failed: Consumer Number '{val}' must be numeric and at least 6 digits for Electricity biller.",
                            error_code="ERR_AUTHENTICATOR_INVALID",
                            error_type="validation_error"
                        )
                elif "TELE" in category_upper or "MOBILE" in category_upper:
                    if not val.isdigit() or len(val) != 10:
                        logger.warning(f"Authenticator validation failed: Invalid Mobile Number '{val}' for Telecom biller '{request.billerid}'")
                        from app.core.exceptions import BBPSBaseException
                        raise BBPSBaseException(
                            status_code=400,
                            message=f"Validation failed: Mobile Number '{val}' must be a valid 10-digit number for Telecom biller.",
                            error_code="ERR_AUTHENTICATOR_INVALID",
                            error_type="validation_error"
                        )
                elif "GAS" in category_upper:
                    if len(val) < 5:
                        logger.warning(f"Authenticator validation failed: Invalid Customer ID '{val}' for Gas biller '{request.billerid}'")
                        from app.core.exceptions import BBPSBaseException
                        raise BBPSBaseException(
                            status_code=400,
                            message=f"Validation failed: Gas Account Number/Customer ID '{val}' must be at least 5 characters.",
                            error_code="ERR_AUTHENTICATOR_INVALID",
                            error_type="validation_error"
                        )

        # Validate Approval Maker/Checker workflow dates
        if request.approval_details:
            app_details = request.approval_details
            logger.info(f"[AUDIT TRAIL] Validating Maker-Checker details: Maker ID: {app_details.makerid}, Approver ID: {app_details.approverid}, Request ID: {app_details.requestid}")
            
            maker_date_str = app_details.maker_request_date
            approval_date_str = app_details.approval_date
            maker_date = None
            approval_date = None
            
            for fmt in ("%d-%m-%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    maker_date = datetime.strptime(maker_date_str, fmt)
                    break
                except ValueError:
                    continue
            for fmt in ("%d-%m-%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    approval_date = datetime.strptime(approval_date_str, fmt)
                    break
                except ValueError:
                    continue
            
            if maker_date and approval_date:
                if approval_date < maker_date:
                    logger.warning(f"[AUDIT TRAIL] Approval validation failed: Approval date '{approval_date_str}' is earlier than Maker request date '{maker_date_str}'")
                    from app.core.exceptions import BBPSBaseException
                    raise BBPSBaseException(
                        status_code=400,
                        message=f"Validation failed: Approval date '{approval_date_str}' cannot be earlier than Maker request date '{maker_date_str}'.",
                        error_code="ERR_APPROVAL_VALIDATION_FAILED",
                        error_type="validation_error"
                    )

        # Process Risk Engine values and anomalies
        if request.risk:
            for risk_item in request.risk:
                logger.info(f"[RISK ENGINE] Evaluating risk scoring: Provider={risk_item.score_provider}, Type={risk_item.score_type}, Value={risk_item.score_value}")
                try:
                    score = int(risk_item.score_value)
                    if score > 80:
                        logger.warning(f"[RISK ENGINE ANOMALY DETECTED] High-risk transaction score '{score}' from provider '{risk_item.score_provider}' for trace: {request.source_ref_no}")
                except ValueError:
                    pass

        # Process Metadata device and agent logging
        agent_id = request.metadata.agent.agentid if request.metadata and request.metadata.agent else "N/A"
        device_ip = request.metadata.device.ip if request.metadata and request.metadata.device else "N/A"
        device_mac = request.metadata.device.mac if request.metadata and request.metadata.device else "N/A"
        logger.info(f"[AUDIT TRAIL] Payment transaction request processed: Biller: {request.billerid} | Agent: {agent_id} | Client IP: {device_ip} | MAC: {device_mac}")

        # 2. Acquire Idempotency Lock
        payment_ref = f"PAY-{str(uuid.uuid4().int)[:16]}"
        try:
            # We flush this to database to secure the lock
            lock_record = await IdempotencyEngine.acquire_lock(
                session=session,
                idempotency_key=request.source_ref_no,
                payment_reference=payment_ref
            )
        except IdempotencyViolationError as e:
            # Record duplicate payment attempt in telemetry
            TelemetryService.record_duplicate_payment()
            raise e

        # If the lock is already in a final state, return the cached response
        if lock_record.transaction_status in ("SUCCESS", "FAILED"):
            logger.info(f"Duplicate request detected for key '{request.source_ref_no}' in state '{lock_record.transaction_status}'. Returning cached response.")
            TelemetryService.record_duplicate_payment()
            existing_tx = await TransactionRepository.get_by_trace_id(session, request.source_ref_no)
            if existing_tx and existing_tx.response_payload:
                return PayBillResponse(**existing_tx.response_payload)
            else:
                raise TransactionFailedError("Duplicate request received, but no response payload was cached.")

        # 3. Create initial Transaction Log (Mask Card details first)
        req_payload_dict = request.model_dump(mode="json")
        if req_payload_dict.get("payment_account"):
            pa = req_payload_dict["payment_account"]
            if pa.get("enc_card_number"):
                card = str(pa["enc_card_number"])
                if len(card) > 8:
                    pa["enc_card_number"] = card[:4] + "*" * (len(card) - 8) + card[-4:]
                else:
                    pa["enc_card_number"] = "****"
            if pa.get("enc_card_expiry"):
                pa["enc_card_expiry"] = "**/**"

        tx_log = await TransactionRepository.create_log(
            session=session,
            trace_id=request.source_ref_no,
            customer_id=customer_id,
            biller_id=request.billerid,
            amount=float(request.payment_amount),
            request_payload=req_payload_dict
        )
        await session.commit()  # Commit initialization to DB

        # Start a new transaction block for processing state transitions
        async with session.begin():
            # Refetch within transaction to keep it active
            tx_log = await TransactionRepository.get_by_trace_id(session, request.source_ref_no, for_update=True)
            
            # Transition to PENDING_SUBMISSION
            await TransactionRepository.update_state(
                session=session,
                trace_id=request.source_ref_no,
                new_state=TransactionState.PENDING_SUBMISSION
            )

            # Transition to NETWORK_IN_FLIGHT
            await TransactionRepository.update_state(
                session=session,
                trace_id=request.source_ref_no,
                new_state=TransactionState.NETWORK_IN_FLIGHT
            )

        # 4. Apply Network Simulation & Resilience Boundaries
        from app.services.network_simulation_service import NetworkSimulationService
        from app.core.circuit_breaker import CircuitBreakerOpenException
        try:
            await NetworkSimulationService.apply_resilience_boundaries(
                x_simulate_failure_header=x_simulate_failure,
                request_path=f"/{source_id}/customers/{customer_id}/billpay/payments",
                biller_id=request.billerid
            )
        except CircuitBreakerOpenException as breaker_ex:
            # Circuit breaker is OPEN: fail immediately without ambiguity
            logger.error(f"Circuit Breaker blocked request for trace '{request.source_ref_no}': {breaker_ex}")
            async with session.begin():
                await TransactionRepository.update_state(
                    session=session,
                    trace_id=request.source_ref_no,
                    new_state=TransactionState.FAILED
                )
                await IdempotencyEngine.update_status(session, request.source_ref_no, "FAILED")
                # Create a completed reconciliation log entry for circuit breaker failure
                from app.database.models import ReconciliationLog
                rec_log = ReconciliationLog(
                    id=uuid.uuid4(),
                    trace_id=request.source_ref_no,
                    polling_attempts=0,
                    resolved_state="FAILED",
                    reconciliation_status="RESOLVED"
                )
                session.add(rec_log)
            
            raise TransactionFailedError(
                message="Downstream gateway circuit breaker is OPEN. Requests short-circuited.",
                status_code=503,
                error_code="ERR_CIRCUIT_BREAKER_OPEN",
                error_type="circuit_breaker_open"
            )
        except TransactionFailedError as timeout_ex:
            # Simulated downstream failure (timeout or outage): persist as AMBIGUOUS_TIMEOUT
            logger.warning(f"Simulated network failure occurred for trace '{request.source_ref_no}'. Marking as AMBIGUOUS_TIMEOUT.")
            TelemetryService.record_network_simulation_failure()
            
            async with session.begin():
                await TransactionRepository.update_state(
                    session=session,
                    trace_id=request.source_ref_no,
                    new_state=TransactionState.AMBIGUOUS_TIMEOUT
                )
                # Keep idempotency as PENDING for recovery
                await IdempotencyEngine.update_status(session, request.source_ref_no, "PENDING")
                # Create a pending reconciliation log entry for ambiguous timeout
                from app.database.models import ReconciliationLog
                rec_log = ReconciliationLog(
                    id=uuid.uuid4(),
                    trace_id=request.source_ref_no,
                    polling_attempts=0,
                    resolved_state=None,
                    reconciliation_status="PENDING"
                )
                session.add(rec_log)
            
            raise timeout_ex
        except Exception as general_ex:
            # Any other general failure: mark as FAILED
            async with session.begin():
                await TransactionRepository.update_state(
                    session=session,
                    trace_id=request.source_ref_no,
                    new_state=TransactionState.FAILED
                )
                await IdempotencyEngine.update_status(session, request.source_ref_no, "FAILED")
                # Create a completed reconciliation log entry for general failure
                from app.database.models import ReconciliationLog
                rec_log = ReconciliationLog(
                    id=uuid.uuid4(),
                    trace_id=request.source_ref_no,
                    polling_attempts=0,
                    resolved_state="FAILED",
                    reconciliation_status="RESOLVED"
                )
                session.add(rec_log)
            raise general_ex

        # 5. Successful Settlement Path
        now = datetime.now()
        payment_date_str = now.strftime("%d-%m-%Y %H:%M:%S")
        
        response_data = PayBillResponse(
            sourceid=source_id,
            customerid=customer_id,
            billerid=request.billerid,
            biller_name=biller.biller_name,
            biller_category=biller.category,
            billeraccountid=request.billeraccountid,
            authenticators=[Authenticator(seq="1", parameter_name="PaymentRef", value=payment_ref)],
            validationid=request.validationid,
            payment_amount=request.payment_amount,
            debit_amount=request.debit_amount,
            payment_type=request.payment_type,
            source_ref_no=request.source_ref_no,
            payment_reference=payment_ref,
            status="SETTLED",
            payment_date=payment_date_str
        )
        response_payload_dict = response_data.model_dump(mode="json")

        # Persist final SETTLED state and mark lock as SUCCESS
        async with session.begin():
            await TransactionRepository.update_state(
                session=session,
                trace_id=request.source_ref_no,
                new_state=TransactionState.SETTLED,
                response_payload=response_payload_dict
            )
            await IdempotencyEngine.update_status(session, request.source_ref_no, "SUCCESS")
            # Create a completed reconciliation log entry for settled payment
            from app.database.models import ReconciliationLog
            rec_log = ReconciliationLog(
                id=uuid.uuid4(),
                trace_id=request.source_ref_no,
                polling_attempts=0,
                resolved_state="SETTLED",
                reconciliation_status="RESOLVED"
            )
            session.add(rec_log)

        logger.info(f"Payment settled successfully. Payment Ref: {payment_ref}")
        return response_data
