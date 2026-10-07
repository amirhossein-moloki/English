import re
from typing import List, Tuple, Dict, Any
from src.core.models import WordItem, DuplicatePolicy
from src.anki.client import AnkiConnectClient


class DuplicateDetector:
    def __init__(self, client: AnkiConnectClient, default_policy: DuplicatePolicy = DuplicatePolicy.SKIP):
        self.client = client
        self.default_policy = default_policy

    @staticmethod
    def normalize_word(word: str) -> str:
        return re.sub(r'[^\w\s-]', '', word).strip().lower()

    def check_duplicate(self, word: str, deck_name: str, model_name: str) -> Tuple[bool, List[int]]:
        norm_target = self.normalize_word(word)
        note_ids = self.client.find_notes_by_word(norm_target, deck_name, model_name)
        if not note_ids and norm_target != word:
            note_ids = self.client.find_notes_by_word(word, deck_name, model_name)
        return (len(note_ids) > 0, note_ids)
