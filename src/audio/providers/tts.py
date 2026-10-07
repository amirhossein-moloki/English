import os
import io
import asyncio
import logging
from typing import Optional, Tuple
from src.audio.base import AudioProvider
from src.core.models import WordItem
from src.core.config import Config

logger = logging.getLogger("chatgpt_anki.audio.tts")


class TTSFallbackProvider(AudioProvider):
    def __init__(self, config: Config):
        self.config = config
        self.tts_type = config.tts_provider.lower()

    @property
    def name(self) -> str:
        return "tts"

    @property
    def is_available(self) -> bool:
        return self.config.enable_tts_fallback

    def get_audio(self, item: WordItem, locale: str = "en-US") -> Optional[Tuple[bytes, str, str, str]]:
        if not self.is_available:
            return None

        word = item.word

        # Try Edge TTS first if selected
        if self.tts_type == "edge_tts":
            audio_data = self._generate_edge_tts(word, locale)
            if audio_data:
                return (audio_data, "edge_tts://generated", "audio/mpeg", "PUBLIC_DOMAIN_TTS")

        # Fallback to gTTS
        audio_data = self._generate_gtts(word, locale)
        if audio_data:
            return (audio_data, "gtts://generated", "audio/mpeg", "PUBLIC_DOMAIN_TTS")

        return None

    def _generate_edge_tts(self, word: str, locale: str) -> Optional[bytes]:
        try:
            import edge_tts

            voice = "en-US-AriaNeural" if locale.lower() in ("en-us", "us") else "en-GB-SoniaNeural"

            async def _run():
                communicate = edge_tts.Communicate(word, voice)
                out = io.BytesIO()
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        out.write(chunk["data"])
                return out.getvalue()

            return asyncio.run(_run())
        except Exception as e:
            logger.warning(f"Edge TTS generation failed for '{word}': {e}")
            return None

    def _generate_gtts(self, word: str, locale: str) -> Optional[bytes]:
        try:
            from gtts import gTTS

            lang = locale.split("-")[0].lower() if "-" in locale else "en"
            tld = "com" if "us" in locale.lower() else "co.uk"

            tts = gTTS(text=word, lang=lang, tld=tld)
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            return fp.getvalue()
        except Exception as e:
            logger.warning(f"gTTS generation failed for '{word}': {e}")
            return None
