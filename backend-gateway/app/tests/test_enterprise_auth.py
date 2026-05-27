import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.auth.role_manager import Role
from app.database.db import engine
import uuid

@pytest.mark.asyncio
async def test_client_self_registration_and_login():
    """
    Tests public CLIENT self-registration and subsequent token retrieval.
    """
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            username = f"test_client_{uuid.uuid4().hex[:6]}"
            signup_payload = {
                "username": username,
                "email": f"{username}@test.com",
                "password": "Password123!",
                "organization": "BobCorp",
                "company": "BobCorp LLC"
            }
            
            # 1. Register Client (public)
            signup_res = await ac.post("/auth/client/signup", json=signup_payload)
            assert signup_res.status_code == 200
            assert signup_res.json()["success"] is True
            
            # 2. Login Client (valid credentials)
            login_payload = {
                "username": username,
                "password": "Password123!"
            }
            login_res = await ac.post("/auth/client/token", json=login_payload)
            assert login_res.status_code == 200
            
            auth_data = login_res.json()
            assert "access_token" in auth_data
            assert auth_data["role"] == Role.CLIENT
    finally:
        await engine.dispose()

@pytest.mark.asyncio
async def test_admin_access_key_login_flows():
    """
    Tests the dual-factor admin login requiring username, password, and ADMIN_ACCESS_KEY.
    """
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Login with correct Admin Access Key (using seeded values)
            admin_payload = {
                "username": "admin",
                "password": "admin123",
                "admin_access_key": "SUPER_KEY_123"
            }
            res_ok = await ac.post("/auth/admin/token", json=admin_payload)
            assert res_ok.status_code == 200
            assert "access_token" in res_ok.json()
            assert res_ok.json()["role"] == Role.SUPER_ADMIN

            # 2. Login with incorrect Admin Access Key
            admin_payload_bad_key = {
                "username": "admin",
                "password": "admin123",
                "admin_access_key": "WRONG_KEY"
            }
            res_bad_key = await ac.post("/auth/admin/token", json=admin_payload_bad_key)
            assert res_bad_key.status_code == 401
            assert "invalid or expired" in res_bad_key.json()["detail"].lower()

            # 3. Client trying to login through the Admin endpoint
            client_payload = {
                "username": "client",
                "password": "client123",
                "admin_access_key": "ANY_KEY"
            }
            res_client_blocked = await ac.post("/auth/admin/token", json=client_payload)
            assert res_client_blocked.status_code == 403
            assert "client accounts must authenticate" in res_client_blocked.json()["detail"].lower()
    finally:
        await engine.dispose()

@pytest.mark.asyncio
async def test_super_admin_provisioning_privilege_boundary():
    """
    Tests that only SUPER_ADMIN can provision admins, list admin keys, or view audit logs,
    and regular ADMINs or CLIENTs are blocked.
    """
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Authenticate as SUPER_ADMIN
            sa_login = await ac.post("/auth/admin/token", json={
                "username": "admin",
                "password": "admin123",
                "admin_access_key": "SUPER_KEY_123"
            })
            sa_token = sa_login.json()["access_token"]
            sa_headers = {"Authorization": f"Bearer {sa_token}"}

            # 2. Authenticate as regular ADMIN
            admin_login = await ac.post("/auth/admin/token", json={
                "username": "regular_admin",
                "password": "admin123",
                "admin_access_key": "ADMIN_KEY_123"
            })
            admin_token = admin_login.json()["access_token"]
            admin_headers = {"Authorization": f"Bearer {admin_token}"}

            # 3. SUPER_ADMIN provisions a new Operations user
            new_ops_payload = {
                "username": f"ops_prov_{uuid.uuid4().hex[:4]}",
                "email": f"ops_prov_{uuid.uuid4().hex[:4]}@bbps.com",
                "password": "OpsPassword123!",
                "role": "OPERATIONS"
            }
            res_prov = await ac.post("/auth/admin/users", json=new_ops_payload, headers=sa_headers)
            assert res_prov.status_code == 200
            assert res_prov.json()["success"] is True
            assert "admin_access_key" in res_prov.json()
            generated_key = res_prov.json()["admin_access_key"]

            # 4. Try logging in with the newly provisioned Operations account & generated key
            ops_login = await ac.post("/auth/admin/token", json={
                "username": new_ops_payload["username"],
                "password": new_ops_payload["password"],
                "admin_access_key": generated_key
            })
            assert ops_login.status_code == 200
            assert ops_login.json()["role"] == Role.OPERATIONS

            # 5. Regular ADMIN attempts to provision an admin (Should fail with 403)
            res_prov_failed = await ac.post("/auth/admin/users", json=new_ops_payload, headers=admin_headers)
            assert res_prov_failed.status_code == 403

            # 6. SUPER_ADMIN lists keys
            res_keys = await ac.get("/auth/admin/keys", headers=sa_headers)
            assert res_keys.status_code == 200
            assert len(res_keys.json()) >= 1

            # 7. Regular ADMIN attempts to list keys (Should fail with 403)
            res_keys_failed = await ac.get("/auth/admin/keys", headers=admin_headers)
            assert res_keys_failed.status_code == 403
    finally:
        await engine.dispose()

@pytest.mark.asyncio
async def test_admin_standalone_key_generation_and_self_signup():
    """
    Tests that a SUPER_ADMIN can pre-generate a standalone ADMIN_ACCESS_KEY,
    and a new staff user can register themselves using that key.
    """
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Login as SUPER_ADMIN
            sa_login = await ac.post("/auth/admin/token", json={
                "username": "admin",
                "password": "admin123",
                "admin_access_key": "SUPER_KEY_123"
            })
            sa_token = sa_login.json()["access_token"]
            sa_headers = {"Authorization": f"Bearer {sa_token}"}

            # 2. Super Admin generates standalone key for AUDITOR role
            gen_key_res = await ac.post(
                "/auth/admin/generate-key", 
                json={"role": "AUDITOR"}, 
                headers=sa_headers
            )
            assert gen_key_res.status_code == 200
            standalone_key = gen_key_res.json()["admin_access_key"]
            assert standalone_key.startswith("ADM_")

            # 3. New staff registers themselves with the key
            new_staff_username = f"self_staff_{uuid.uuid4().hex[:6]}"
            signup_payload = {
                "username": new_staff_username,
                "email": f"{new_staff_username}@bbps.com",
                "password": "StaffPassword123!",
                "admin_access_key": standalone_key
            }
            signup_res = await ac.post("/auth/admin/signup", json=signup_payload)
            assert signup_res.status_code == 200
            assert signup_res.json()["success"] is True

            # 4. Attempt login as the new staff with the key
            staff_login = await ac.post("/auth/admin/token", json={
                "username": new_staff_username,
                "password": signup_payload["password"],
                "admin_access_key": standalone_key
            })
            assert staff_login.status_code == 200
            assert staff_login.json()["role"] == Role.AUDITOR

            # 5. Attempting to register another user with the same key must fail (it is now assigned/used)
            dup_signup_payload = {
                "username": f"dup_staff_{uuid.uuid4().hex[:6]}",
                "email": f"dup_staff_{uuid.uuid4().hex[:6]}@bbps.com",
                "password": "StaffPassword123!",
                "admin_access_key": standalone_key
            }
            dup_res = await ac.post("/auth/admin/signup", json=dup_signup_payload)
            assert dup_res.status_code == 401
    finally:
        await engine.dispose()
