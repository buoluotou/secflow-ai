"""Central configuration — all values come from environment (see .env.example)."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- General ---
    app_env: str = "development"
    app_name: str = "SecFlow AI"
    secret_key: str = "CHANGE_ME"
    api_port: int = 8000
    access_token_expire_minutes: int = 720

    # --- PostgreSQL ---
    postgres_db: str = "secflow"
    postgres_user: str = "secflow"
    postgres_password: str = "CHANGE_ME"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    # --- Redis / Celery ---
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None

    # --- Wazuh ---
    wazuh_url: str = ""
    wazuh_username: str = ""
    wazuh_password: str = ""
    wazuh_verify_ssl: bool = False
    wazuh_sync_initial_lookback: int = 3600

    # --- MISP ---
    misp_url: str = ""
    misp_api_key: str = ""
    misp_verify_ssl: bool = False
    misp_org: str = "SecFlow"

    # --- Nuclei ---
    nuclei_mode: str = "docker"  # docker | binary
    nuclei_image: str = "projectdiscovery/nuclei:latest"
    nuclei_bin: str = "nuclei"
    nuclei_concurrency: int = 10
    nuclei_template_dir: str = ""

    # --- LLM ---
    llm_provider: str = "mock"  # mock | openai | ollama
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout: int = 120
    llm_temperature: float = 0.2
    llm_max_tokens: int = 4096

    # --- Storage ---
    data_dir: str = "/data"
    log_dir: str = "/logs"
    report_dir: str = "/reports"

    # --- Scheduler ---
    wazuh_sync_interval_seconds: int = 300
    misp_enrich_interval_seconds: int = 600

    # --- Frontend (used for CORS / docs) ---
    frontend_origin: str = "http://localhost"

    # Override for local dev/tests, e.g. sqlite:///./dev.db
    database_url_override: str | None = None

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def result_backend(self) -> str:
        return self.celery_result_backend or self.redis_url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
