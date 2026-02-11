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


class ChatterboxSettings(BaseModel):
    """Chatterbox TTS engine settings for zero-shot voice cloning."""

    device: str = Field(default="cuda", description="Torch device for inference (cuda, cpu)")
    exaggeration: float = Field(default=0.1, description="Controls vocal expressiveness (0.0=flat, 1.0=dramatic)")
    cfg_weight: float = Field(default=3.0, description="Classifier-free guidance strength for voice cloning fidelity")
    temperature: float = Field(default=0.5, description="Sampling temperature; higher produces more variation")
    chunk_size: int = Field(default=50, description="Number of tokens per streaming chunk")


class OrpheusSettings(BaseModel):
    """Orpheus TTS engine settings for vLLM-served LoRA adapters."""

    enabled: bool = Field(default=False, description="Enable the Orpheus engine (requires running vLLM)")
    vllm_base_url: str = Field(
        default="http://localhost:8001/v1", description="Base URL for vLLM OpenAI-compatible API"
    )
    base_model: str = Field(
        default="canopylabs/orpheus-tts-0.1-pretrained", description="HuggingFace model ID for the Orpheus base"
    )
    snac_device: str = Field(default="cpu", description="Device for SNAC audio decoder (cpu is usually fine)")
    max_tokens: int = Field(default=2000, description="Max tokens per vLLM completion request")
    max_context: int = Field(default=2048, description="Model context window size in tokens")
    temperature: float = Field(default=0.6, description="Sampling temperature for generation")
    top_p: float = Field(default=0.95, description="Top-p nucleus sampling threshold")
    repetition_penalty: float = Field(default=1.1, description="Repetition penalty to reduce looping")
    frequency_penalty: float = Field(default=0.0, description="Penalizes tokens proportional to their frequency")
    sample_rate: int = Field(default=24000, description="Output audio sample rate in Hz")


class DiscordSettings(BaseModel):
    """Discord bot settings."""

    token: SecretStr = Field(default=SecretStr(""), description="Discord bot token from the developer portal")
    guild_id: str = Field(default="", description="Discord server ID for guild-scoped slash commands")
    required_role_id: str = Field(default="", description="Role ID required to use the bot; empty allows everyone")
    cooldown_seconds: int = Field(default=5, description="Per-guild cooldown between TTS plays in seconds")
    command_prefix: str = Field(default="!", description="Prefix for text-based commands (slash commands are always /)")
    entrance_sound: str = Field(default="", description="Path to a WAV file played when the bot joins a voice channel")
    max_text_length: int = Field(default=255, description="Max characters per /say request")
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
    voices_dir: str = Field(default="voices", description="Directory containing character voice subdirectories")
    cache_max_size: int = Field(default=100, description="Max entries in the in-memory audio LRU cache")

    database: DatabaseSettings = Field(default_factory=DatabaseSettings, description="PostgreSQL connection settings")
    chatterbox: ChatterboxSettings = Field(
        default_factory=ChatterboxSettings, description="Chatterbox TTS engine settings"
    )
    orpheus: OrpheusSettings = Field(default_factory=OrpheusSettings, description="Orpheus TTS engine settings")
    discord: DiscordSettings = Field(default_factory=DiscordSettings, description="Discord bot settings")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
