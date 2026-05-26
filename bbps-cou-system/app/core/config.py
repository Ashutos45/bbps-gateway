from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

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

    DATABASE_URL: str = "sqlite:///./bbps_cou.db"
    LOG_LEVEL: str = "INFO"

    # Credentials map
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
        Returns the client_id, client_secret and base_url for the given channel.
        Channels must be one of: mbanking, upi, fi, feature-phone
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
