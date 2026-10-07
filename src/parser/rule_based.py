import re
from typing import List, Optional, Dict, Any
from src.parser.base import ContentParser
from src.core.models import WordItem, ItemStatus


class RuleBasedParser(ContentParser):
    def normalize_word(self, word: str) -> str:
        return re.sub(r'[^\w\s-]', '', word).strip().lower()

    def confidence_score(self, text: str) -> float:
        if not text or not text.strip():
            return 0.0

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

        # 1. Try structured [ANKI] blocks first
        anki_items = self._parse_anki_blocks(text)
        if anki_items:
            return anki_items

        # 2. Try Key-Value / Line block formats
        kv_items = self._parse_key_value_blocks(text)
        if kv_items:
            return kv_items

        # 3. Try Markdown list items (e.g. - **deploy**: meaning / example)
        md_items = self._parse_markdown_list(text)
        if md_items:
            return md_items

        # 4. Fallback to freeform line-by-line parsing
        return self._parse_freeform_lines(text)

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
                meaning = data.get('meaning') or data.get('translation') or data.get('definition')
                example = data.get('example') or data.get('sentence')
                pos = data.get('part_of_speech') or data.get('pos')
                pron = data.get('pronunciation') or data.get('ipa')
                tags_raw = data.get('tags') or data.get('category') or ""
                tags = [t.strip() for t in tags_raw.split() if t.strip()]

                items.append(
                    WordItem(
                        word=word,
                        normalized_word=self.normalize_word(word),
                        meaning=meaning,
                        example=example,
                        part_of_speech=pos,
                        pronunciation=pron,
                        tags=tags,
                        status=ItemStatus.PENDING
                    )
                )
        return items

    def _parse_key_value_blocks(self, text: str) -> List[WordItem]:
        # Split text into chunks separated by blank lines or horizontal rules
        chunks = re.split(r'\n\s*\n|---+', text)
        items = []

        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue

            lines = chunk.splitlines()
            data = {}
            for line in lines:
                match = re.match(r'^\s*[*_#-]*\s*(Word|Vocabulary|Term|Meaning|Translation|Definition|Example|Part of Speech|POS|Pronunciation|IPA|Tags|Category)\s*:\s*(.+)$', line, re.IGNORECASE)
                if match:
                    key = match.group(1).lower().replace(' ', '_')
                    val = match.group(2).strip()
                    # Strip markdown bold/italic surrounding val if present
                    val = re.sub(r'^\*\*([^*]+)\*\*$', r'\1', val)
                    data[key] = val

            word = data.get('word') or data.get('vocabulary') or data.get('term')
            if word:
                meaning = data.get('meaning') or data.get('translation') or data.get('definition')
                example = data.get('example') or data.get('sentence')
                pos = data.get('part_of_speech') or data.get('pos')
                pron = data.get('pronunciation') or data.get('ipa')
                tags_raw = data.get('tags') or data.get('category') or ""
                tags = [t.strip() for t in tags_raw.split() if t.strip()]

                items.append(
                    WordItem(
                        word=word,
                        normalized_word=self.normalize_word(word),
                        meaning=meaning,
                        example=example,
                        part_of_speech=pos,
                        pronunciation=pron,
                        tags=tags,
                        status=ItemStatus.PENDING
                    )
                )
        return items

    def _parse_markdown_list(self, text: str) -> List[WordItem]:
        items = []
        # Matches patterns like: - **deploy**: meaning - Example: We deploy software.
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
                    # Look for Example: or Ex: in rest
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
                        meaning=meaning,
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

            # Format: Word - Meaning / Example
            if ':' in line or '-' in line or '–' in line:
                parts = re.split(r'[:\-–—]', line, maxsplit=1)
                word = parts[0].strip()
                # Clean up markdown bold from word
                word = re.sub(r'^\*\*([^*]+)\*\*$', r'\1', word)
                rest = parts[1].strip() if len(parts) > 1 else ""

                if word and len(word.split()) <= 4:  # Vocabulary phrase length limit
                    items.append(
                        WordItem(
                            word=word,
                            normalized_word=self.normalize_word(word),
                            meaning=rest if rest else None,
                            status=ItemStatus.PENDING
                        )
                    )
        return items
