from abc import ABC, abstractmethod
from typing import Optional, Tuple
from src.core.models import AudioAsset, WordItem


class AudioProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if provider credentials/dependencies are valid."""
        pass

    @abstractmethod
    def get_audio(self, item: WordItem, locale: str = "en-US") -> Optional[Tuple[bytes, str, str, str]]:
        """Fetch pronunciation audio for given WordItem.
        Returns Optional tuple: (audio_bytes, source_url_or_ref, mime_type, license_status)
        """
        pass
