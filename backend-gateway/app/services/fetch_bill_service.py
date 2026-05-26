from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.repositories.biller_repository import BillerRepository
from app.core.exceptions import BillerNotFoundError, BBPSBaseException
from app.schemas.fetch_bill_schema import FetchBillRequest, FetchBillResponse, BillItem
from app.database.models import FavoriteBiller
from app.utils.timestamp_util import get_current_bob_timestamp
import uuid
from datetime import datetime, timedelta, timezone
from loguru import logger

class FetchBillService:
    """
    Service layer logic for validating and retrieving bill details.
    """
    
    @staticmethod
    async def fetch_bill(
        session: AsyncSession,
        request: FetchBillRequest,
        source_id: str,
        customer_id: str
    ) -> FetchBillResponse:
        logger.info(f"Processing Fetch Bill request for customer '{customer_id}' on channel '{source_id}'")

        # 1. Validate input parameters (either billeraccountid OR billerid + authenticators must exist)
        if not request.billeraccountid and (not request.billerid or not request.authenticators):
            raise BBPSBaseException(
                status_code=400,
                message="Validation failed: Either 'billeraccountid' OR a combination of 'billerid' and 'authenticators' must be provided.",
                error_code="ERR_VALIDATION_FAILED",
                error_type="validation_error"
            )

        # 2. Query and Validate Biller
        resolved_biller_id = request.billerid
        if not resolved_biller_id and request.billeraccountid:
            # Try to resolve Biller ID from favorite billers if not provided
            stmt = select(FavoriteBiller).filter_by(
                billeraccountid=request.billeraccountid,
                customer_id=customer_id,
                status="ACTIVE"
            )
            res = await session.execute(stmt)
            fav_biller = res.scalar_one_or_none()
            if fav_biller:
                resolved_biller_id = fav_biller.biller_id
            else:
                raise BBPSBaseException(
                    status_code=400,
                    message="Validation failed: Biller ID must be provided for ad-hoc bill fetch when the account is not registered.",
                    error_code="ERR_BILLER_ID_REQUIRED",
                    error_type="validation_error"
                )

        biller = await BillerRepository.get_by_biller_id(session, resolved_biller_id)
        if not biller:
            logger.warning(f"Biller not found in database: {resolved_biller_id}")
            raise BillerNotFoundError(resolved_biller_id)

        # Check if biller is active
        metadata_dict = biller.biller_metadata or {}
        active_status = metadata_dict.get("active_status", "ACTIVE")
        if str(active_status).strip().upper() == "INACTIVE":
            logger.warning(f"Biller is inactive: {resolved_biller_id}")
            raise BBPSBaseException(
                status_code=400,
                message="Biller is currently inactive.",
                error_code="ERR_BILLER_INACTIVE",
                error_type="biller_status_error"
            )

        biller_name = biller.biller_name
        biller_category = biller.category

        # Dynamic Authenticator Validation based on Biller Category
        if request.authenticators:
            category_upper = biller_category.upper()
            for auth in request.authenticators:
                val = str(auth.value).strip()
                if "ELECT" in category_upper:
                    if not val.isdigit() or len(val) < 6:
                        logger.warning(f"Authenticator validation failed: Invalid Consumer Number '{val}' for Electricity biller '{resolved_biller_id}'")
                        raise BBPSBaseException(
                            status_code=400,
                            message=f"Validation failed: Consumer Number '{val}' must be numeric and at least 6 digits for Electricity biller.",
                            error_code="ERR_AUTHENTICATOR_INVALID",
                            error_type="validation_error"
                        )
                elif "TELE" in category_upper or "MOBILE" in category_upper:
                    if not val.isdigit() or len(val) != 10:
                        logger.warning(f"Authenticator validation failed: Invalid Mobile Number '{val}' for Telecom biller '{resolved_biller_id}'")
                        raise BBPSBaseException(
                            status_code=400,
                            message=f"Validation failed: Mobile Number '{val}' must be a valid 10-digit number for Telecom biller.",
                            error_code="ERR_AUTHENTICATOR_INVALID",
                            error_type="validation_error"
                        )
                elif "GAS" in category_upper:
                    if len(val) < 5:
                        logger.warning(f"Authenticator validation failed: Invalid Customer ID '{val}' for Gas biller '{resolved_biller_id}'")
                        raise BBPSBaseException(
                            status_code=400,
                            message=f"Validation failed: Gas Account Number/Customer ID '{val}' must be at least 5 characters.",
                            error_code="ERR_AUTHENTICATOR_INVALID",
                            error_type="validation_error"
                        )

        # Audit event log for incoming fetch request metadata
        agent_id = request.metadata.agent.agentid if request.metadata and request.metadata.agent else "N/A"
        device_ip = request.metadata.device.ip if request.metadata and request.metadata.device else "N/A"
        logger.info(f"[AUDIT TRAIL] Fetch request authenticated: Biller: {resolved_biller_id} | Agent: {agent_id} | Client IP: {device_ip}")

        # 3. Auto-enrich Customer
        from app.database.models import User
        from app.schemas.common_schema import Customer
        stmt = select(User).where(User.username.ilike(customer_id))
        res = await session.execute(stmt)
        db_user = res.scalar_one_or_none()
        if db_user:
            customer = Customer(
                firstname=db_user.username.capitalize(),
                lastname="Customer",
                mobile="9876543210",
                email=db_user.email
            )
        else:
            customer = Customer(
                firstname="Ashutos",
                lastname="Satapathy",
                mobile="9876543210",
                email="ashutos@test.com"
            )

        # 4. Auto-enrich Metadata
        from app.schemas.common_schema import Metadata, Agent, Device
        metadata = Metadata(
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

        # 5. Resolve Authenticators and Biller Account ID
        resolved_biller_account_id = request.billeraccountid or (request.authenticators[0].value if request.authenticators else "RELEN155187")
        
        from app.schemas.common_schema import Authenticator
        if request.authenticators:
            auths = request.authenticators
        else:
            if biller_category == "Electricity":
                auths = [Authenticator(seq="1", parameter_name="Consumer Number", value="123456789")]
            elif biller_category == "Telecom":
                auths = [Authenticator(seq="1", parameter_name="Mobile Number", value="9876543210")]
            elif biller_category == "Water":
                auths = [Authenticator(seq="1", parameter_name="Consumer ID", value="987654321")]
            elif biller_category == "Gas":
                auths = [Authenticator(seq="1", parameter_name="Gas Account Number", value="GAS9876543")]
            else:
                auths = [Authenticator(seq="1", parameter_name="Consumer Number", value="1234567890")]

        # 6. Generate validation credentials with UTC ISO-8601 formatting
        validation_id = f"VAL-{str(uuid.uuid4().int)[:5]}"
        now_utc = datetime.now(timezone.utc)
        validation_date = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        valid_until = (now_utc + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")

        # 7. Simulate Outstanding Amount & Bill Retrieval based on dataset
        min_val = float(metadata_dict.get("min_amount", "10.00"))
        max_val = float(metadata_dict.get("max_amount", "500000.00"))
        
        if biller_category == "Electricity":
            amount = "2500"
        elif biller_category == "Water":
            amount = "650"
        elif biller_category == "Telecom":
            amount = "399"
        elif biller_category == "Broadband":
            amount = "899"
        elif biller_category == "Gas":
            amount = "1200"
        else:
            amount = f"{int(min(max(min_val + 240.0, min_val), max_val))}"

        # Generate realistic past bill date (-15 days) and future due date (+15 days)
        bill_date_str = (now_utc - timedelta(days=15)).strftime("%d-%m-%Y")
        due_date_str = (now_utc + timedelta(days=15)).strftime("%d-%m-%Y")

        bill_item = BillItem(
            billid=str(uuid.uuid4().int)[:9],
            billerid=resolved_biller_id,
            billperiod=now_utc.strftime("%B"),
            customer_name=f"{customer.firstname} {customer.lastname}",
            billeraccountid=resolved_biller_account_id,
            authenticators=[{"name": a.parameter_name, "value": a.value} for a in auths],
            billnumber=f"BILL-{str(uuid.uuid4().int)[:9]}",
            billdate=bill_date_str,
            billduedate=due_date_str,
            billamount=amount,
            net_billamount=amount,
            description=f"Bill payment for {biller_name}",
            billstatus="UNPAID"
        )

        response = FetchBillResponse(
            sourceid=source_id,
            customerid=customer_id,
            validationid=validation_id,
            validation_date=validation_date,
            valid_until=valid_until,
            billerid=resolved_biller_id,
            biller_name=biller_name,
            biller_category=biller_category,
            authenticators=auths,
            payment_amount=amount,
            billlist=[bill_item],
            pay_multiple_bills="N",
            additional_validation_details=[
                {"parameter_name": "Recharge Type", "value": "1"}
            ]
        )

        # 8. Persist the validation session in the transaction log database
        from app.database.models import TransactionLog
        from app.core.constants import TransactionState

        # Build full request payload structure for logging and downstream use
        log_request_payload = {
            "billerid": resolved_biller_id,
            "billeraccountid": resolved_biller_account_id,
            "customer": {
                "firstname": customer.firstname,
                "lastname": customer.lastname,
                "mobile": customer.mobile,
                "email": customer.email
            },
            "metadata": {
                "agent": {"agentid": "AGENT001", "sub_agentid": "SUBAG001"},
                "device": {
                    "init_channel": "MOBILE_APP",
                    "ip": "192.168.1.10",
                    "mac": "AA:BB:CC:DD:EE:FF",
                    "os": "Windows 11",
                    "app": "BBPS NextGen",
                    "user_agent": "Mozilla/5.0"
                }
            },
            "authenticators": [{"seq": a.seq, "parameter_name": a.parameter_name, "value": a.value} for a in auths]
        }

        tx_log = TransactionLog(
            id=uuid.uuid4(),
            trace_id=f"VAL-TR-{str(uuid.uuid4().int)[:12]}",
            customer_id=customer_id,
            biller_id=resolved_biller_id,
            amount=float(amount),
            transaction_state=TransactionState.INITIALIZED,
            request_payload=log_request_payload,
            response_payload=response.model_dump(mode="json")
        )
        session.add(tx_log)
        await session.commit()

        logger.info(f"Fetch Bill successfully completed for validation ID: {validation_id}")
        return response

