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
            signup_res = await ac.post("/auth/register-client", json=signup_payload)
            assert signup_res.status_code == 200
            assert signup_res.json()["success"] is True
            
            # 2. Login Client (valid credentials)
            login_payload = {
                "username": username,
                "password": "Password123!"
            }
            login_res = await ac.post("/auth/login-client", json=login_payload)
            assert login_res.status_code == 200
            
            auth_data = login_res.json()
            assert "access_token" in auth_data
            assert auth_data["role"] == Role.CLIENT
    finally:
        await engine.dispose()

@pytest.mark.asyncio
async def test_admin_access_key_login_flows():
    """
    Tests that admins login using only username/email and password (no key required for active accounts),
    and check access restrictions.
    """
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Login with correct Admin Credentials (no key needed)
            admin_payload = {
                "username": "admin",
                "password": "admin123"
            }
            res_ok = await ac.post("/auth/admin/login", json=admin_payload)
            assert res_ok.status_code == 200
            assert "access_token" in res_ok.json()
            assert res_ok.json()["role"] == Role.SUPER_ADMIN

            # 2. Login with incorrect password fails
            admin_payload_bad_pwd = {
                "username": "admin",
                "password": "wrong_password"
            }
            res_bad_pwd = await ac.post("/auth/admin/login", json=admin_payload_bad_pwd)
            assert res_bad_pwd.status_code == 400

            # 3. Client trying to login through the Admin endpoint fails
            client_payload = {
                "username": "client",
                "password": "client123"
            }
            res_client_blocked = await ac.post("/auth/admin/login", json=client_payload)
            assert res_client_blocked.status_code == 403
            assert "client accounts must authenticate" in res_client_blocked.json()["detail"].lower()
    finally:
        await engine.dispose()

@pytest.mark.asyncio
async def test_super_admin_provisioning_privilege_boundary():
    """
    Tests that SUPER_ADMIN and ADMIN can provision staff, and new staff must activate their accounts before login.
    """
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Authenticate as SUPER_ADMIN
            sa_login = await ac.post("/auth/admin/login", json={
                "username": "admin",
                "password": "admin123"
            })
            sa_token = sa_login.json()["access_token"]
            sa_headers = {"Authorization": f"Bearer {sa_token}"}

            # 2. Authenticate as regular ADMIN
            admin_login = await ac.post("/auth/admin/login", json={
                "username": "regular_admin",
                "password": "admin123"
            })
            admin_token = admin_login.json()["access_token"]
            admin_headers = {"Authorization": f"Bearer {admin_token}"}

            # 3. SUPER_ADMIN provisions a new Operations user (invitation flow, no password)
            new_ops_payload = {
                "username": f"ops_prov_{uuid.uuid4().hex[:4]}",
                "email": f"ops_prov_{uuid.uuid4().hex[:4]}@bbps.com",
                "role": "OPERATIONS"
            }
            res_prov = await ac.post("/auth/admin/create", json=new_ops_payload, headers=sa_headers)
            assert res_prov.status_code == 200
            assert res_prov.json()["success"] is True
            assert "admin_access_key" in res_prov.json()
            generated_key = res_prov.json()["admin_access_key"]

            # 4. Try logging in as the provisioned admin before activation (Should fail with 403)
            res_pre_activate = await ac.post("/auth/admin/login", json={
                "username": new_ops_payload["username"],
                "password": "OpsPassword123!"
            })
            assert res_pre_activate.status_code == 403

            # 5. Activate the Operations user using the access key and setting their password
            res_activate = await ac.post("/auth/admin/activate", json={
                "username": new_ops_payload["username"],
                "password": "OpsPassword123!",
                "admin_access_key": generated_key
            })
            assert res_activate.status_code == 200
            assert res_activate.json()["success"] is True

            # 6. Try logging in with the newly activated Operations account (no key required)
            ops_login = await ac.post("/auth/admin/login", json={
                "username": new_ops_payload["username"],
                "password": "OpsPassword123!"
            })
            assert ops_login.status_code == 200
            assert ops_login.json()["role"] == Role.OPERATIONS

            # 7. Regular ADMIN attempts to provision an admin (Should succeed as ADMIN role can provision staff)
            new_ops_2 = {
                "username": f"ops_prov_{uuid.uuid4().hex[:4]}",
                "email": f"ops_prov_{uuid.uuid4().hex[:4]}@bbps.com",
                "role": "OPERATIONS"
            }
            res_prov_ok = await ac.post("/auth/admin/create", json=new_ops_2, headers=admin_headers)
            assert res_prov_ok.status_code == 200

            # 8. SUPER_ADMIN lists keys
            res_keys = await ac.get("/auth/admin/keys", headers=sa_headers)
            assert res_keys.status_code == 200
            assert len(res_keys.json()) >= 1

            # 9. Regular ADMIN attempts to list keys (Should fail with 403)
            res_keys_failed = await ac.get("/auth/admin/keys", headers=admin_headers)
            assert res_keys_failed.status_code == 403
    finally:
        await engine.dispose()

@pytest.mark.asyncio
async def test_admin_standalone_key_generation_and_self_signup():
    """
    Tests that a SUPER_ADMIN can pre-generate a standalone ADMIN_ACCESS_KEY,
    and a new staff user can activate/register themselves using that key.
    """
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Login as SUPER_ADMIN
            sa_login = await ac.post("/auth/admin/login", json={
                "username": "admin",
                "password": "admin123"
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

            # 3. New staff registers/activates themselves with the key
            new_staff_username = f"self_staff_{uuid.uuid4().hex[:6]}"
            signup_payload = {
                "username": new_staff_username,
                "password": "StaffPassword123!",
                "admin_access_key": standalone_key
            }
            signup_res = await ac.post("/auth/admin/activate", json=signup_payload)
            assert signup_res.status_code == 200
            assert signup_res.json()["success"] is True

            # 4. Attempt login as the new staff (no key required)
            staff_login = await ac.post("/auth/admin/login", json={
                "username": new_staff_username,
                "password": signup_payload["password"]
            })
            assert staff_login.status_code == 200
            assert staff_login.json()["role"] == Role.AUDITOR

            # 5. Attempting to activate another user with the same key must fail (it is now consumed)
            dup_signup_payload = {
                "username": f"dup_staff_{uuid.uuid4().hex[:6]}",
                "password": "StaffPassword123!",
                "admin_access_key": standalone_key
            }
            dup_res = await ac.post("/auth/admin/activate", json=dup_signup_payload)
            assert dup_res.status_code == 401
    finally:
        await engine.dispose()
