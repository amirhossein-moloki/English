import unittest
from unittest.mock import MagicMock, patch
from src.core.config import get_config
from src.database.repository import Database
from src.core.pipeline import ProcessingPipeline


class TestPipelineAndCLI(unittest.TestCase):
    @patch("requests.post")
    def test_pipeline_analyze(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"result": [], "error": None}
        mock_post.return_value = mock_resp

        config = get_config()
        db = Database(config.db_path)
        pipeline = ProcessingPipeline(config, db)

        sample_text = """
        [ANKI]
        word: deploy
        meaning: مستقر کردن
        [/ANKI]
        """

        items = pipeline.analyze_text(sample_text)
        assert len(items) == 1
        assert items[0].word == "deploy"
        assert items[0].meaning == "مستقر کردن"
