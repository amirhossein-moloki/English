import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from src.core.models import WordItem, AudioAsset, AnkiNoteRecord, ItemStatus, utc_now


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL,
                normalized_word TEXT NOT NULL,
                language TEXT NOT NULL,
                locale TEXT NOT NULL,
                meaning TEXT,
                example TEXT,
                part_of_speech TEXT,
                pronunciation TEXT,
                tags TEXT,
                source TEXT,
                status TEXT NOT NULL,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS audio_assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word_id INTEGER,
                word TEXT NOT NULL,
                normalized_word TEXT NOT NULL,
                provider TEXT NOT NULL,
                locale TEXT NOT NULL,
                source_url TEXT,
                filename TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                license TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(word_id) REFERENCES words(id)
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word_id INTEGER,
                word TEXT NOT NULL,
                anki_note_id INTEGER,
                deck TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(word_id) REFERENCES words(id)
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """)

            conn.commit()

    # --- Audio Asset Operations ---

    def save_audio_asset(self, asset: AudioAsset) -> AudioAsset:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO audio_assets (
                word_id, word, normalized_word, provider, locale, source_url,
                filename, mime_type, sha256, file_size, license, status, created_at, last_used_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                asset.word_id, asset.word, asset.normalized_word, asset.provider, asset.locale,
                asset.source_url, asset.filename, asset.mime_type, asset.sha256, asset.file_size,
                asset.license, asset.status, asset.created_at.isoformat(), asset.last_used_at.isoformat()
            ))
            asset.id = cursor.lastrowid
            conn.commit()
            return asset

    def get_cached_audio(self, normalized_word: str, locale: str = "en-US") -> Optional[AudioAsset]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM audio_assets
            WHERE normalized_word = ? AND locale = ? AND status = 'VALID'
            ORDER BY id DESC LIMIT 1
            """, (normalized_word, locale))
            row = cursor.fetchone()
            if not row:
                return None

            now_iso = utc_now().isoformat()
            cursor.execute("UPDATE audio_assets SET last_used_at = ? WHERE id = ?", (now_iso, row["id"]))
            conn.commit()

            return AudioAsset(
                id=row["id"],
                word_id=row["word_id"],
                word=row["word"],
                normalized_word=row["normalized_word"],
                provider=row["provider"],
                locale=row["locale"],
                source_url=row["source_url"],
                filename=row["filename"],
                mime_type=row["mime_type"],
                sha256=row["sha256"],
                file_size=row["file_size"],
                license=row["license"],
                status=row["status"],
                created_at=datetime.fromisoformat(row["created_at"]),
                last_used_at=utc_now()
            )

    def list_cached_audio(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audio_assets ORDER BY id DESC")
            return [dict(row) for row in cursor.fetchall()]
