from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = "postgresql+asyncpg://emosync:emosync@localhost:5432/emosync"
    database_url_sync: str = "postgresql://emosync:emosync@localhost:5432/emosync"
    cors_origins: str = "http://localhost:3000"
    # When set, chat routes require Authorization: Bearer <api_key> or X-API-Key. Health stays public.
    api_key: str | None = None

    # Gemini API key for the LangGraph agent pipeline.
    # When unset, chat falls back to a deterministic stub (safe for CI / local dev).
    gemini_api_key: str | None = None

    # JWT auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
