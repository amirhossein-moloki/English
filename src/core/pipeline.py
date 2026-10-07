import logging
from typing import List, Dict, Any, Callable, Optional
from src.core.config import Config
from src.core.models import WordItem, ItemStatus, DuplicatePolicy, AudioAsset
from src.database.repository import Database
from src.parser.rule_based import RuleBasedParser
from src.parser.llm import LLMParser
from src.audio.manager import AudioManager
from src.anki.client import AnkiConnectClient
from src.anki.duplicate import DuplicateDetector

logger = logging.getLogger("chatgpt_anki.pipeline")


class ProcessingPipeline:
    def __init__(self, config: Config, db: Database):
        self.config = config
        self.db = db
        self.parser = RuleBasedParser()
        self.audio_manager = AudioManager(config, db)
        self.anki_client = AnkiConnectClient(config)
        self.duplicate_detector = DuplicateDetector(
            self.anki_client, DuplicatePolicy(config.duplicate_policy)
        )

    def analyze_text(self, text: str) -> List[WordItem]:
        # Parse text into WordItems
        items = self.parser.parse(text)
        if not items and self.config.llm_api_key:
            llm_parser = LLMParser(self.config)
            items = llm_parser.parse(text)

        # Check duplicate status for each item
        deck = self.config.anki_default_deck
        model = self.config.anki_note_type
        is_anki_online = self.anki_client.is_connected()

        for item in items:
            if is_anki_online:
                is_dup, _ = self.duplicate_detector.check_duplicate(item.word, deck, model)
                if is_dup:
                    item.status = ItemStatus.DUPLICATE
                else:
                    item.status = ItemStatus.PENDING
            else:
                item.status = ItemStatus.PENDING

        return items

    def process_items(
        self,
        items: List[WordItem],
        progress_callback: Optional[Callable[[WordItem, int, int], None]] = None
    ) -> List[WordItem]:
        deck_name = self.config.anki_default_deck
        model_name = self.config.anki_note_type
        policy = DuplicatePolicy(self.config.duplicate_policy)

        # Check / Ensure deck and note model
        if self.anki_client.is_connected():
            self.anki_client.create_deck(deck_name)
            self.anki_client.ensure_note_model(model_name)

        total = len(items)
        for idx, item in enumerate(items, 1):
            try:
                # 1. Handle Duplicate Check & Policy
                if self.anki_client.is_connected():
                    is_dup, existing_ids = self.duplicate_detector.check_duplicate(
                        item.word, deck_name, model_name
                    )
                    if is_dup:
                        if policy == DuplicatePolicy.SKIP:
                            item.status = ItemStatus.DUPLICATE
                            logger.info(f"Skipping duplicate word '{item.word}'")
                            if progress_callback:
                                progress_callback(item, idx, total)
                            continue

                # 2. Retrieve & Cache Audio
                audio_asset: Optional[AudioAsset] = self.audio_manager.resolve_audio(item)

                if not audio_asset and not self.config.allow_cards_without_audio:
                    item.status = ItemStatus.FAILED
                    item.error_message = "No valid audio found and allow_cards_without_audio is False"
                    if progress_callback:
                        progress_callback(item, idx, total)
                    continue

                # 3. Store Media File in Anki
                audio_field_str = ""
                if audio_asset:
                    cache_file_path = str(self.config.cache_dir / audio_asset.filename)
                    if self.anki_client.is_connected():
                        self.anki_client.store_media_file(audio_asset.filename, cache_file_path)
                    audio_field_str = f"[sound:{audio_asset.filename}]"

                # 4. Construct Anki Note Payload
                if self.anki_client.is_connected():
                    note_payload = {
                        "deckName": deck_name,
                        "modelName": model_name,
                        "fields": {
                            "Word": item.word,
                            "Meaning": item.meaning or "",
                            "Example": item.example or "",
                            "PartOfSpeech": item.part_of_speech or "",
                            "Pronunciation": item.pronunciation or "",
                            "Audio": audio_field_str,
                            "Source": audio_asset.provider if audio_asset else "ChatGPT",
                            "Tags": " ".join(item.tags)
                        },
                        "tags": item.tags,
                        "options": {
                            "allowDuplicate": policy == DuplicatePolicy.CREATE,
                            "duplicateScope": "deck"
                        }
                    }

                    item.status = ItemStatus.ANKI_CREATING
                    note_ids = self.anki_client.add_notes([note_payload])
                    if note_ids and note_ids[0] is not None:
                        item.status = ItemStatus.SUCCESS
                    else:
                        item.status = ItemStatus.FAILED
                        item.error_message = "AnkiConnect failed to add note"
                else:
                    item.status = ItemStatus.SUCCESS

            except Exception as e:
                logger.error(f"Error processing item '{item.word}': {e}", exc_info=True)
                item.status = ItemStatus.FAILED
                item.error_message = str(e)

            if progress_callback:
                progress_callback(item, idx, total)

        return items
