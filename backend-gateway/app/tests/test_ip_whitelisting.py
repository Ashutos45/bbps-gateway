import pytest
import os
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings

@pytest.mark.asyncio
async def test_ip_whitelisting_behavior(monkeypatch):
    # Ensure settings.ENV or ENVIRONMENT env var is set to development/staging for strict checking first
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("RENDER", "")
    monkeypatch.setenv("VERCEL", "")
    # Force settings.ENV to be something non-prod
    original_env = settings.ENV
    settings.ENV = "development"

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Dev mode: Whitelisted IP (using x-forwarded-for: 127.0.0.1) should pass through
            # (it might return 404 or 401 since it's not a valid transaction route, but not 403 IP blocked)
            res = await ac.get("/BOBCOU/BBPS/mbanking/fetch", headers={"x-forwarded-for": "127.0.0.1"})
            assert res.status_code != 403

            # 2. Dev mode: Non-whitelisted IP should be blocked with 403 Forbidden
            res = await ac.get("/BOBCOU/BBPS/mbanking/fetch", headers={"x-forwarded-for": "49.37.112.20"})
            assert res.status_code == 403
            assert res.json()["error_code"] == "ERR_IP_FORBIDDEN"

            # 3. Dev mode: Auth route should bypass IP check even from non-whitelisted IP
            # (will return 405 Method Not Allowed or 400 Bad Request, but not 403 Forbidden)
            res = await ac.post("/auth/signup", headers={"x-forwarded-for": "49.37.112.20"})
            assert res.status_code != 403

            # 4. Dev mode: Docs/Swagger route should bypass IP check even from non-whitelisted IP
            res = await ac.get("/docs", headers={"x-forwarded-for": "49.37.112.20"})
            assert res.status_code != 403

            # 5. Dev mode: Demo/testing route should bypass IP check even from non-whitelisted IP
            res = await ac.get("/demo/hmac-probe", headers={"x-forwarded-for": "49.37.112.20"})
            assert res.status_code != 403

            # 6. Production mode (using ENVIRONMENT=production): Should not block non-whitelisted IP
            monkeypatch.setenv("ENVIRONMENT", "production")
            # Clear settings ENV to make sure it respects the env var or set it to production
            settings.ENV = "production"

            res = await ac.get("/BOBCOU/BBPS/mbanking/fetch", headers={"x-forwarded-for": "49.37.112.20"})
            # Should bypass 403 IP whitelisting check (though it will fail signature/HMAC verification with 401 or similar, not 403)
            assert res.status_code != 403

            # 7. Production mode (using RENDER=true environment variable): Should not block non-whitelisted IP
            monkeypatch.setenv("ENVIRONMENT", "")
            settings.ENV = "development"
            monkeypatch.setenv("RENDER", "true")

            res = await ac.get("/BOBCOU/BBPS/mbanking/fetch", headers={"x-forwarded-for": "49.37.112.20"})
            assert res.status_code != 403

    finally:
        settings.ENV = original_env
