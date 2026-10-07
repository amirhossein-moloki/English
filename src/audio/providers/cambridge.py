import logging
import requests
from typing import Optional, Tuple
from src.audio.base import AudioProvider
from src.core.models import WordItem
from src.core.config import Config

logger = logging.getLogger("chatgpt_anki.audio.cambridge")


class CambridgeAudioProvider(AudioProvider):
    """Cambridge Audio Provider Adapter.
    Note: Requires official API key or endpoint configured.
    """

    def __init__(self, config: Config):
        self.config = config

    @property
    def name(self) -> str:
        return "cambridge"

    @property
    def is_available(self) -> bool:
        # Returns False if no official API key provided to strictly avoid web scraping
        return False

    def get_audio(self, item: WordItem, locale: str = "en-US") -> Optional[Tuple[bytes, str, str, str]]:
        return None
