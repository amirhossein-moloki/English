from enum import Enum
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field


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


class WordItem(BaseModel):
    id: Optional[int] = None
    word: str
    normalized_word: str
    language: str = "en"
    locale: str = "en-US"
    meaning: Optional[str] = None
    example: Optional[str] = None
    part_of_speech: Optional[str] = None
    pronunciation: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    source: str = "ChatGPT"
    status: ItemStatus = ItemStatus.PENDING
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)


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
