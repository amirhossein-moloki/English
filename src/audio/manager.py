import logging
from pathlib import Path
from typing import Optional, List
from src.core.config import Config
from src.core.models import WordItem, AudioAsset, ItemStatus
from src.database.repository import Database
from src.audio.validator import AudioValidator
from src.audio.base import AudioProvider
from src.audio.providers.oxford import OxfordAudioProvider
from src.audio.providers.merriam_webster import MerriamWebsterAudioProvider
from src.audio.providers.cambridge import CambridgeAudioProvider
from src.audio.providers.tts import TTSFallbackProvider

logger = logging.getLogger("chatgpt_anki.audio.manager")


class AudioManager:
    def __init__(self, config: Config, db: Database):
        self.config = config
        self.db = db
        self.providers: List[AudioProvider] = [
            OxfordAudioProvider(config),
            MerriamWebsterAudioProvider(config),
            CambridgeAudioProvider(config),
            TTSFallbackProvider(config),
        ]

    def resolve_audio(self, item: WordItem) -> Optional[AudioAsset]:
        locale = item.locale or self.config.default_locale
        norm_word = item.normalized_word or item.word.strip().lower()

        # 1. Check SQLite Persistent Audio Cache
        cached_asset = self.db.get_cached_audio(norm_word, locale)
        if cached_asset:
            cache_file = self.config.cache_dir / cached_asset.filename
            if cache_file.exists():
                logger.info(f"Cache hit for '{norm_word}' ({cached_asset.filename})")
                item.status = ItemStatus.AUDIO_VALIDATING
                return cached_asset

        # 2. Iterate through configured Provider Priority
        item.status = ItemStatus.AUDIO_SEARCH
        for provider_name in self.config.audio_provider_priority:
            if provider_name == "tts" and not self.config.enable_tts_fallback:
                logger.info("TTS fallback disabled in configuration; skipping TTS provider.")
                continue

            provider = next((p for p in self.providers if p.name == provider_name), None)
            if not provider or not provider.is_available:
                continue

            logger.info(f"Trying audio provider '{provider.name}' for word '{item.word}'")
            item.status = ItemStatus.AUDIO_DOWNLOADING
            try:
                res = provider.get_audio(item, locale=locale)
            except Exception as e:
                logger.warning(f"Audio provider '{provider.name}' threw exception for '{item.word}': {e}")
                continue

            if not res:
                continue

            audio_bytes, source_url, content_type, license_status = res

            # 3. Validate retrieved Audio File
            item.status = ItemStatus.AUDIO_VALIDATING
            is_valid, reason, mime_type, sha256 = AudioValidator.validate_bytes(
                content=audio_bytes,
                filename_or_url=source_url,
                content_type=content_type,
                max_size_bytes=self.config.max_audio_size_bytes
            )

            if not is_valid:
                logger.warning(f"Audio validation failed from provider '{provider.name}' for '{item.word}': {reason}")
                continue

            # 4. Save to Disk Cache & Database
            safe_filename = f"{norm_word}_{locale.lower().replace('-', '_')}_{provider.name}.mp3"
            target_path = self.config.cache_dir / safe_filename
            with open(target_path, "wb") as f:
                f.write(audio_bytes)

            asset = AudioAsset(
                word_id=item.id,
                word=item.word,
                normalized_word=norm_word,
                provider=provider.name,
                locale=locale,
                source_url=source_url,
                filename=safe_filename,
                mime_type=mime_type,
                sha256=sha256,
                file_size=len(audio_bytes),
                license=license_status,
                status="VALID"
            )

            saved_asset = self.db.save_audio_asset(asset)
            if provider.name == "tts":
                item.status = ItemStatus.TTS_FALLBACK
            else:
                item.status = ItemStatus.SUCCESS

            return saved_asset

        # 5. Handle Failure
        item.status = ItemStatus.AUDIO_UNAVAILABLE
        logger.warning(f"No audio available for '{item.word}' across all providers.")
        return None
