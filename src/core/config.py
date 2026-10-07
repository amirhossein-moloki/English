import os
import re
import logging
from typing import Optional, List
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config(BaseModel):
    anki_connect_url: str = Field(
        default_factory=lambda: os.getenv("ANKI_CONNECT_URL", "http://localhost:8765")
    )
    anki_default_deck: str = Field(
        default_factory=lambda: os.getenv("ANKI_DEFAULT_DECK", "English Vocabulary")
    )
    anki_note_type: str = Field(
        default_factory=lambda: os.getenv("ANKI_NOTE_TYPE", "English Vocabulary")
    )

    default_language: str = Field(
        default_factory=lambda: os.getenv("DEFAULT_LANGUAGE", "en")
    )
    default_locale: str = Field(
        default_factory=lambda: os.getenv("DEFAULT_LOCALE", "en-US")
    )

    oxford_app_id: Optional[str] = Field(
        default_factory=lambda: os.getenv("OXFORD_APP_ID")
    )
    oxford_app_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("OXFORD_APP_KEY")
    )
    merriam_webster_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("MERRIAM_WEBSTER_API_KEY")
    )

    audio_provider_priority: List[str] = Field(
        default_factory=lambda: [
            p.strip()
            for p in os.getenv(
                "AUDIO_PROVIDER_PRIORITY", "oxford,merriam_webster,cambridge,tts"
            ).split(",")
            if p.strip()
        ]
    )
    enable_tts_fallback: bool = Field(
        default_factory=lambda: os.getenv("ENABLE_TTS_FALLBACK", "true").lower() == "true"
    )
    tts_provider: str = Field(
        default_factory=lambda: os.getenv("TTS_PROVIDER", "edge_tts")
    )
    allow_cards_without_audio: bool = Field(
        default_factory=lambda: os.getenv("ALLOW_CARDS_WITHOUT_AUDIO", "false").lower() == "true"
    )
    max_audio_size_bytes: int = Field(
        default_factory=lambda: int(os.getenv("MAX_AUDIO_SIZE_BYTES", "5242880"))
    )
    cache_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("CACHE_DIR", "./data/cache"))
    )
    db_path: Path = Field(
        default_factory=lambda: Path(os.getenv("DB_PATH", "./data/app.db"))
    )

    llm_provider: Optional[str] = Field(
        default_factory=lambda: os.getenv("LLM_PROVIDER", "openai")
    )
    llm_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("LLM_API_KEY")
    )
    llm_model: Optional[str] = Field(
        default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini")
    )

    duplicate_policy: str = Field(
        default_factory=lambda: os.getenv("DUPLICATE_POLICY", "SKIP").upper()
    )


class SecretSanitizingFormatter(logging.Formatter):
    """Logging formatter that redacts known sensitive API keys and secrets."""

    def __init__(self, fmt=None, datefmt=None, style='%', secrets: Optional[List[str]] = None):
        super().__init__(fmt=fmt, datefmt=datefmt, style=style)
        self.secrets = [s for s in (secrets or []) if s and len(s) > 3]

    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        for secret in self.secrets:
            formatted = formatted.replace(secret, "[REDACTED]")
        # Redact any URL query parameters with key/token/auth
        formatted = re.sub(r'([?&](key|token|auth|app_key|api_key)=)[^&\s]+', r'\1[REDACTED]', formatted, flags=re.IGNORECASE)
        return formatted


def setup_logging(config: Optional[Config] = None) -> logging.Logger:
    logger = logging.getLogger("chatgpt_anki")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    secrets = []
    if config:
        for s in [config.oxford_app_id, config.oxford_app_key, config.merriam_webster_api_key, config.llm_api_key]:
            if s:
                secrets.append(s)

    handler = logging.StreamHandler()
    formatter = SecretSanitizingFormatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        secrets=secrets
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def get_config() -> Config:
    config = Config()
    config.cache_dir.mkdir(parents=True, exist_ok=True)
    config.db_path.parent.mkdir(parents=True, exist_ok=True)
    return config
