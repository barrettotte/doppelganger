"""Application configuration via environment variables."""

from functools import lru_cache

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseModel):
    """PostgreSQL connection settings."""

    host: str = Field(default="localhost", description="Database server hostname")
    port: int = Field(default=5432, description="Database server port")
    user: str = Field(default="doppelganger", description="Database username")
    password: SecretStr = Field(default=SecretStr("doppelganger"), description="Database password")
    name: str = Field(default="doppelganger", description="Database name")
    pool_size: int = Field(default=5, description="Number of persistent connections in the pool")
    pool_max_overflow: int = Field(default=10, description="Max temporary connections above pool_size")

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
    device: str = Field(default="cuda", description="Torch device for inference (cuda, cpu)")
    voices_dir: str = Field(default="voices", description="Directory containing character voice subdirectories")
    exaggeration: float = Field(default=0.1, description="Controls vocal expressiveness (0.0=flat, 1.0=dramatic)")
    cfg_weight: float = Field(default=3.0, description="Classifier-free guidance strength for voice cloning fidelity")
    temperature: float = Field(default=0.5, description="Sampling temperature; higher produces more variation")
    chunk_size: int = Field(default=50, description="Number of tokens per streaming chunk")
    cache_max_size: int = Field(default=100, description="Max entries in the in-memory audio LRU cache")


class DiscordSettings(BaseModel):
    """Discord bot settings."""

    token: SecretStr = Field(default=SecretStr(""), description="Discord bot token from the developer portal")
    guild_id: str = Field(default="", description="Discord server ID for guild-scoped slash commands")
    required_role_id: str = Field(default="", description="Role ID required to use the bot; empty allows everyone")
    cooldown_seconds: int = Field(default=5, description="Per-guild cooldown between TTS plays in seconds")
    command_prefix: str = Field(default="!", description="Prefix for text-based commands (slash commands are always /)")
    entrance_sound: str = Field(default="", description="Path to a WAV file played when the bot joins a voice channel")
    max_text_length: int = Field(default=500, description="Max characters per /say request (hallucination starts ~500)")
    max_queue_depth: int = Field(default=20, description="Max pending requests in the TTS queue before rejecting")
    requests_per_minute: int = Field(default=3, description="Per-user rate limit for /say requests per rolling minute")


class Settings(BaseSettings):
    """Root application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="DOPPELGANGER_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    debug: bool = Field(default=False, description="Enable debug mode with verbose logging")
    host: str = Field(default="0.0.0.0", description="Host address to bind the API server to")
    port: int = Field(default=8000, description="Port to bind the API server to")
    allowed_origins: list[str] = Field(default=["*"], description="CORS allowed origins for the API")

    database: DatabaseSettings = Field(default_factory=DatabaseSettings, description="PostgreSQL connection settings")
    tts: TTSSettings = Field(default_factory=TTSSettings, description="TTS engine and voice settings")
    discord: DiscordSettings = Field(default_factory=DiscordSettings, description="Discord bot settings")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
