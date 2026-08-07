from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "StudyMingle API"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = (
        "postgresql+asyncpg://studymingle:studymingle@localhost:5432/studymingle"
    )
    frontend_origins: str = (
        "http://localhost:5173,https://study.thoughtmingle.com"
    )
    session_cookie_name: str = "studymingle_session"
    session_ttl_hours: int = 168
    turnstile_secret_key: str | None = None
    storage_endpoint_url: str | None = None
    storage_public_endpoint_url: str | None = None
    storage_region: str = "auto"
    storage_access_key_id: str = "studymingle"
    storage_secret_access_key: str = "studymingle-local-secret"
    storage_bucket: str = "studymingle-worksheets"
    storage_auto_create_bucket: bool = True
    upload_max_bytes: int = 10 * 1024 * 1024
    ocr_max_pages: int = 20
    tutor_provider: str = "ollama"
    tutor_model: str = "qwen3:4b"
    tutor_base_url: str = "http://localhost:11434"
    tutor_timeout_seconds: float = 30.0
    tutor_rate_limit_requests: int = 12
    tutor_rate_limit_window_seconds: int = 60
    tutor_max_hints: int = 3

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.frontend_origins.split(",")
            if origin.strip()
        ]

    @property
    def secure_cookies(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
