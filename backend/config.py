from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./data/yourwriter.db"
    jwt_secret_key: str = "dev-secret-change-in-production"
    cors_origins: list[str] = ["*"]
    anthropic_api_key: str = ""
    environment: str = "development"

    # Agent layer model IDs.
    # Centralized so the agent layer never hardcodes model strings.
    # Override per-environment via env vars (CHAT_MODEL, WRITING_MODEL, ...).
    chat_model: str = "claude-sonnet-4-6"
    writing_model: str = "claude-sonnet-4-6"
    evolution_detect_model: str = "claude-haiku-4-5-20251001"
    evolution_compute_model: str = "claude-sonnet-4-6"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()
