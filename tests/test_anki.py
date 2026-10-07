import unittest
from unittest.mock import MagicMock, patch
from src.core.config import get_config
from src.core.models import DuplicatePolicy
from src.anki.client import AnkiConnectClient
from src.anki.duplicate import DuplicateDetector


class TestAnkiConnectAndDuplicate(unittest.TestCase):
    @patch("requests.post")
    def test_anki_client_connection_and_methods(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"result": 6, "error": None}
        mock_post.return_value = mock_resp

        config = get_config()
        client = AnkiConnectClient(config)

        assert client.is_connected() is True

        # Test find_notes_by_word
        mock_resp.json.return_value = {"result": [12345], "error": None}
        note_ids = client.find_notes_by_word("deploy", "English Vocabulary", "English Vocabulary")
        assert note_ids == [12345]

    @patch("requests.post")
    def test_duplicate_detector(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"result": [1001], "error": None}
        mock_post.return_value = mock_resp

        config = get_config()
        client = AnkiConnectClient(config)
        detector = DuplicateDetector(client, DuplicatePolicy.SKIP)

        is_dup, note_ids = detector.check_duplicate("Deploy", "English Vocabulary", "English Vocabulary")
        assert is_dup is True
        assert note_ids == [1001]
