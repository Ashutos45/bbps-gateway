import pytest
import time
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.auth.jwt_handler import create_access_token
from app.auth.token_service import generate_signed_download_token
from app.database.db import engine
from datetime import timedelta

@pytest.mark.asyncio
async def test_jwt_login_flow():
  """
  Tests exchanging credentials for a valid JWT token and authenticating requests.
  """
  try:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
      # 1. Login request with admin credentials
      login_payload = {"username": "admin", "password": "admin123"}
      login_res = await ac.post("/auth/token", json=login_payload)
      assert login_res.status_code == 200
      
      auth_data = login_res.json()
      assert "access_token" in auth_data
      assert auth_data["role"] == "ADMIN"
      
      jwt_token = auth_data["access_token"]
      
      # 2. Access protected endpoint (e.g. telemetry requires ADMIN or AUDITOR role)
      # Wait, is telemetry protected in our code?
      # Let's check: GET /telemetry is currently public in main.py, but biller master file routes are protected.
      # Biller master file post route requires Role.ADMIN.
      url_init = "/BOBCOU/BBPS/mbanking/billpay/billers/file"
      body = {"callbackUrl": "http://localhost:8000/callback/file"}
      headers = {"Authorization": f"Bearer {jwt_token}"}
      
      res_init = await ac.post(url_init, json=body, headers=headers)
      # Bypasses HMAC headers check in middleware.py if headers are not present?
      # Wait! Does it bypass HMAC for `/billers/file`? No, it matches ROUTE_REGEX and doesn't end with `/billers/stream`!
      # Ah! So `/billers/file` still requires HMAC headers!
      # We must include valid HMAC headers along with JWT header for `/billers/file`!
      # Let's import generate_signed_headers helper to construct it.
      from app.tests.test_integration import generate_signed_headers
      import json
      
      # Build body bytes
      payload_bytes = json.dumps(body).encode("utf-8")
      hmac_headers = generate_signed_headers(payload_bytes, "mbanking")
      
      # Merge JWT into headers
      hmac_headers["Authorization"] = f"Bearer {jwt_token}"
      
      res_init_hmac = await ac.post(url_init, json=body, headers=hmac_headers)
      # Since we don't have the file worker fully started here, it might return 200/403 depending on role.
      # If role is ADMIN, it will succeed (status 200).
      assert res_init_hmac.status_code == 200
  finally:
    await engine.dispose()

@pytest.mark.asyncio
async def test_rbac_boundary_restrictions():
  """
  Tests role restrictions. Operator/Auditor/Client should be blocked from initiating file generation.
  """
  try:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
      # 1. Login as operator
      login_res = await ac.post("/auth/token", json={"username": "operator", "password": "operator123"})
      operator_token = login_res.json()["access_token"]
      
      url_init = "/BOBCOU/BBPS/mbanking/billpay/billers/file"
      body = {"callbackUrl": "http://localhost:8000/callback/file"}
      
      # Build valid HMAC headers
      from app.tests.test_integration import generate_signed_headers
      import json
      payload_bytes = json.dumps(body).encode("utf-8")
      hmac_headers = generate_signed_headers(payload_bytes, "mbanking")
      hmac_headers["Authorization"] = f"Bearer {operator_token}"
      
      # 2. Trigger generation as Operator (Should return 403 Forbidden)
      res_operator = await ac.post(url_init, json=body, headers=hmac_headers)
      assert res_operator.status_code == 403
      assert "Insufficient permissions" in res_operator.json()["detail"]

      # 3. Access stream endpoint as Auditor (Auditor role does not inherit Client or Admin access)
      stream_url = "/BOBCOU/BBPS/mbanking/billpay/billers/stream"
      login_res_auditor = await ac.post("/auth/token", json={"username": "auditor", "password": "auditor123"})
      auditor_token = login_res_auditor.json()["access_token"]
      
      res_auditor = await ac.get(stream_url, headers={"Authorization": f"Bearer {auditor_token}"})
      assert res_auditor.status_code == 403
  finally:
    await engine.dispose()

@pytest.mark.asyncio
async def test_api_key_authentication():
  """
  Tests authenticating database stream using API Keys.
  """
  try:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
      stream_url = "/BOBCOU/BBPS/mbanking/billpay/billers/stream"
      
      # 1. Invalid API Key
      res_invalid = await ac.get(stream_url, headers={"X-API-Key": "WRONG_KEY"})
      assert res_invalid.status_code == 401
      
      # 2. Valid API Key for CLIENT (Allowed role)
      res_valid = await ac.get(stream_url, headers={"X-API-Key": "client_key_123"})
      assert res_valid.status_code == 200
  finally:
    await engine.dispose()

@pytest.mark.asyncio
async def test_expired_jwt_and_download_tokens():
  """
  Tests rejections of expired JWT and download signature tokens.
  """
  try:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
      # 1. Create immediately expired JWT
      expired_jwt = create_access_token(
        data={"sub": "test_user", "role": "CLIENT"},
        expires_delta=timedelta(seconds=-10) # Expired 10 seconds ago
      )
      
      stream_url = "/BOBCOU/BBPS/mbanking/billpay/billers/stream"
      res_expired_jwt = await ac.get(stream_url, headers={"Authorization": f"Bearer {expired_jwt}"})
      assert res_expired_jwt.status_code == 401
      assert "token has expired" in res_expired_jwt.json()["detail"].lower()

      # 2. Create immediately expired download token
      expired_download_token = generate_signed_download_token(
        file_id="HGA12345",
        client_id="test_client",
        expires_in_sec=-10 # Expired
      )
      
      download_url = "/download/file/HGA12345"
      res_expired_download = await ac.get(download_url, params={"token": expired_download_token})
      assert res_expired_download.status_code == 401
      assert "expired signed url token" in res_expired_download.json()["detail"].lower()
  finally:
    await engine.dispose()
