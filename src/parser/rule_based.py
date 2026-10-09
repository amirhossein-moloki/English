import re
import json
from typing import List, Optional, Dict, Any
from src.parser.base import ContentParser
from src.core.models import (
    WordItem,
    ItemStatus,
    CanonicalEntrySchema,
    validate_canonical_json
)


class RuleBasedParser(ContentParser):
    def normalize_word(self, word: str) -> str:
        return re.sub(r'[^\w\s-]', '', word).strip().lower()

    def confidence_score(self, text: str) -> float:
        if not text or not text.strip():
            return 0.0

        stripped = text.strip()
        if (stripped.startswith("{") or stripped.startswith("[")) and ("word" in stripped.lower() or "entries" in stripped.lower()):
            return 1.0

        score = 0.5
        if "[ANKI]" in text and "[/ANKI]" in text:
            score += 0.4
        if re.search(r'^\s*(word|meaning|example|part_of_speech|translation|definition):', text, re.IGNORECASE | re.MULTILINE):
            score += 0.3
        if re.search(r'^\s*[-*•]\s+\*\*([^*]+)\*\*', text, re.MULTILINE):
            score += 0.2

        return min(score, 1.0)

    def parse(self, text: str) -> List[WordItem]:
        if not text or not text.strip():
            return []

        # 1. Try Canonical JSON parsing first
        json_items = self._parse_json(text)
        if json_items:
            return json_items

        # 2. Try structured [ANKI] blocks
        anki_items = self._parse_anki_blocks(text)
        if anki_items:
            return anki_items

        # 3. Try Key-Value / Line block formats
        kv_items = self._parse_key_value_blocks(text)
        if kv_items:
            return kv_items

        # 4. Try Markdown list items (e.g. - **deploy**: meaning / example)
        md_items = self._parse_markdown_list(text)
        if md_items:
            return md_items

        # 5. Fallback to freeform line-by-line parsing
        return self._parse_freeform_lines(text)

    def _parse_json(self, text: str) -> List[WordItem]:
        report = validate_canonical_json(text)
        if report.valid_entries:
            items = []
            for entry in report.valid_entries:
                item = WordItem.from_canonical_schema(entry, source="JSON")
                items.append(item)
            return items
        return []

    def _parse_anki_blocks(self, text: str) -> List[WordItem]:
        blocks = re.findall(r'\[ANKI\](.*?)\[/ANKI\]', text, re.DOTALL | re.IGNORECASE)
        items = []

        for block in blocks:
            data = {}
            for line in block.strip().splitlines():
                if ':' in line:
                    k, v = line.split(':', 1)
                    data[k.strip().lower().replace(' ', '_')] = v.strip()

            word = data.get('word') or data.get('vocabulary') or data.get('term')
            if word:
                meaning_en = data.get('meaning_en') or data.get('meaning') or data.get('definition')
                meaning_fa = data.get('meaning_fa') or data.get('translation')
                example_en = data.get('example_en') or data.get('example') or data.get('sentence')
                example_fa = data.get('example_fa')
                pos = data.get('part_of_speech') or data.get('pos')
                pron = data.get('pronunciation') or data.get('ipa')
                tags_raw = data.get('tags') or data.get('category') or ""
                tags = [t.strip() for t in tags_raw.split() if t.strip()]

                items.append(
                    WordItem(
                        word=word,
                        normalized_word=self.normalize_word(word),
                        meaning_en=meaning_en,
                        meaning=meaning_en,
                        meaning_fa=meaning_fa,
                        example_en=example_en,
                        example=example_en,
                        example_fa=example_fa,
                        part_of_speech=pos,
                        pronunciation=pron,
                        ipa=pron,
                        tags=tags,
                        status=ItemStatus.PENDING
                    )
                )
        return items

    def _parse_key_value_blocks(self, text: str) -> List[WordItem]:
        chunks = re.split(r'\n\s*\n|---+', text)
        items = []

        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue

            lines = chunk.splitlines()
            data = {}
            for line in lines:
                match = re.match(r'^\s*[*_#-]*\s*(Word|Vocabulary|Term|Meaning_EN|Meaning_FA|Meaning|Translation|Definition|Example_EN|Example_FA|Example|Part of Speech|POS|Pronunciation|IPA|Collocations|Synonyms|Antonyms|Notes|Tags|Category)\s*:\s*(.+)$', line, re.IGNORECASE)
                if match:
                    key = match.group(1).lower().replace(' ', '_')
                    val = match.group(2).strip()
                    val = re.sub(r'^\*\*([^*]+)\*\*$', r'\1', val)
                    data[key] = val

            word = data.get('word') or data.get('vocabulary') or data.get('term')
            if word:
                meaning_en = data.get('meaning_en') or data.get('meaning') or data.get('definition')
                meaning_fa = data.get('meaning_fa') or data.get('translation')
                example_en = data.get('example_en') or data.get('example') or data.get('sentence')
                example_fa = data.get('example_fa')
                pos = data.get('part_of_speech') or data.get('pos')
                pron = data.get('pronunciation') or data.get('ipa')
                collocations = [c.strip() for c in data.get('collocations', '').split(',') if c.strip()]
                synonyms = [s.strip() for s in data.get('synonyms', '').split(',') if s.strip()]
                antonyms = [a.strip() for a in data.get('antonyms', '').split(',') if a.strip()]
                notes = data.get('notes')
                tags_raw = data.get('tags') or data.get('category') or ""
                tags = [t.strip() for t in tags_raw.split() if t.strip()]

                items.append(
                    WordItem(
                        word=word,
                        normalized_word=self.normalize_word(word),
                        meaning_en=meaning_en,
                        meaning=meaning_en,
                        meaning_fa=meaning_fa,
                        example_en=example_en,
                        example=example_en,
                        example_fa=example_fa,
                        part_of_speech=pos,
                        pronunciation=pron,
                        ipa=pron,
                        collocations=collocations,
                        synonyms=synonyms,
                        antonyms=antonyms,
                        notes=notes,
                        tags=tags,
                        status=ItemStatus.PENDING
                    )
                )
        return items

    def _parse_markdown_list(self, text: str) -> List[WordItem]:
        items = []
        pattern = r'^\s*[-*•]\s+\*\*([^*]+)\*\*\s*(?:\(([^)]+)\))?\s*[:\-–—]?\s*(.*?)$'
        for line in text.splitlines():
            line = line.strip()
            match = re.match(pattern, line)
            if match:
                word = match.group(1).strip()
                pos = match.group(2).strip() if match.group(2) else None
                rest = match.group(3).strip() if match.group(3) else None

                meaning = None
                example = None

                if rest:
                    ex_match = re.search(r'(?:example|ex)\s*:\s*(.+)$', rest, re.IGNORECASE)
                    if ex_match:
                        example = ex_match.group(1).strip()
                        meaning = rest[:ex_match.start()].strip(" :-–—")
                    else:
                        meaning = rest

                items.append(
                    WordItem(
                        word=word,
                        normalized_word=self.normalize_word(word),
                        meaning_en=meaning,
                        meaning=meaning,
                        example_en=example,
                        example=example,
                        part_of_speech=pos,
                        status=ItemStatus.PENDING
                    )
                )
        return items

    def _parse_freeform_lines(self, text: str) -> List[WordItem]:
        items = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if ':' in line or '-' in line or '–' in line:
                parts = re.split(r'[:\-–—]', line, maxsplit=1)
                word = parts[0].strip()
                word = re.sub(r'^\*\*([^*]+)\*\*$', r'\1', word)
                rest = parts[1].strip() if len(parts) > 1 else ""

                if word and len(word.split()) <= 4:
                    items.append(
                        WordItem(
                            word=word,
                            normalized_word=self.normalize_word(word),
                            meaning_en=rest if rest else None,
                            meaning=rest if rest else None,
                            status=ItemStatus.PENDING
                        )
                    )
        return items


class BatchSourceParser:
    """Supports batch parsing from multiple named input sources."""

    def __init__(self, parser: Optional[ContentParser] = None):
        self.parser = parser or RuleBasedParser()

    def parse_sources(self, sources: Dict[str, str]) -> Dict[str, List[WordItem]]:
        """Given a dict of source_name -> text, parse each source into WordItems, tagged with source name."""
        results = {}
        for source_name, text in sources.items():
            items = self.parser.parse(text)
            for item in items:
                item.source = source_name
            results[source_name] = items
        return results
