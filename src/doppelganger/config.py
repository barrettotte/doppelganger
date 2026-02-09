"""Application configuration via environment variables."""

from functools import lru_cache

from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseModel):
    """PostgreSQL connection settings."""

    host: str = "localhost"
    port: int = 5432
    user: str = "doppelganger"
    password: SecretStr = SecretStr("doppelganger")
    name: str = "doppelganger"
    pool_size: int = 5
    pool_max_overflow: int = 10

    @property
    def async_url(self) -> str:
        """Connection URL for asyncpg."""
        pw = self.password.get_secret_value()
        return f"postgresql+asyncpg://{self.user}:{pw}@{self.host}:{self.port}/{self.name}"

    @property
    def sync_url(self) -> str:
        """Connection URL for psycopg2 (Alembic)."""
        pw = self.password.get_secret_value()
        return f"postgresql+psycopg2://{self.user}:{pw}@{self.host}:{self.port}/{self.name}"


class TTSSettings(BaseModel):
    """TTS engine settings."""

    model_name: str = "chatterbox"
    device: str = "cuda"
    voices_dir: str = "voices"


class DiscordSettings(BaseModel):
    """Discord bot settings."""

    token: SecretStr = SecretStr("")
    guild_id: str = ""
    required_role_id: str = ""
    cooldown_seconds: int = 5


class Settings(BaseSettings):
    """Root application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="DOPPELGANGER_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    allowed_origins: list[str] = ["*"]

    database: DatabaseSettings = DatabaseSettings()
    tts: TTSSettings = TTSSettings()
    discord: DiscordSettings = DiscordSettings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
