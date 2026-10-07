import json
import logging
from typing import List, Optional
from src.parser.base import ContentParser
from src.core.models import WordItem, ItemStatus
from src.core.config import Config

logger = logging.getLogger("chatgpt_anki.parser")


class LLMParser(ContentParser):
    """LLM Content Parser Abstraction.
    Allows extracting structured vocabulary from complex/unstructured text using LLM APIs.
    """

    def __init__(self, config: Config):
        self.config = config
        self.provider = config.llm_provider
        self.api_key = config.llm_api_key
        self.model = config.llm_model

    def confidence_score(self, text: str) -> float:
        return 0.9 if self.api_key else 0.0

    def parse(self, text: str) -> List[WordItem]:
        if not self.api_key:
            logger.warning("LLMParser called without LLM_API_KEY configured.")
            return []

        # Placeholder implementation for LLM parsing
        logger.info(f"LLMParser invoked with provider={self.provider}, model={self.model}")
        return []
