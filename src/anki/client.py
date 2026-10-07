import base64
import logging
import requests
from typing import Any, Dict, List, Optional
from src.core.config import Config

logger = logging.getLogger("chatgpt_anki.anki.client")


class AnkiConnectClient:
    def __init__(self, config: Config):
        self.config = config
        self.url = config.anki_connect_url

    def _invoke(self, action: str, **params) -> Any:
        payload = {"action": action, "version": 6, "params": params}
        try:
            resp = requests.post(self.url, json=payload, timeout=10)
            if resp.status_code != 200:
                raise RuntimeError(f"AnkiConnect HTTP Error {resp.status_code}")

            response = resp.json()
            if len(response) != 2:
                raise RuntimeError("Response has an unexpected number of fields")
            if "error" not in response:
                raise RuntimeError("Response is missing required error field")
            if "result" not in response:
                raise RuntimeError("Response is missing required result field")
            if response["error"] is not None:
                raise RuntimeError(f"AnkiConnect error: {response['error']}")

            return response["result"]
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to communicate with AnkiConnect at {self.url}: {e}")
            raise RuntimeError(f"AnkiConnect unreachable at {self.url}") from e

    def is_connected(self) -> bool:
        try:
            version = self._invoke("version")
            return bool(version)
        except Exception:
            return False

    def get_deck_names(self) -> List[str]:
        return self._invoke("deckNames")

    def create_deck(self, deck_name: str) -> bool:
        try:
            self._invoke("createDeck", deck=deck_name)
            return True
        except Exception as e:
            logger.error(f"Failed to create deck '{deck_name}': {e}")
            return False

    def get_model_names(self) -> List[str]:
        return self._invoke("modelNames")

    def ensure_note_model(self, model_name: str) -> bool:
        models = self.get_model_names()
        if model_name in models:
            return True

        # Create model if not present
        in_order_fields = [
            "Word",
            "Meaning",
            "Example",
            "PartOfSpeech",
            "Pronunciation",
            "Audio",
            "Source",
            "Tags"
        ]

        card_templates = [
            {
                "Name": "Card 1",
                "Front": '<div class="card front"><h1 class="word">{{Word}}</h1><div class="audio">{{Audio}}</div></div>',
                "Back": (
                    '<div class="card back"><h1 class="word">{{Word}}</h1>'
                    '<div class="pos"><i>{{PartOfSpeech}}</i> {{Pronunciation}}</div><hr>'
                    '<div class="meaning">{{Meaning}}</div>'
                    '<div class="example"><b>Example:</b> {{Example}}</div>'
                    '<div class="audio">{{Audio}}</div>'
                    '<div class="source"><small>Source: {{Source}}</small></div></div>'
                )
            }
        ]

        try:
            self._invoke(
                "createModel",
                modelName=model_name,
                inOrderFields=in_order_fields,
                css=".card { font-family: arial; font-size: 18px; text-align: center; color: black; background-color: white; } .word { color: #1a73e8; }",
                cardTemplates=card_templates
            )
            return True
        except Exception as e:
            logger.error(f"Failed to create note model '{model_name}': {e}")
            return False

    def store_media_file(self, filename: str, file_path: str) -> bool:
        with open(file_path, "rb") as f:
            data_b64 = base64.b64encode(f.read()).decode("utf-8")
        try:
            self._invoke("storeMediaFile", filename=filename, data=data_b64)
            return True
        except Exception as e:
            logger.error(f"Failed to store media file '{filename}': {e}")
            return False

    def find_notes_by_word(self, word: str, deck_name: str, model_name: str) -> List[int]:
        query = f'"deck:{deck_name}" "note:{model_name}" "Word:{word}"'
        try:
            return self._invoke("findNotes", query=query)
        except Exception:
            # Fallback broader search
            try:
                return self._invoke("findNotes", query=f'"Word:{word}"')
            except Exception:
                return []

    def can_add_notes(self, notes: List[Dict[str, Any]]) -> List[bool]:
        return self._invoke("canAddNotes", notes=notes)

    def add_notes(self, notes: List[Dict[str, Any]]) -> List[Optional[int]]:
        return self._invoke("addNotes", notes=notes)
