from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class ConcurrencyConfig(BaseSettings):
    redis_url: str = Field(default="redis://localhost:6379", description="Redis connection URL")
    hmac_master_secret: str = Field(..., description="Master secret for HMAC key derivation")
    hmac_key_ttl_seconds: int = Field(default=60, description="TTL for ephemeral HMAC keys in seconds")
    xread_block_ms: int = Field(default=50, description="Block time for XREAD in milliseconds")
    lock_timeout_ms: int = Field(default=5000, description="Timeout for handshake in milliseconds")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

config = ConcurrencyConfig()
