import re
import json
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ItemStatus(str, Enum):
    PENDING = "PENDING"
    PARSING = "PARSING"
    AUDIO_SEARCH = "AUDIO_SEARCH"
    AUDIO_DOWNLOADING = "AUDIO_DOWNLOADING"
    AUDIO_VALIDATING = "AUDIO_VALIDATING"
    TTS_FALLBACK = "TTS_FALLBACK"
    AUDIO_UNAVAILABLE = "AUDIO_UNAVAILABLE"
    ANKI_CREATING = "ANKI_CREATING"
    SUCCESS = "SUCCESS"
    DUPLICATE = "DUPLICATE"
    FAILED = "FAILED"


class DuplicatePolicy(str, Enum):
    SKIP = "SKIP"
    UPDATE = "UPDATE"
    CREATE = "CREATE"


class CanonicalEntrySchema(BaseModel):
    word: str = Field(..., description="Required English word or expression")
    ipa: Optional[str] = Field(default=None, description="Optional pronunciation in IPA")
    part_of_speech: Optional[str] = Field(default=None, description="Part of speech or expression type")
    meaning_en: Optional[str] = Field(default=None, description="Concise English definition")
    meaning_fa: Optional[str] = Field(default=None, description="Natural Persian translation")
    example_en: Optional[str] = Field(default=None, description="Natural English example sentence")
    example_fa: Optional[str] = Field(default=None, description="Accurate Persian translation of example")
    collocations: List[str] = Field(default_factory=list, description="Array of useful collocations")
    synonyms: List[str] = Field(default_factory=list, description="Array of relevant synonyms")
    antonyms: List[str] = Field(default_factory=list, description="Array of relevant antonyms")
    notes: Optional[str] = Field(default=None, description="Optional grammar, usage, register, or learning notes")

    extra_fields: Dict[str, Any] = Field(default_factory=dict, description="Preserved unknown fields")

    @field_validator("word")
    @classmethod
    def validate_word_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field 'word' cannot be empty or whitespace.")
        return v.strip()

    @model_validator(mode="before")
    @classmethod
    def capture_unknown_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            known_keys = {
                "word", "ipa", "part_of_speech", "meaning_en", "meaning_fa",
                "example_en", "example_fa", "collocations", "synonyms",
                "antonyms", "notes", "extra_fields"
            }
            extra = {k: v for k, v in values.items() if k not in known_keys}
            if extra:
                if "extra_fields" not in values or not isinstance(values["extra_fields"], dict):
                    values["extra_fields"] = {}
                values["extra_fields"].update(extra)
        return values


class CanonicalBatchSchema(BaseModel):
    schema_version: str = Field(default="1.0", description="Schema version tag")
    entries: List[CanonicalEntrySchema] = Field(default_factory=list)

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, v: str) -> str:
        if v != "1.0":
            raise ValueError(f"Unsupported schema version '{v}'. Only version '1.0' is supported.")
        return v


class ValidationErrorDetail(BaseModel):
    entry_index: int
    field: str
    message: str


class ValidationReport(BaseModel):
    is_valid: bool
    total_entries: int
    valid_entries: List[CanonicalEntrySchema] = Field(default_factory=list)
    errors: List[ValidationErrorDetail] = Field(default_factory=list)


def normalize_word_str(word: str) -> str:
    return re.sub(r'[^\w\s-]', '', word).strip().lower()


class WordItem(BaseModel):
    id: Optional[int] = None
    word: str
    normalized_word: str
    language: str = "en"
    locale: str = "en-US"
    ipa: Optional[str] = None
    part_of_speech: Optional[str] = None
    meaning_en: Optional[str] = None
    meaning_fa: Optional[str] = None
    example_en: Optional[str] = None
    example_fa: Optional[str] = None
    collocations: List[str] = Field(default_factory=list)
    synonyms: List[str] = Field(default_factory=list)
    antonyms: List[str] = Field(default_factory=list)
    notes: Optional[str] = Field(default=None, description="Learning / usage notes")

    # Legacy fields mapping
    meaning: Optional[str] = None
    example: Optional[str] = None
    pronunciation: Optional[str] = None

    tags: List[str] = Field(default_factory=list)
    source: str = "ChatGPT"
    status: ItemStatus = ItemStatus.PENDING
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    extra_fields: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def sync_legacy_and_canonical_fields(self) -> "WordItem":
        if not self.normalized_word and self.word:
            self.normalized_word = normalize_word_str(self.word)

        if self.ipa and not self.pronunciation:
            self.pronunciation = self.ipa
        elif self.pronunciation and not self.ipa:
            self.ipa = self.pronunciation

        if self.meaning_en and not self.meaning:
            self.meaning = self.meaning_en
        elif self.meaning and not self.meaning_en:
            self.meaning_en = self.meaning

        if self.example_en and not self.example:
            self.example = self.example_en
        elif self.example and not self.example_en:
            self.example_en = self.example

        return self

    def to_canonical_schema(self) -> CanonicalEntrySchema:
        return CanonicalEntrySchema(
            word=self.word,
            ipa=self.ipa or self.pronunciation,
            part_of_speech=self.part_of_speech,
            meaning_en=self.meaning_en or self.meaning,
            meaning_fa=self.meaning_fa,
            example_en=self.example_en or self.example,
            example_fa=self.example_fa,
            collocations=self.collocations,
            synonyms=self.synonyms,
            antonyms=self.antonyms,
            notes=self.notes,
            extra_fields=self.extra_fields
        )

    @classmethod
    def from_canonical_schema(
        cls,
        entry: CanonicalEntrySchema,
        source: str = "JSON",
        tags: Optional[List[str]] = None
    ) -> "WordItem":
        norm = normalize_word_str(entry.word)
        return cls(
            word=entry.word,
            normalized_word=norm,
            ipa=entry.ipa,
            pronunciation=entry.ipa,
            part_of_speech=entry.part_of_speech,
            meaning_en=entry.meaning_en,
            meaning=entry.meaning_en,
            meaning_fa=entry.meaning_fa,
            example_en=entry.example_en,
            example=entry.example_en,
            example_fa=entry.example_fa,
            collocations=entry.collocations,
            synonyms=entry.synonyms,
            antonyms=entry.antonyms,
            notes=entry.notes,
            tags=tags or [],
            source=source,
            extra_fields=entry.extra_fields
        )


def validate_canonical_json(json_str: str) -> ValidationReport:
    """Validate raw JSON string against Canonical Schema deterministically."""
    try:
        data = json.loads(json_str)
    except Exception as e:
        return ValidationReport(
            is_valid=False,
            total_entries=0,
            valid_entries=[],
            errors=[ValidationErrorDetail(entry_index=-1, field="root", message=f"Invalid JSON syntax: {str(e)}")]
        )

    # Allow single entry object, list of entries, or schema object
    schema_version = "1.0"
    raw_entries = []

    if isinstance(data, dict):
        if "schema_version" in data:
            s_ver = str(data["schema_version"])
            if s_ver != "1.0":
                return ValidationReport(
                    is_valid=False,
                    total_entries=0,
                    valid_entries=[],
                    errors=[ValidationErrorDetail(entry_index=-1, field="schema_version", message=f"Unsupported schema version '{s_ver}'. Only '1.0' is supported.")]
                )
        if "entries" in data and isinstance(data["entries"], list):
            raw_entries = data["entries"]
        else:
            # Single entry object
            raw_entries = [data]
    elif isinstance(data, list):
        raw_entries = data
    else:
        return ValidationReport(
            is_valid=False,
            total_entries=0,
            valid_entries=[],
            errors=[ValidationErrorDetail(entry_index=-1, field="root", message="JSON root must be an object or array of entries.")]
        )

    valid_entries: List[CanonicalEntrySchema] = []
    errors: List[ValidationErrorDetail] = []

    for idx, raw in enumerate(raw_entries):
        if not isinstance(raw, dict):
            errors.append(ValidationErrorDetail(entry_index=idx, field="entry", message="Entry must be a JSON object."))
            continue
        try:
            parsed = CanonicalEntrySchema.model_validate(raw)
            valid_entries.append(parsed)
        except Exception as ve:
            # Extract detailed validation errors
            msg = str(ve)
            field = "entry"
            if hasattr(ve, "errors"):
                pydantic_errors = getattr(ve, "errors")()
                if pydantic_errors:
                    first_err = pydantic_errors[0]
                    loc = first_err.get("loc", ())
                    field = ".".join(str(l) for l in loc) if loc else "entry"
                    msg = first_err.get("msg", msg)
            errors.append(ValidationErrorDetail(entry_index=idx, field=field, message=msg))

    is_valid = len(errors) == 0 and len(valid_entries) > 0
    return ValidationReport(
        is_valid=is_valid,
        total_entries=len(raw_entries),
        valid_entries=valid_entries,
        errors=errors
    )


class AudioAsset(BaseModel):
    id: Optional[int] = None
    word_id: Optional[int] = None
    word: str
    normalized_word: str
    provider: str
    locale: str = "en-US"
    source_url: Optional[str] = None
    filename: str
    mime_type: str = "audio/mpeg"
    sha256: str
    file_size: int
    license: str = "UNKNOWN"
    created_at: datetime = Field(default_factory=utc_now)
    last_used_at: datetime = Field(default_factory=utc_now)
    status: str = "VALID"


class AnkiNoteRecord(BaseModel):
    id: Optional[int] = None
    word_id: Optional[int] = None
    word: str
    anki_note_id: Optional[int] = None
    deck: str
    status: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
