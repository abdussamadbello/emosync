import logging

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_INSECURE_DEFAULT_SECRET = "change-me-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = "postgresql+asyncpg://emosync:emosync@localhost:5432/emosync"
    database_url_sync: str = "postgresql://emosync:emosync@localhost:5432/emosync"
    cors_origins: str = "http://localhost:3000"
    # When set, chat routes require Authorization: Bearer <api_key> or X-API-Key. Health stays public.
    api_key: str | None = None

    # Gemini API key for the LangGraph agent pipeline.
    # When unset, chat falls back to a deterministic stub (safe for CI / local dev).
    gemini_api_key: str | None = None

    # ElevenLabs STT model (Scribe).
    elevenlabs_stt_model_id: str = "scribe_v2"

    # ElevenLabs TTS configuration.
    # Keep optional for local dev: when unset, TTS falls back to deterministic stub audio.
    elevenlabs_api_key: str | None = None
    elevenlabs_voice_id: str = "EXAVITQu4vr4xnSDxMaL"
    elevenlabs_model_id: str = "eleven_turbo_v2_5"

    # Voice realtime defaults.
    voice_output_format: str = "mp3_22050_32"
    voice_chunk_bytes: int = 4096
    voice_input_buffer_max_bytes: int = 2_000_000
    voice_session_idle_timeout_seconds: int = 300

    # JWT auth
    jwt_secret: str = _INSECURE_DEFAULT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours

    @model_validator(mode="after")
    def _reject_insecure_jwt_secret(self) -> "Settings":
        is_local = "localhost" in self.database_url or "127.0.0.1" in self.database_url
        if self.jwt_secret == _INSECURE_DEFAULT_SECRET:
            if is_local:
                logger.warning(
                    "Using insecure default JWT secret — acceptable for local dev only. "
                    "Set JWT_SECRET env var before deploying."
                )
            else:
                raise ValueError(
                    "JWT_SECRET must be set to a secure random value in non-local environments. "
                    "The default 'change-me-in-production' is not safe."
                )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
