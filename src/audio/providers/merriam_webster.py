import logging
import requests
from typing import Optional, Tuple
from src.audio.base import AudioProvider
from src.core.models import WordItem
from src.core.config import Config

logger = logging.getLogger("chatgpt_anki.audio.merriam_webster")


class MerriamWebsterAudioProvider(AudioProvider):
    def __init__(self, config: Config):
        self.api_key = config.merriam_webster_api_key

    @property
    def name(self) -> str:
        return "merriam_webster"

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    def get_audio(self, item: WordItem, locale: str = "en-US") -> Optional[Tuple[bytes, str, str, str]]:
        if not self.is_available:
            return None

        word = item.normalized_word
        url = f"https://www.dictionaryapi.com/api/v3/references/collegiate/json/{word}?key={self.api_key}"

        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                return None

            data = resp.json()
            if not isinstance(data, list) or not data:
                return None

            first_entry = data[0]
            if not isinstance(first_entry, dict):
                return None

            hwi = first_entry.get("hwi", {})
            prs = hwi.get("prs", [])
            for pr in prs:
                sound = pr.get("sound", {})
                audio_base = sound.get("audio")
                if audio_base:
                    # Determine subdirectory format based on MW rules
                    if audio_base.startswith("bix"):
                        subdir = "bix"
                    elif audio_base.startswith("gg"):
                        subdir = "gg"
                    elif audio_base[0].isdigit() or audio_base[0] in "punctuation":
                        subdir = "number"
                    else:
                        subdir = audio_base[0]

                    audio_url = f"https://media.merriam-webster.com/audio/prons/en/us/mp3/{subdir}/{audio_base}.mp3"
                    audio_resp = requests.get(audio_url, timeout=10)
                    if audio_resp.status_code == 200:
                        return (audio_resp.content, audio_url, "audio/mpeg", "MERRIAM_WEBSTER_OFFICIAL_API")
        except Exception as e:
            logger.warning(f"Error fetching Merriam-Webster audio for '{word}': {e}")

        return None
