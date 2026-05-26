import pytest
import time
import uuid
import asyncio
import base64
from httpx import AsyncClient, ASGITransport
from sqlalchemy import delete, select
from app.main import app
from app.core.config import settings
from app.core.security import calculate_hmac_sha256
from app.utils.json_canonicalizer import canonicalize_bytes
from app.database.db import AsyncSessionLocal, engine
from app.database.models import TransactionLog, FavoriteBiller, NonceRegistry, ReconciliationLog, Biller
from app.database.repositories.biller_repository import BillerRepository
from app.core.constants import TransactionState
from app.workers.file_generation_worker import FileGenerationWorker

def generate_signed_headers(payload_bytes: bytes, source_id: str = "mbanking") -> dict:
    """
    Helper to calculate timestamp, nonce, and HMAC-SHA256 signature for test requests.
    """
    timestamp = str(int(time.time()))
    nonce = str(uuid.uuid4())
    config = settings.get_channel_config(source_id)
    secret = config["client_secret"]
    
    canonical_body = canonicalize_bytes(payload_bytes) if payload_bytes else b""
    sig_payload = canonical_body + timestamp.encode("utf-8") + nonce.encode("utf-8")
    signature = calculate_hmac_sha256(sig_payload, secret)
    
    return {
        "x-timestamp": timestamp,
        "x-nonce": nonce,
        "x-signature": signature,
        "x-trace-id": f"trace-{uuid.uuid4().hex[:8]}"
    }

async def setup_clean_db():
    """
    Resets the database tables and seeds the required test biller.
    """
    async with AsyncSessionLocal() as session:
        await session.execute(delete(FavoriteBiller))
        await session.execute(delete(TransactionLog))
        await session.execute(delete(ReconciliationLog))
        await session.execute(delete(NonceRegistry))
        await session.execute(delete(Biller).where(Biller.biller_id == "UPPCL0000UTP01"))
        await session.commit()

    async with AsyncSessionLocal() as session:
        await BillerRepository.seed_billers(session, [
            {
                "biller_id": "UPPCL0000UTP01",
                "biller_name": "Uttar Pradesh Power Corp Ltd - URBAN",
                "category": "Electricity",
                "region": "Uttar Pradesh",
                "metadata": {"min_amount": "10.00", "max_amount": "50000.00"}
            }
        ])
        await session.commit()


@pytest.mark.asyncio
async def test_health_check_endpoint():
    """
    Verifies that the public /health API is online and doesn't require HMAC signing.
    """
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/health")
            assert response.status_code == 200
            assert response.json()["status"] == "success"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_hmac_tampering_rejection():
    """
    Verifies that requests are rejected with 401 if signature is tampered or header missing.
    """
    try:
        await setup_clean_db()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            url = "/BOBCOU/BBPS/mbanking/customers/cust123/billpay/validate"
            body = {
                "billerid": "UPPCL0000UTP01",
                "authenticators": [{"seq": "1", "parameter_name": "Consumer No", "value": "123456"}],
                "customer": {"firstname": "John", "lastname": "Doe", "mobile": "9999999999"},
                "metadata": {
                    "agent": {"agentid": "AGT001"},
                    "device": {"init_channel": "Internet"}
                }
            }
            
            # 1. Missing headers
            res_no_headers = await ac.post(url, json=body)
            assert res_no_headers.status_code == 401
            assert "Required security headers" in res_no_headers.json()["message"]

            # 2. Tampered signature
            payload_bytes = ac.build_request("POST", url, json=body).content
            headers = generate_signed_headers(payload_bytes, "mbanking")
            headers["x-signature"] = "WRONGSIGNATURE"
            
            res_tampered = await ac.post(url, json=body, headers=headers)
            assert res_tampered.status_code == 401
            assert "signature verification failed" in res_tampered.json()["message"].lower()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_biller_master_generation_flow():
    """
    Tests the Biller Master File generation and retrieval sequence.
    """
    try:
        await setup_clean_db()
        FileGenerationWorker.start()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            url_init = "/BOBCOU/BBPS/mbanking/billpay/billers/file"
            body = {"callbackUrl": "http://localhost:8000/callback/file"}
            
            payload_bytes = ac.build_request("POST", url_init, json=body).content
            headers = generate_signed_headers(payload_bytes, "mbanking")
            headers["X-API-Key"] = "admin_key_123"
            
            # Initiate generation
            res_init = await ac.post(url_init, json=body, headers=headers)
            assert res_init.status_code == 200
            res_data = res_init.json()
            assert res_data["objectid"] == "file"
            assert res_data["file_status"] == "INPROCESS"
            assert "fileid" in res_data
            
            file_id = res_data["fileid"]
            
            # Poll status and wait for background zip compilation task to finish
            url_get = f"/BOBCOU/BBPS/mbanking/billpay/billers/file/{file_id}"
            max_retries = 20
            completed = False
            file_data = {}
            for _ in range(max_retries):
                headers_get = generate_signed_headers(b"", "mbanking")
                headers_get["X-API-Key"] = "admin_key_123"
                res_get = await ac.get(url_get, headers=headers_get)
                assert res_get.status_code == 200
                file_data = res_get.json()
                if file_data.get("status") == 0:
                    completed = True
                    break
                await asyncio.sleep(0.5)

            assert completed, f"File compilation did not complete in time: {file_data}"
            assert file_data["fileName"] == f"{file_id}.zip"
            assert "fileContent" in file_data
            
            # Verify base64 decodes to zip header
            zip_bytes = base64.b64decode(file_data["fileContent"])
            assert zip_bytes.startswith(b"PK")  # ZIP magic bytes
    finally:
        await FileGenerationWorker.stop()
        await engine.dispose()


@pytest.mark.asyncio
async def test_prepaid_plans_endpoint():
    """
    Tests retrieving mobile prepaid plans.
    """
    try:
        await setup_clean_db()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            url = "/BOBCOU/BBPS/mbanking/billpay/plans"
            params = {
                "billerid": "UPPCL0000UTP01",
                "circle_name": "Delhi",
                "plan_id": "PLAN001",
                "plan_category_name": "Unlimited"
            }
            
            headers = generate_signed_headers(b"", "mbanking")
            response = await ac.get(url, params=params, headers=headers)
            assert response.status_code == 200
            plans = response.json()
            assert len(plans) == 1
            assert plans[0]["planid"] == "PLAN001"
            assert plans[0]["talktime"] == "100"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_favorite_billers_crud_flow():
    """
    Verifies registration, fetching, updating, and deactivation of favorite biller accounts.
    """
    try:
        await setup_clean_db()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            url_base = "/BOBCOU/BBPS/mbanking/customers/9999988888/billpay/billeraccounts"
            
            # 1. Create Favorite Biller
            body_add = {
                "billerid": "UPPCL0000UTP01",
                "short_name": "Home Electricity",
                "authenticators": [{"seq": "1", "parameter_name": "Consumer No", "value": "987654"}],
                "autopay_status": "Y",
                "autopay_amount": 1000.0,
                "frequency": "Monthly"
            }
            payload_bytes = ac.build_request("POST", url_base, json=body_add).content
            headers = generate_signed_headers(payload_bytes, "mbanking")
            
            res_add = await ac.post(url_base, json=body_add, headers=headers)
            assert res_add.status_code == 200
            res_data = res_add.json()
            assert res_data["billerid"] == "UPPCL0000UTP01"
            assert res_data["short_name"] == "Home Electricity"
            assert res_data["autopay_status"] == "Y"
            assert "billeraccountid" in res_data
            
            biller_acc_id = res_data["billeraccountid"]

            # 2. Get Favorite Billers
            headers_get = generate_signed_headers(b"", "mbanking")
            res_get = await ac.get(url_base, headers=headers_get)
            assert res_get.status_code == 200
            billers = res_get.json()
            assert len(billers) >= 1
            assert any(b["billeraccountid"] == biller_acc_id for b in billers)

            # 3. Update Favorite Biller
            url_item = f"{url_base}/{biller_acc_id}"
            body_update = {
                "short_name": "My Vacation Home",
                "autopay_amount": 1500.0
            }
            payload_update_bytes = ac.build_request("PUT", url_item, json=body_update).content
            headers_put = generate_signed_headers(payload_update_bytes, "mbanking")
            
            res_put = await ac.put(url_item, json=body_update, headers=headers_put)
            assert res_put.status_code == 200
            assert res_put.json()["short_name"] == "My Vacation Home"
            assert res_put.json()["autopay_amount"] == 1500.0

            # 4. Delete Favorite Biller
            headers_del = generate_signed_headers(b"", "mbanking")
            res_del = await ac.delete(url_item, headers=headers_del)
            assert res_del.status_code == 200
            assert res_del.json()["status"] == "DELETED"
            assert "deletion_date" in res_del.json()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_fetch_bill_and_successful_payment():
    """
    Validates a successful end-to-end bill fetch and payment flow.
    """
    try:
        await setup_clean_db()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Fetch Bill
            url_fetch = "/BOBCOU/BBPS/mbanking/customers/9999988888/billpay/validate"
            body_fetch = {
                "billerid": "UPPCL0000UTP01",
                "authenticators": [{"seq": "1", "parameter_name": "Consumer No", "value": "123456"}],
                "customer": {"firstname": "John", "lastname": "Doe", "mobile": "9999988888"},
                "metadata": {
                    "agent": {"agentid": "AGT001"},
                    "device": {"init_channel": "Internet"}
                }
            }
            payload_fetch_bytes = ac.build_request("POST", url_fetch, json=body_fetch).content
            headers_fetch = generate_signed_headers(payload_fetch_bytes, "mbanking")
            
            res_fetch = await ac.post(url_fetch, json=body_fetch, headers=headers_fetch)
            assert res_fetch.status_code == 200
            fetch_data = res_fetch.json()
            assert fetch_data["billerid"] == "UPPCL0000UTP01"
            assert "validationid" in fetch_data
            validation_id = fetch_data["validationid"]

            # 2. Pay Bill (Force success)
            url_pay = "/BOBCOU/BBPS/mbanking/customers/9999988888/billpay/payments"
            trace_id = f"pay-{uuid.uuid4().hex[:12]}"
            body_pay = {
                "billerid": "UPPCL0000UTP01",
                "validationid": validation_id,
                "payment_amount": "920.00",
                "debit_amount": "920.00",
                "payment_type": "billpay",
                "source_ref_no": trace_id,
                "customer": {"firstname": "John", "lastname": "Doe", "mobile": "9999988888"},
                "metadata": {
                    "agent": {"agentid": "AGT001"},
                    "device": {"init_channel": "Internet"}
                },
                "payment_account": {
                    "payment_method": "CreditCard",
                    "cardholder_name": "John Doe"
                }
            }
            payload_pay_bytes = ac.build_request("POST", url_pay, json=body_pay).content
            headers_pay = generate_signed_headers(payload_pay_bytes, "mbanking")
            headers_pay["x-simulate-failure"] = "false"
            
            res_pay = await ac.post(url_pay, json=body_pay, headers=headers_pay)
            assert res_pay.status_code == 200
            pay_data = res_pay.json()
            assert pay_data["status"] == "SETTLED"
            assert pay_data["source_ref_no"] == trace_id
            assert "payment_reference" in pay_data

            # 3. Test concurrent payment idempotency
            headers_pay_dup = generate_signed_headers(payload_pay_bytes, "mbanking")
            headers_pay_dup["x-simulate-failure"] = "false"
            res_dup = await ac.post(url_pay, json=body_pay, headers=headers_pay_dup)
            assert res_dup.status_code == 200
            assert res_dup.json()["status"] == "SETTLED"
            assert res_dup.json()["payment_reference"] == pay_data["payment_reference"]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_minimal_payload_fetch_and_payment():
    """
    Verifies that minimal request payloads for both Fetch Bill and Pay Bill
    are automatically enriched by the backend and execute successfully.
    """
    try:
        await setup_clean_db()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Minimal Fetch Bill
            url_fetch = "/BOBCOU/BBPS/mbanking/customers/9999988888/billpay/validate"
            body_fetch = {
                "billerid": "UPPCL0000UTP01",
                "billeraccountid": "ELEC987654321"
            }
            payload_fetch_bytes = ac.build_request("POST", url_fetch, json=body_fetch).content
            headers_fetch = generate_signed_headers(payload_fetch_bytes, "mbanking")
            
            res_fetch = await ac.post(url_fetch, json=body_fetch, headers=headers_fetch)
            assert res_fetch.status_code == 200
            fetch_data = res_fetch.json()
            assert fetch_data["billerid"] == "UPPCL0000UTP01"
            assert "validationid" in fetch_data
            validation_id = fetch_data["validationid"]
            payment_amount = fetch_data["payment_amount"]
            assert payment_amount == "2500"  # Since category is Electricity, simulated amount should be 2500

            # 2. Minimal Pay Bill
            url_pay = "/BOBCOU/BBPS/mbanking/customers/9999988888/billpay/payments"
            body_pay = {
                "validationid": validation_id,
                "payment_amount": payment_amount,
                "payment_method": "CARD"
            }
            payload_pay_bytes = ac.build_request("POST", url_pay, json=body_pay).content
            headers_pay = generate_signed_headers(payload_pay_bytes, "mbanking")
            headers_pay["x-simulate-failure"] = "false"
            
            res_pay = await ac.post(url_pay, json=body_pay, headers=headers_pay)
            assert res_pay.status_code == 200
            pay_data = res_pay.json()
            assert pay_data["status"] == "SETTLED"
            assert "source_ref_no" in pay_data
            assert pay_data["payment_amount"] == payment_amount
            assert pay_data["debit_amount"] == payment_amount
            assert "payment_reference" in pay_data
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_payment_failure_simulation_and_oneview_reconciliation():
    """
    Tests network failure drop simulation resulting in AMBIGUOUS_TIMEOUT,
    and subsequent resolution via OneView API on-the-fly reconciliation.
    """
    try:
        await setup_clean_db()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Pay with forced failure
            url_pay = "/BOBCOU/BBPS/mbanking/customers/9999977777/billpay/payments"
            trace_id = f"pay-{uuid.uuid4().hex[:12]}"
            body_pay = {
                "billerid": "UPPCL0000UTP01",
                "validationid": "VALIDATE123",
                "payment_amount": "500.00",
                "debit_amount": "500.00",
                "payment_type": "billpay",
                "source_ref_no": trace_id,
                "customer": {"firstname": "Alice", "lastname": "Smith", "mobile": "9999977777"},
                "metadata": {
                    "agent": {"agentid": "AGT001"},
                    "device": {"init_channel": "Internet"}
                },
                "payment_account": {
                    "payment_method": "DebitCard",
                    "cardholder_name": "Alice Smith"
                }
            }
            
            payload_pay_bytes = ac.build_request("POST", url_pay, json=body_pay).content
            headers_pay = generate_signed_headers(payload_pay_bytes, "mbanking")
            headers_pay["x-simulate-failure"] = "true"
            
            res_pay = await ac.post(url_pay, json=body_pay, headers=headers_pay)
            assert res_pay.status_code == 504
            assert "Transaction status is ambiguous" in res_pay.json()["message"]

            # 2. Check that database record is in AMBIGUOUS_TIMEOUT state
            async with AsyncSessionLocal() as session:
                stmt = select(TransactionLog).filter_by(trace_id=trace_id)
                res = await session.execute(stmt)
                tx = res.scalar_one()
                assert tx.transaction_state == TransactionState.AMBIGUOUS_TIMEOUT

            # 3. Call OneView API to resolve on-the-fly
            url_oneview = "/BOBCOU/BBPS/mbanking/customers/9999977777/billpay/oneview"
            headers_ov = generate_signed_headers(b"", "mbanking")
            
            res_ov = await ac.get(url_oneview, headers=headers_ov)
            assert res_ov.status_code == 200
            ov_data = res_ov.json()
            assert ov_data["customerid"] == "9999977777"
            assert ov_data["total_transactions"] >= 1
            
            # Verify the transaction was resolved
            tx_item = next(t for t in ov_data["transactions"] if t["trace_id"] == trace_id)
            assert tx_item["transaction_state"] in ("SETTLED", "FAILED")
            assert tx_item["reconciliation_log"] is not None
            assert tx_item["reconciliation_log"]["reconciliation_status"] == "RESOLVED"
            assert tx_item["reconciliation_log"]["polling_attempts"] == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_manual_reconciliation_endpoint():
    """
    Tests manual reconciliation API route.
    """
    try:
        await setup_clean_db()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Trigger simulated timeout
            url_pay = "/BOBCOU/BBPS/mbanking/customers/9999966666/billpay/payments"
            trace_id = f"pay-{uuid.uuid4().hex[:12]}"
            body_pay = {
                "billerid": "UPPCL0000UTP01",
                "validationid": "VALIDATE123",
                "payment_amount": "450.00",
                "debit_amount": "450.00",
                "payment_type": "billpay",
                "source_ref_no": trace_id,
                "customer": {"firstname": "Bob", "lastname": "Jones", "mobile": "9999966666"},
                "metadata": {
                    "agent": {"agentid": "AGT001"},
                    "device": {"init_channel": "Internet"}
                },
                "payment_account": {
                    "payment_method": "NetBanking",
                    "cardholder_name": "Bob Jones"
                }
            }
            payload_pay_bytes = ac.build_request("POST", url_pay, json=body_pay).content
            headers_pay = generate_signed_headers(payload_pay_bytes, "mbanking")
            headers_pay["x-simulate-failure"] = "true"
            await ac.post(url_pay, json=body_pay, headers=headers_pay)

            # 2. Trigger manual reconcile
            url_rec = "/BOBCOU/BBPS/mbanking/billpay/reconcile"
            body_rec = {"trace_id": trace_id}
            payload_rec_bytes = ac.build_request("POST", url_rec, json=body_rec).content
            headers_rec = generate_signed_headers(payload_rec_bytes, "mbanking")
            
            res_rec = await ac.post(url_rec, json=body_rec, headers=headers_rec)
            assert res_rec.status_code == 200
            rec_data = res_rec.json()
            assert rec_data["trace_id"] == trace_id
            assert rec_data["reconciliation_status"] == "RESOLVED"
            assert rec_data["resolved_state"] in ("SETTLED", "FAILED")
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_telemetry_and_metrics_exposition():
    """
    Tests retrieval of JSON telemetry and Prometheus text metrics.
    """
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Telemetry JSON
            res_tel = await ac.get("/telemetry")
            assert res_tel.status_code == 200
            tel_data = res_tel.json()
            assert tel_data["total_requests"] > 0
            assert "success_rate" in tel_data
            
            # Telemetry Prometheus Metrics
            res_met = await ac.get("/metrics")
            assert res_met.status_code == 200
            text = res_met.text
            assert "bbps_requests_total" in text
            assert "bbps_hmac_failures_total" in text
            assert "bbps_replay_attacks_total" in text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_pay_bill_minimal_no_amount():
    """
    Verifies that Pay Bill succeeds even when payment_amount is missing from
    the request body by retrieving it from the validation log.
    """
    try:
        await setup_clean_db()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Fetch Bill (create validation session)
            url_fetch = "/BOBCOU/BBPS/mbanking/customers/9999988888/billpay/validate"
            body_fetch = {
                "billerid": "UPPCL0000UTP01",
                "billeraccountid": "ELEC987654321"
            }
            payload_fetch_bytes = ac.build_request("POST", url_fetch, json=body_fetch).content
            headers_fetch = generate_signed_headers(payload_fetch_bytes, "mbanking")
            res_fetch = await ac.post(url_fetch, json=body_fetch, headers=headers_fetch)
            assert res_fetch.status_code == 200
            validation_id = res_fetch.json()["validationid"]

            # 2. Pay Bill with minimal payload (no payment_amount)
            url_pay = "/BOBCOU/BBPS/mbanking/customers/9999988888/billpay/payments"
            body_pay = {
                "validationid": validation_id,
                "payment_method": "CARD"
            }
            payload_pay_bytes = ac.build_request("POST", url_pay, json=body_pay).content
            headers_pay = generate_signed_headers(payload_pay_bytes, "mbanking")
            headers_pay["x-simulate-failure"] = "false"
            res_pay = await ac.post(url_pay, json=body_pay, headers=headers_pay)
            assert res_pay.status_code == 200
            pay_data = res_pay.json()
            assert pay_data["status"] == "SETTLED"
            assert pay_data["payment_amount"] == "2500"  # Dynamically enriched from validation!
            assert pay_data["debit_amount"] == "2500"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_favorite_biller_minimal():
    """
    Verifies that a favorite biller can be added with only a billerid,
    with other properties being auto-enriched on the backend.
    """
    try:
        await setup_clean_db()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            url = "/BOBCOU/BBPS/mbanking/customers/9999988888/billpay/billeraccounts"
            body = {
                "billerid": "UPPCL0000UTP01"
            }
            payload_bytes = ac.build_request("POST", url, json=body).content
            headers = generate_signed_headers(payload_bytes, "mbanking")
            res = await ac.post(url, json=body, headers=headers)
            assert res.status_code == 200
            data = res.json()
            assert data["billerid"] == "UPPCL0000UTP01"
            assert data["short_name"] == "Uttar Pradesh Power Corp Ltd - URBAN"
            assert len(data["authenticators"]) == 1
            assert data["authenticators"][0]["parameter_name"] == "Consumer Number"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_prepaid_plans_by_operator_circle():
    """
    Verifies that prepaid plans are retrievable by operator name and circle via GET or POST.
    """
    try:
        await setup_clean_db()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Test POST endpoint
            url_post = "/BOBCOU/BBPS/mbanking/billpay/plans"
            body = {
                "operator": "Uttar Pradesh Power Corp Ltd - URBAN",
                "circle": "Uttar Pradesh"
            }
            payload_post_bytes = ac.build_request("POST", url_post, json=body).content
            headers_post = generate_signed_headers(payload_post_bytes, "mbanking")
            res_post = await ac.post(url_post, json=body, headers=headers_post)
            assert res_post.status_code == 200
            plans_post = res_post.json()
            assert len(plans_post) > 0
            assert plans_post[0]["biller_name"] == "Uttar Pradesh Power Corp Ltd - URBAN"
            assert plans_post[0]["circle_name"] == "Uttar Pradesh"

            # 2. Test GET endpoint with minimal query parameters
            url_get = "/BOBCOU/BBPS/mbanking/billpay/plans"
            params = {
                "operator": "Uttar Pradesh Power Corp Ltd - URBAN",
                "circle": "Uttar Pradesh"
            }
            headers_get = generate_signed_headers(b"", "mbanking")
            res_get = await ac.get(url_get, params=params, headers=headers_get)
            assert res_get.status_code == 200
            plans_get = res_get.json()
            assert len(plans_get) > 0
            assert plans_get[0]["biller_name"] == "Uttar Pradesh Power Corp Ltd - URBAN"
            assert plans_get[0]["circle_name"] == "Uttar Pradesh"
    finally:
        await engine.dispose()

