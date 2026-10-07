import os
from pathlib import Path
from src.core.config import Config, get_config, setup_logging
from src.core.models import WordItem, AudioAsset, ItemStatus
from src.database.repository import Database


def test_config_and_db(tmp_path):
    test_db_path = tmp_path / "test.db"
    test_cache_dir = tmp_path / "cache"

    os.environ["DB_PATH"] = str(test_db_path)
    os.environ["CACHE_DIR"] = str(test_cache_dir)
    os.environ["OXFORD_APP_ID"] = "test_secret_12345"

    config = get_config()
    logger = setup_logging(config)

    assert config.db_path == test_db_path
    assert config.cache_dir == test_cache_dir

    db = Database(config.db_path)

    # Test audio asset caching
    asset = AudioAsset(
        word="deploy",
        normalized_word="deploy",
        provider="test_provider",
        filename="deploy.mp3",
        sha256="dummy_hash",
        file_size=1024,
        license="TEST_LICENSE"
    )
    saved = db.save_audio_asset(asset)
    assert saved.id is not None

    cached = db.get_cached_audio("deploy")
    assert cached is not None
    assert cached.filename == "deploy.mp3"
    assert cached.provider == "test_provider"
    print("Database & Config test passed successfully!")
