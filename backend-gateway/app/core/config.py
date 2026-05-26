from typing import Dict
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    ENV: str = "staging"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/bbps_gateway_db"
    LOG_LEVEL: str = "INFO"

    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:4173,http://127.0.0.1:5173,http://127.0.0.1:4173"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def async_database_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    # IP Whitelisting
    WHITELISTED_IPS: str = "127.0.0.1,206.1.1.1,206.1.1.2,206.1.1.3,localhost,::1,testclient"

    @property
    def whitelisted_ips_list(self) -> list[str]:
        return [ip.strip() for ip in self.WHITELISTED_IPS.split(",") if ip.strip()]

    # Gateway Service Registry
    SERVICE_REGISTRY: dict = {
        "/BOBCOU/BBPS": "bbps_service",
        "/AUTH": "auth_service",
        "/METRICS": "telemetry_service"
    }

    # JWT & API Key Security
    JWT_SECRET: str = "supersecretjwtsecretkeyforbbpsnextgenecosystemauth123!"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 60
    API_KEYS_JSON: str = '{"admin_key_123": "ADMIN", "operator_key_123": "OPERATOR", "client_key_123": "CLIENT", "auditor_key_123": "AUDITOR"}'


    # Resilience & Chaos Simulation settings
    ENABLE_CHAOS_MODE: bool = False
    SIMULATED_FAILURE_RATE: float = 0.30
    SIMULATED_LATENCY_MS: int = 500
    ENABLE_PARTIAL_DEGRADATION: bool = True

    # BBPS Channel Credentials (from Bank of Baroda API Specs)
    # mbanking
    MBANKING_CLIENT_ID: str = "bH1aI2Qgp7zJJFsmF01pPJtzawUBrafGkIz9rWrYA06wNtNj"
    MBANKING_CLIENT_SECRET: str = "ugVz1hETNXUIwnWtpLafAASFPL0qGI5fAWybWMfuEsIL3HusiIRWO1AvVmBRe0Gy"
    MBANKING_BASE_URL: str = "https://api-preprod.isampurna.com/mbanking"

    # upi
    UPI_CLIENT_ID: str = "qpcklLfKX6JA7taczJfoJXvSglPy4jR5lmWx3YdQsIaV1PVK"
    UPI_CLIENT_SECRET: str = "g8qZYnBjjd3FV0r8ZRpSCi96WO8DGEXFL3uScivt99XlRyGSSKxkBep5z9a11nfm"
    UPI_BASE_URL: str = "https://api-preprod.isampurna.com/upi"

    # fi
    FI_CLIENT_ID: str = "UG94ygc40cgWNF36y5BOWsKNaux9Kt1lyAikFdXV6LXC6mtp"
    FI_CLIENT_SECRET: str = "rfAjcxaY4ZNjxpP2A63os4tXllgOQ9mMoesrSs099wnEzWDAxGfBcC4qGJCIfqxA"
    FI_BASE_URL: str = "https://api-preprod.isampurna.com/fi"

    # feature-phone
    FEATURE_PHONE_CLIENT_ID: str = "OXYxrVdP8UNnwPGnEFRDwwSDCwYYThO51ItcknPT6aCKr8TT"
    FEATURE_PHONE_CLIENT_SECRET: str = "GSOjY6fAaCYX8UVkdHGQTz1dHF6tdRADpPTuo94lJvRENgalwdVpjquAdw6aTedk"
    FEATURE_PHONE_BASE_URL: str = "https://api-preprod.isampurna.com/feature-phone"

    def get_channel_config(self, channel: str) -> Dict[str, str]:
        """
        Returns client_id, client_secret, and base_url for the given channel.
        """
        normalized = channel.lower().replace("-", "_")
        if normalized == "mbanking":
            return {
                "client_id": self.MBANKING_CLIENT_ID,
                "client_secret": self.MBANKING_CLIENT_SECRET,
                "base_url": self.MBANKING_BASE_URL
            }
        elif normalized == "upi":
            return {
                "client_id": self.UPI_CLIENT_ID,
                "client_secret": self.UPI_CLIENT_SECRET,
                "base_url": self.UPI_BASE_URL
            }
        elif normalized == "fi":
            return {
                "client_id": self.FI_CLIENT_ID,
                "client_secret": self.FI_CLIENT_SECRET,
                "base_url": self.FI_BASE_URL
            }
        elif normalized in ("feature_phone", "featurephone"):
            return {
                "client_id": self.FEATURE_PHONE_CLIENT_ID,
                "client_secret": self.FEATURE_PHONE_CLIENT_SECRET,
                "base_url": self.FEATURE_PHONE_BASE_URL
            }
        else:
            raise ValueError(f"Invalid channel/sourceid: '{channel}'. Must be one of mbanking, upi, fi, feature-phone")

settings = Settings()
