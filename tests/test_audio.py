import os
from pathlib import Path
from src.core.config import get_config
from src.core.models import WordItem
from src.database.repository import Database
from src.audio.validator import AudioValidator
from src.audio.manager import AudioManager


def test_audio_validator():
    # Valid mp3 snippet simulation
    valid_bytes = b"ID3" + b"\x00" * 500
    is_valid, reason, mime, sha256 = AudioValidator.validate_bytes(valid_bytes, "test.mp3", "audio/mpeg")
    assert is_valid is True
    assert mime == "audio/mpeg"
    assert sha256 != ""

    # HTML error page simulation
    html_bytes = b"<!DOCTYPE html><html><body>Error 404</body></html>"
    is_valid_html, reason_html, _, _ = AudioValidator.validate_bytes(html_bytes, "test.mp3", "audio/mpeg")
    assert is_valid_html is False
    assert "HTML" in reason_html


def test_audio_manager_tts_fallback_and_cache(tmp_path):
    os.environ["DB_PATH"] = str(tmp_path / "test_audio.db")
    os.environ["CACHE_DIR"] = str(tmp_path / "cache")
    config = get_config()
    db = Database(config.db_path)

    manager = AudioManager(config, db)

    item = WordItem(word="deploy", normalized_word="deploy")

    # Fetch audio (should fallback to TTS since no dictionary API keys are provided)
    asset = manager.resolve_audio(item)
    assert asset is not None
    assert (config.cache_dir / asset.filename).exists()
    assert asset.provider == "tts"

    # Second call for same word should hit cache
    item2 = WordItem(word="deploy", normalized_word="deploy")
    cached_asset = manager.resolve_audio(item2)
    assert cached_asset is not None
    assert cached_asset.filename == asset.filename
