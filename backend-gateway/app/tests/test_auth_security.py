import pytest
import time
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.auth.jwt_handler import create_access_token
from app.auth.token_service import generate_signed_download_token
from app.database.db import engine
from datetime import timedelta
import uuid

@pytest.mark.asyncio
async def test_jwt_login_flow():
  """
  Tests exchanging credentials for a valid JWT token and authenticating requests.
  """
  try:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
      # 1. Login request with admin credentials
      login_payload = {
        "username": "admin", 
        "password": "admin123",
        "admin_access_key": "SUPER_KEY_123"
      }
      login_res = await ac.post("/auth/admin/token", json=login_payload)
      assert login_res.status_code == 200
      
      auth_data = login_res.json()
      assert "access_token" in auth_data
      assert auth_data["role"] == "SUPER_ADMIN"
      
      jwt_token = auth_data["access_token"]
      
      # 2. Access protected endpoint
      url_init = "/BOBCOU/BBPS/mbanking/billpay/billers/file"
      body = {"callbackUrl": "http://localhost:8000/callback/file"}
      headers = {"Authorization": f"Bearer {jwt_token}"}
      
      from app.tests.test_integration import generate_signed_headers
      import json
      
      # Build body bytes
      payload_bytes = json.dumps(body).encode("utf-8")
      hmac_headers = generate_signed_headers(payload_bytes, "mbanking")
      
      # Merge JWT into headers
      hmac_headers["Authorization"] = f"Bearer {jwt_token}"
      
      res_init_hmac = await ac.post(url_init, json=body, headers=hmac_headers)
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
      # 1. Login as operations
      login_res = await ac.post("/auth/admin/token", json={
        "username": "operations", 
        "password": "operations123",
        "admin_access_key": "OPERATIONS_KEY_123"
      })
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
      login_res_auditor = await ac.post("/auth/admin/token", json={
        "username": "auditor", 
        "password": "auditor123",
        "admin_access_key": "AUDITOR_KEY_123"
      })
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

@pytest.mark.asyncio
async def test_admin_provisioning_and_lifecycles():
  """
  Tests Admin-only provisioning, user activation/deactivation lifecycles,
  role updates, and password resets.
  """
  try:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
      # 1. Login as Super Admin
      admin_login = await ac.post("/auth/admin/token", json={
        "username": "admin", 
        "password": "admin123",
        "admin_access_key": "SUPER_KEY_123"
      })
      admin_token = admin_login.json()["access_token"]
      admin_headers = {"Authorization": f"Bearer {admin_token}"}

      # 2. Block regular client signup from adding admin users
      signup_body = {
        "username": f"client_{uuid.uuid4().hex[:4]}",
        "email": f"client_{uuid.uuid4().hex[:4]}@bbps.com",
        "password": "ClientPassword123!",
        "organization": "TestOrg"
      }
      # Public signup automatically forces CLIENT role
      res_client_signup = await ac.post("/auth/client/signup", json=signup_body)
      assert res_client_signup.status_code == 200
      
      # Try logging in as the client
      client_login = await ac.post("/auth/client/token", json={
        "username": signup_body["username"],
        "password": signup_body["password"]
      })
      assert client_login.status_code == 200
      assert client_login.json()["role"] == "CLIENT"

      # 3. Super Admin provisions a regular ADMIN user
      res_prov = await ac.post("/auth/admin/users", json={
        "username": "new_admin_user",
        "email": "new_admin@bbps.com",
        "password": "AdminPassword123!",
        "role": "ADMIN"
      }, headers=admin_headers)
      assert res_prov.status_code == 200
      prov_key = res_prov.json()["admin_access_key"]

      # 4. Login as provisioned admin
      prov_admin_login = await ac.post("/auth/admin/token", json={
        "username": "new_admin_user",
        "password": "AdminPassword123!",
        "admin_access_key": prov_key
      })
      assert prov_admin_login.status_code == 200
      prov_admin_token = prov_admin_login.json()["access_token"]
      prov_admin_headers = {"Authorization": f"Bearer {prov_admin_token}"}

      # 5. Deactivate user via regular Admin
      res_deactivate = await ac.post(f"/auth/users/{signup_body['username']}/toggle-active", headers=prov_admin_headers)
      assert res_deactivate.status_code == 200

      # 6. Block login of deactivated user
      client_login_blocked = await ac.post("/auth/client/token", json={
        "username": signup_body["username"],
        "password": signup_body["password"]
      })
      assert client_login_blocked.status_code == 403
  finally:
    await engine.dispose()
