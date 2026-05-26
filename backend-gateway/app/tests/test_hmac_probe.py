import pytest
import time
import uuid
import json
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings
from app.core.security import calculate_hmac_sha256
from app.utils.json_canonicalizer import canonicalize_bytes
from app.database.db import engine

def compute_signature(payload: dict, timestamp: str, nonce: str, secret: str) -> str:
    payload_bytes = json.dumps(payload, separators=(',', ':'), sort_keys=True).encode("utf-8")
    canonical_body = canonicalize_bytes(payload_bytes)
    sig_payload = canonical_body + timestamp.encode("utf-8") + nonce.encode("utf-8")
    return calculate_hmac_sha256(sig_payload, secret)

@pytest.mark.asyncio
async def test_hmac_probe_stateless_flows():
    """
    Tests various cryptographic validation flows through the stateless /demo/hmac-probe endpoint.
    Also verifies that the audit logs are correctly populated and retrievable.
    """
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {"trace_id": "TXN-test-789", "amount": 2500.0}
            timestamp = str(int(time.time()))
            nonce = str(uuid.uuid4())
            secret = settings.MBANKING_CLIENT_SECRET
            
            sig = compute_signature(payload, timestamp, nonce, secret)
            
            # 1. Test VALID request
            probe_res = await ac.post(
                "/demo/hmac-probe",
                json=payload,
                headers={
                    "X-Signature": sig,
                    "X-Timestamp": timestamp,
                    "X-Nonce": nonce,
                    "X-Source-Id": "mbanking"
                }
            )
            assert probe_res.status_code == 200
            assert probe_res.json() == {
                "success": True,
                "status": "VALID",
                "message": "Payload integrity verified"
            }
            
            # 2. Test REPLAY attack (reuse SAME nonce, timestamp, and signature)
            probe_res_dup = await ac.post(
                "/demo/hmac-probe",
                json=payload,
                headers={
                    "X-Signature": sig,
                    "X-Timestamp": timestamp,
                    "X-Nonce": nonce,
                    "X-Source-Id": "mbanking"
                }
            )
            assert probe_res_dup.status_code == 401
            assert probe_res_dup.json()["status"] == "REPLAY_ATTACK"
            
            # 3. Test TAMPERED request (modify payload without recomputing signature)
            tampered_payload = {"trace_id": "TXN-test-789", "amount": 2501.0}
            new_nonce = str(uuid.uuid4())
            probe_res_tampered = await ac.post(
                "/demo/hmac-probe",
                json=tampered_payload,
                headers={
                    "X-Signature": sig,
                    "X-Timestamp": timestamp,
                    "X-Nonce": new_nonce,
                    "X-Source-Id": "mbanking"
                }
            )
            assert probe_res_tampered.status_code == 401
            assert probe_res_tampered.json()["status"] == "TAMPERED"

            # 4. Test SKEWED/expired timestamp
            expired_timestamp = str(int(time.time()) - 600)
            expired_sig = compute_signature(payload, expired_timestamp, new_nonce, secret)
            probe_res_expired = await ac.post(
                "/demo/hmac-probe",
                json=payload,
                headers={
                    "X-Signature": expired_sig,
                    "X-Timestamp": expired_timestamp,
                    "X-Nonce": new_nonce,
                    "X-Source-Id": "mbanking"
                }
            )
            assert probe_res_expired.status_code == 401
            assert probe_res_expired.json()["status"] == "EXPIRED_TIMESTAMP"

            # 5. Fetch and verify Audit Logs
            logs_res = await ac.get("/demo/hmac-probe/audit-logs")
            assert logs_res.status_code == 200
            logs = logs_res.json()
            assert len(logs) >= 4
            
            # Verify statuses correspond to requests in order
            assert logs[0]["status"] == "VALID"
            assert logs[1]["status"] == "REPLAY_ATTACK"
            assert logs[2]["status"] == "TAMPERED"
            assert logs[3]["status"] == "EXPIRED_TIMESTAMP"
            
            # Verify details match
            assert logs[0]["trace_id"] == "TXN-test-789"
            assert logs[0]["amount"] == 2500.0
            assert logs[2]["amount"] == 2501.0
    finally:
        await engine.dispose()
