import os
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

from src.core.config import get_config, setup_logging
from src.database.repository import Database
from src.core.pipeline import ProcessingPipeline
from src.core.models import ItemStatus, DuplicatePolicy


class TestEndToEndIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path("/tmp/chatgpt_anki_test")
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        os.environ["DB_PATH"] = str(self.tmp_dir / "test.db")
        os.environ["CACHE_DIR"] = str(self.tmp_dir / "cache")

        self.config = get_config()
        self.logger = setup_logging(self.config)
        self.db = Database(self.config.db_path)
        self.pipeline = ProcessingPipeline(self.config, self.db)

    @patch("requests.post")
    def test_full_pipeline_flow(self, mock_post):
        # Mock AnkiConnect response
        def _mock_anki_response(url, json, timeout):
            action = json.get("action")
            mock_resp = MagicMock()
            mock_resp.status_code = 200

            if action == "version":
                mock_resp.json.return_value = {"result": 6, "error": None}
            elif action == "deckNames":
                mock_resp.json.return_value = {"result": ["English Vocabulary"], "error": None}
            elif action == "modelNames":
                mock_resp.json.return_value = {"result": ["English Vocabulary"], "error": None}
            elif action == "findNotes":
                mock_resp.json.return_value = {"result": [], "error": None}
            elif action == "storeMediaFile":
                mock_resp.json.return_value = {"result": None, "error": None}
            elif action == "addNotes":
                mock_resp.json.return_value = {"result": [10001, 10002], "error": None}
            else:
                mock_resp.json.return_value = {"result": None, "error": None}

            return mock_resp

        mock_post.side_effect = _mock_anki_response

        raw_chatgpt_text = """
        [ANKI]
        word: deploy
        meaning: مستقر کردن / منتشر کردن
        example: We deploy the application on the server.
        part_of_speech: verb
        tags: technology backend
        [/ANKI]

        [ANKI]
        word: server
        meaning: سرور
        example: The cloud server is active.
        part_of_speech: noun
        tags: technology
        [/ANKI]
        """

        # 1. Analyze
        items = self.pipeline.analyze_text(raw_chatgpt_text)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].word, "deploy")
        self.assertEqual(items[1].word, "server")

        # 2. Process / Import
        processed = self.pipeline.process_items(items)
        self.assertEqual(len(processed), 2)
        self.assertEqual(processed[0].status, ItemStatus.SUCCESS)
        self.assertEqual(processed[1].status, ItemStatus.SUCCESS)

        # 3. Verify Audio Cache
        cached_deploy = self.db.get_cached_audio("deploy")
        self.assertIsNotNone(cached_deploy)
        self.assertEqual(cached_deploy.word, "deploy")

    def test_log_sanitization(self):
        secret_key = "super_secret_api_token_12345"
        self.config.oxford_app_key = secret_key
        logger = setup_logging(self.config)

        # Ensure SecretSanitizingFormatter redacts the secret
        for handler in logger.handlers:
            formatter = handler.formatter
            formatted = formatter.format(
                logger.makeRecord("test", 20, "fn", 1, f"Connecting with key {secret_key}", (), None)
            )
            self.assertNotIn(secret_key, formatted)
            self.assertIn("[REDACTED]", formatted)
