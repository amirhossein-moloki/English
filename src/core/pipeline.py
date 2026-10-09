import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Callable, Optional
from pydantic import BaseModel, Field

from src.core.config import Config
from src.core.models import WordItem, ItemStatus, DuplicatePolicy, AudioAsset
from src.database.repository import Database
from src.parser.rule_based import RuleBasedParser, BatchSourceParser
from src.parser.llm import LLMParser
from src.audio.manager import AudioManager
from src.anki.client import AnkiConnectClient
from src.anki.duplicate import DuplicateDetector

logger = logging.getLogger("chatgpt_anki.pipeline")


class PipelineStats(BaseModel):
    total_sources: int = 0
    completed_sources: int = 0
    total_entries: int = 0
    valid_entries: int = 0
    invalid_entries: int = 0
    selected_for_import: int = 0
    successfully_added: int = 0
    skipped_duplicates: int = 0
    updated_notes: int = 0
    audio_failures: int = 0
    import_failures: int = 0
    pending_tasks: int = 0


class ProcessingPipeline:
    def __init__(self, config: Config, db: Database, max_workers: int = 3):
        self.config = config
        self.db = db
        self.max_workers = max_workers
        self.parser = RuleBasedParser()
        self.batch_parser = BatchSourceParser(self.parser)
        self.audio_manager = AudioManager(config, db)
        self.anki_client = AnkiConnectClient(config)
        self.duplicate_detector = DuplicateDetector(
            self.anki_client, DuplicatePolicy(config.duplicate_policy)
        )
        self.cancel_requested = False
        self._lock = threading.Lock()

    def request_cancellation(self):
        with self._lock:
            self.cancel_requested = True

    def reset_cancellation(self):
        with self._lock:
            self.cancel_requested = False

    def is_cancelled(self) -> bool:
        with self._lock:
            return self.cancel_requested

    def analyze_text(self, text: str, source_name: str = "ChatGPT") -> List[WordItem]:
        items = self.parser.parse(text)
        if not items and self.config.llm_api_key:
            llm_parser = LLMParser(self.config)
            items = llm_parser.parse(text)

        for item in items:
            item.source = source_name

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

    def analyze_sources(self, sources: Dict[str, str]) -> List[WordItem]:
        all_items = []
        parsed_dict = self.batch_parser.parse_sources(sources)

        deck = self.config.anki_default_deck
        model = self.config.anki_note_type
        is_anki_online = self.anki_client.is_connected()

        for source_name, items in parsed_dict.items():
            for item in items:
                if is_anki_online:
                    is_dup, _ = self.duplicate_detector.check_duplicate(item.word, deck, model)
                    if is_dup:
                        item.status = ItemStatus.DUPLICATE
                    else:
                        item.status = ItemStatus.PENDING
                else:
                    item.status = ItemStatus.PENDING
                all_items.append(item)

        return all_items

    def process_single_item(self, item: WordItem, deck_name: str, model_name: str, policy: DuplicatePolicy) -> WordItem:
        if self.is_cancelled():
            item.status = ItemStatus.FAILED
            item.error_message = "Cancelled by user"
            return item

        try:
            # 1. Duplicate Handling
            is_dup = False
            existing_ids = []
            if self.anki_client.is_connected():
                is_dup, existing_ids = self.duplicate_detector.check_duplicate(item.word, deck_name, model_name)

            if is_dup:
                if policy == DuplicatePolicy.SKIP:
                    item.status = ItemStatus.DUPLICATE
                    logger.info(f"Skipping duplicate word '{item.word}'")
                    return item
                elif policy == DuplicatePolicy.UPDATE and existing_ids:
                    # Update existing card
                    audio_asset = self.audio_manager.resolve_audio(item)
                    audio_filename = audio_asset.filename if audio_asset else None
                    fields = self.anki_client.build_note_fields(item, audio_filename)
                    if audio_asset and self.anki_client.is_connected():
                        cache_file_path = str(self.config.cache_dir / audio_asset.filename)
                        self.anki_client.store_media_file(audio_asset.filename, cache_file_path)

                    success = True
                    for nid in existing_ids:
                        if not self.anki_client.update_note_fields(nid, fields):
                            success = False
                    if success:
                        item.status = ItemStatus.SUCCESS
                    else:
                        item.status = ItemStatus.FAILED
                        item.error_message = "Failed to update existing note fields in Anki"
                    return item

            # 2. Retrieve & Cache Audio
            audio_asset: Optional[AudioAsset] = self.audio_manager.resolve_audio(item)

            if not audio_asset and not self.config.allow_cards_without_audio:
                item.status = ItemStatus.FAILED
                item.error_message = f"No valid audio found for '{item.word}' and allow_cards_without_audio is False"
                return item

            # 3. Store Media File in Anki
            audio_filename = audio_asset.filename if audio_asset else None
            if audio_asset and self.anki_client.is_connected():
                cache_file_path = str(self.config.cache_dir / audio_asset.filename)
                self.anki_client.store_media_file(audio_asset.filename, cache_file_path)

            # 4. Construct Note Payload & Add
            if self.anki_client.is_connected():
                fields = self.anki_client.build_note_fields(item, audio_filename)
                note_payload = {
                    "deckName": deck_name,
                    "modelName": model_name,
                    "fields": fields,
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

        return item

    def process_items(
        self,
        items: List[WordItem],
        progress_callback: Optional[Callable[[WordItem, int, int, PipelineStats], None]] = None
    ) -> List[WordItem]:
        self.reset_cancellation()
        deck_name = self.config.anki_default_deck
        model_name = self.config.anki_note_type
        policy = DuplicatePolicy(self.config.duplicate_policy)

        if self.anki_client.is_connected():
            self.anki_client.create_deck(deck_name)
            self.anki_client.ensure_note_model(model_name)

        total = len(items)
        stats = PipelineStats(
            total_entries=total,
            valid_entries=total,
            selected_for_import=total,
            pending_tasks=total
        )

        completed_count = 0
        processed_items: List[WordItem] = [None] * total

        # Process with bounded ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_index = {
                executor.submit(self.process_single_item, item, deck_name, model_name, policy): idx
                for idx, item in enumerate(items)
            }

            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    res_item = future.result()
                except Exception as e:
                    res_item = items[idx]
                    res_item.status = ItemStatus.FAILED
                    res_item.error_message = str(e)

                processed_items[idx] = res_item
                completed_count += 1
                stats.pending_tasks = total - completed_count

                if res_item.status == ItemStatus.SUCCESS:
                    stats.successfully_added += 1
                elif res_item.status == ItemStatus.DUPLICATE:
                    stats.skipped_duplicates += 1
                elif res_item.status == ItemStatus.FAILED:
                    stats.import_failures += 1
                    if "audio" in (res_item.error_message or "").lower():
                        stats.audio_failures += 1

                if progress_callback:
                    progress_callback(res_item, completed_count, total, stats)

        return [item for item in processed_items if item is not None]
