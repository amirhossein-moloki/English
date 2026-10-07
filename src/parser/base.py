from abc import ABC, abstractmethod
from typing import List
from src.core.models import WordItem


class ContentParser(ABC):
    @abstractmethod
    def parse(self, text: str) -> List[WordItem]:
        """Parse raw input text into a list of WordItem objects."""
        pass

    @abstractmethod
    def confidence_score(self, text: str) -> float:
        """Estimate parser confidence score (0.0 to 1.0) for the given input text."""
        pass
