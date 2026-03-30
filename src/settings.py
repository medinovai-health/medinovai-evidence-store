"""Application settings (no secrets; use platform vault in production)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class MosSettings(BaseSettings):
    """Runtime configuration with mos_ field names in env."""

    model_config = SettingsConfigDict(
        env_prefix="MOS_",
        env_file=".env",
        extra="ignore",
    )

    service_name: str = "medinovai-evidence-store"
    tenant_id: str = "dev-tenant"
    temporal_address: str = "127.0.0.1:7233"
    temporal_namespace: str = "default"
    task_queue: str = "evidence-store-tasks"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    fda_config_path: Path = Path("config/fda-compliance.yaml")
    require_tenant_header: bool = False
    database_url: str = (
        "postgresql+asyncpg://evidence:evidence@127.0.0.1:5433/evidence"
    )
    skip_db: bool = False


@lru_cache
def mos_get_settings() -> MosSettings:
    """Return cached settings instance."""
    return MosSettings()
