import logging
import requests
from typing import Optional, Tuple
from src.audio.base import AudioProvider
from src.core.models import WordItem
from src.core.config import Config

logger = logging.getLogger("chatgpt_anki.audio.oxford")


class OxfordAudioProvider(AudioProvider):
    def __init__(self, config: Config):
        self.app_id = config.oxford_app_id
        self.app_key = config.oxford_app_key

    @property
    def name(self) -> str:
        return "oxford"

    @property
    def is_available(self) -> bool:
        return bool(self.app_id and self.app_key)

    def get_audio(self, item: WordItem, locale: str = "en-US") -> Optional[Tuple[bytes, str, str, str]]:
        if not self.is_available:
            return None

        word = item.normalized_word
        lang = "en-us" if locale.lower() in ("en-us", "us") else "en-gb"
        url = f"https://od-api.oxforddictionaries.com/api/v2/entries/{lang}/{word}"
        headers = {
            "app_id": self.app_id,
            "app_key": self.app_key
        }

        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                logger.debug(f"Oxford API returned status {resp.status_code} for word '{word}'")
                return None

            data = resp.json()
            results = data.get("results", [])
            for res in results:
                for entry in res.get("lexicalEntries", []):
                    for pron in entry.get("pronunciations", []):
                        audio_url = pron.get("audioFile")
                        if audio_url:
                            audio_resp = requests.get(audio_url, timeout=10)
                            if audio_resp.status_code == 200:
                                return (audio_resp.content, audio_url, "audio/mpeg", "OXFORD_OFFICIAL_API")
        except Exception as e:
            logger.warning(f"Error fetching Oxford audio for '{word}': {e}")

        return None
