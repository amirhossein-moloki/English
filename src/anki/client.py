import base64
import logging
import requests
from typing import Any, Dict, List, Optional
from src.core.config import Config
from src.core.models import WordItem

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

    def get_model_field_names(self, model_name: str) -> List[str]:
        try:
            res = self._invoke("modelFieldNames", modelName=model_name)
            return res if isinstance(res, list) else []
        except Exception as e:
            logger.error(f"Failed to get field names for model '{model_name}': {e}")
            return []

    def ensure_note_model(
        self,
        model_name: str,
        enable_active_recall: bool = True
    ) -> bool:
        models = self.get_model_names()
        if model_name in models:
            # Model exists. Check if missing essential fields or templates safely
            existing_fields = self.get_model_field_names(model_name) or []
            needed_fields = [
                "Word", "IPA", "PartOfSpeech", "Meaning_EN", "Meaning_FA",
                "Example_EN", "Example_FA", "Collocations", "Synonyms",
                "Antonyms", "Notes", "Audio", "Source", "Tags",
                "Meaning", "Example", "Pronunciation"  # legacy fields
            ]
            for field in needed_fields:
                if field not in existing_fields:
                    try:
                        self._invoke("modelFieldAdd", modelName=model_name, fieldName=field)
                    except Exception as e:
                        logger.warning(f"Could not add field '{field}' to model '{model_name}': {e}")
            return True

        # Fields for canonical schema + legacy compatibility
        in_order_fields = [
            "Word",
            "IPA",
            "PartOfSpeech",
            "Meaning_EN",
            "Meaning_FA",
            "Example_EN",
            "Example_FA",
            "Collocations",
            "Synonyms",
            "Antonyms",
            "Notes",
            "Audio",
            "Source",
            "Tags",
            "Meaning",
            "Example",
            "Pronunciation"
        ]

        # Card Type A — English Recognition
        card_a_front = (
            '<div class="card front">'
            '<h1 class="word">{{Word}}</h1>'
            '{{#Audio}}<div class="audio">{{Audio}}</div>{{/Audio}}'
            '</div>'
        )
        card_a_back = (
            '<div class="card back">'
            '<h1 class="word">{{Word}}</h1>'
            '<div class="pos"><i>{{PartOfSpeech}}</i> {{#IPA}}[{{IPA}}]{{/IPA}}{{^IPA}}{{Pronunciation}}{{/IPA}}</div>'
            '<hr>'
            '{{#Meaning_EN}}<div class="meaning-en"><b>EN:</b> {{Meaning_EN}}</div>{{/Meaning_EN}}'
            '{{^Meaning_EN}}{{#Meaning}}<div class="meaning-en"><b>EN:</b> {{Meaning}}</div>{{/Meaning}}{{/Meaning_EN}}'
            '{{#Meaning_FA}}<div class="meaning-fa" dir="rtl"><b>FA:</b> {{Meaning_FA}}</div>{{/Meaning_FA}}'
            '<hr>'
            '{{#Example_EN}}<div class="example-en"><b>Example:</b> {{Example_EN}}</div>{{/Example_EN}}'
            '{{^Example_EN}}{{#Example}}<div class="example-en"><b>Example:</b> {{Example}}</div>{{/Example}}{{/Example_EN}}'
            '{{#Example_FA}}<div class="example-fa" dir="rtl"><b>ترجمه:</b> {{Example_FA}}</div>{{/Example_FA}}'
            '{{#Collocations}}<div class="collocations"><b>Collocations:</b> {{Collocations}}</div>{{/Collocations}}'
            '{{#Synonyms}}<div class="synonyms"><b>Synonyms:</b> {{Synonyms}}</div>{{/Synonyms}}'
            '{{#Antonyms}}<div class="antonyms"><b>Antonyms:</b> {{Antonyms}}</div>{{/Antonyms}}'
            '{{#Notes}}<div class="notes"><b>Notes:</b> {{Notes}}</div>{{/Notes}}'
            '{{#Audio}}<div class="audio">{{Audio}}</div>{{/Audio}}'
            '<div class="source"><small>Source: {{Source}}</small></div>'
            '</div>'
        )

        card_templates = [
            {
                "Name": "English Recognition",
                "Front": card_a_front,
                "Back": card_a_back
            }
        ]

        if enable_active_recall:
            # Card Type B — Active Recall
            card_b_front = (
                '<div class="card front active-recall">'
                '<div class="prompt"><b>Recall English Word:</b></div>'
                '{{#Meaning_FA}}<div class="meaning-fa" dir="rtl"><h2 dir="rtl">{{Meaning_FA}}</h2></div>{{/Meaning_FA}}'
                '{{^Meaning_FA}}<div class="meaning-en"><h2>{{Meaning_EN}}</h2></div>{{/Meaning_FA}}'
                '{{#Example_FA}}<div class="example-fa" dir="rtl"><i>"{{Example_FA}}"</i></div>{{/Example_FA}}'
                '{{#PartOfSpeech}}<div class="pos">({{PartOfSpeech}})</div>{{/PartOfSpeech}}'
                '</div>'
            )
            card_b_back = (
                '<div class="card back active-recall">'
                '<h1 class="word">{{Word}}</h1>'
                '<div class="pos"><i>{{PartOfSpeech}}</i> {{#IPA}}[{{IPA}}]{{/IPA}}</div>'
                '{{#Audio}}<div class="audio">{{Audio}}</div>{{/Audio}}'
                '<hr>'
                '{{#Meaning_EN}}<div class="meaning-en"><b>EN:</b> {{Meaning_EN}}</div>{{/Meaning_EN}}'
                '{{#Meaning_FA}}<div class="meaning-fa" dir="rtl"><b>FA:</b> {{Meaning_FA}}</div>{{/Meaning_FA}}'
                '{{#Example_EN}}<div class="example-en"><b>Example:</b> {{Example_EN}}</div>{{/Example_EN}}'
                '{{#Collocations}}<div class="collocations"><b>Collocations:</b> {{Collocations}}</div>{{/Collocations}}'
                '</div>'
            )
            card_templates.append({
                "Name": "Active Recall",
                "Front": card_b_front,
                "Back": card_b_back
            })

        css = (
            ".card { font-family: system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; "
            "font-size: 18px; text-align: center; color: #222; background-color: #fff; padding: 15px; }\n"
            ".word { color: #1a73e8; font-size: 28px; margin-bottom: 5px; }\n"
            ".meaning-fa, .example-fa { font-family: 'Vazirmatn', 'B Nazanin', 'Tahoma', sans-serif; }\n"
            ".meaning-en, .meaning-fa { font-size: 20px; margin: 8px 0; }\n"
            ".example-en, .example-fa { font-size: 16px; color: #444; margin: 4px 0; }\n"
            ".collocations, .synonyms, .antonyms, .notes { font-size: 14px; color: #666; margin-top: 6px; }\n"
            ".pos { color: #666; font-style: italic; }\n"
            ".prompt { color: #d93025; font-size: 16px; margin-bottom: 10px; }"
        )

        try:
            self._invoke(
                "createModel",
                modelName=model_name,
                inOrderFields=in_order_fields,
                css=css,
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
            try:
                return self._invoke("findNotes", query=f'"Word:{word}"')
            except Exception:
                return []

    def get_notes_info(self, note_ids: List[int]) -> List[Dict[str, Any]]:
        try:
            return self._invoke("notesInfo", notes=note_ids)
        except Exception as e:
            logger.error(f"Failed to get notesInfo for {note_ids}: {e}")
            return []

    def update_note_fields(self, note_id: int, fields: Dict[str, str]) -> bool:
        try:
            self._invoke("updateNoteFields", note={"id": note_id, "fields": fields})
            return True
        except Exception as e:
            logger.error(f"Failed to update note {note_id}: {e}")
            return False

    def build_note_fields(self, item: WordItem, audio_filename: Optional[str] = None) -> Dict[str, str]:
        audio_str = f"[sound:{audio_filename}]" if audio_filename else ""
        collocations_str = ", ".join(item.collocations) if item.collocations else ""
        synonyms_str = ", ".join(item.synonyms) if item.synonyms else ""
        antonyms_str = ", ".join(item.antonyms) if item.antonyms else ""

        meaning_en = item.meaning_en or item.meaning or ""
        meaning_fa = item.meaning_fa or ""
        example_en = item.example_en or item.example or ""
        example_fa = item.example_fa or ""
        ipa = item.ipa or item.pronunciation or ""

        return {
            "Word": item.word,
            "IPA": ipa,
            "PartOfSpeech": item.part_of_speech or "",
            "Meaning_EN": meaning_en,
            "Meaning_FA": meaning_fa,
            "Example_EN": example_en,
            "Example_FA": example_fa,
            "Collocations": collocations_str,
            "Synonyms": synonyms_str,
            "Antonyms": antonyms_str,
            "Notes": item.notes or "",
            "Audio": audio_str,
            "Source": item.source or "ChatGPT",
            "Tags": " ".join(item.tags) if item.tags else "",
            # Legacy compatibility fields
            "Meaning": meaning_en if not meaning_fa else f"{meaning_en} / {meaning_fa}".strip(" /"),
            "Example": example_en if not example_fa else f"{example_en} ({example_fa})",
            "Pronunciation": ipa
        }

    def can_add_notes(self, notes: List[Dict[str, Any]]) -> List[bool]:
        return self._invoke("canAddNotes", notes=notes)

    def add_notes(self, notes: List[Dict[str, Any]]) -> List[Optional[int]]:
        return self._invoke("addNotes", notes=notes)
