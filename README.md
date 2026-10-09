# ChatGPT to Anki Importer (Desktop & CLI)

A fast, reliable, automated desktop application (PyQt6) and CLI tool designed for English vocabulary learning, JSON batch processing, pronunciation audio retrieval, and safe Anki integration via **AnkiConnect**.

---

## Canonical Data Format (Schema Version 1.0)

JSON is the canonical format for exchanging vocabulary data between ChatGPT, the GUI, CLI, and Anki importer.

```json
{
  "schema_version": "1.0",
  "entries": [
    {
      "word": "meticulous",
      "ipa": "/məˈtɪkjələs/",
      "part_of_speech": "adjective",
      "meaning_en": "Very careful about details and accuracy.",
      "meaning_fa": "دقیق و موشکاف",
      "example_en": "She is meticulous about her work.",
      "example_fa": "او در کارش بسیار دقیق است.",
      "collocations": [
        "meticulous planning",
        "meticulous attention to detail"
      ],
      "synonyms": [
        "thorough",
        "precise"
      ],
      "antonyms": [
        "careless",
        "sloppy"
      ],
      "notes": "Often used to describe a person or their work."
    }
  ]
}
```

### Canonical Field Definitions:
- `word` (required): Target English word or expression.
- `ipa` (optional): Phonetic pronunciation string in IPA.
- `part_of_speech` (optional): Part of speech or expression type.
- `meaning_en` (optional): Concise English definition.
- `meaning_fa` (optional): Natural Persian translation.
- `example_en` (optional): Natural English example sentence.
- `example_fa` (optional): Accurate Persian translation of example sentence.
- `collocations` (optional): Array of useful word collocations.
- `synonyms` (optional): Array of relevant synonyms.
- `antonyms` (optional): Array of relevant antonyms.
- `notes` (optional): Usage, register, grammar, or learning notes.

---

## Key Features

1. **Direct Anki Integration**: Uses `AnkiConnect` API to create decks, models, store media files (`[sound:filename.mp3]`), and batch add or update cards.
2. **Two Card Types**:
   - **Card Type A (English Recognition)**: Front displays English word & audio; back reveals definitions, examples, collocations, and Persian translation.
   - **Card Type B (Active Recall)**: Front displays Persian meaning or prompt; back reveals correct English word, IPA, audio, and examples.
3. **Multi-Source Batch Processing**: Supports pasting canonical JSON or text, loading multiple JSON/text/Markdown files, and selecting individual items or input sources.
4. **Audio Retrieval & Fallback Pipeline**:
   - Provider priority: Official Dictionary APIs (Oxford, Merriam-Webster, Cambridge) -> TTS Fallback (Edge TTS / gTTS).
   - Strict audio file validation (HTTP status, size, MIME type, binary SHA256 checksum).
   - Persistent SQLite Audio Cache.
5. **Duplicate Detection & Policies**: `SKIP` (default), `UPDATE`, or `CREATE`.
6. **GUI & CLI Interfaces**:
   - PyQt6 Desktop GUI with cell-editable preview table, JSON validation, and export capability.
   - CLI interface supporting `check-anki`, `validate-json`, `analyze`, `import`, `audio`, and `cache`.

---

## Quick Start Guide

### 1. Requirements & Setup
- Python 3.10+
- Anki installed with the [AnkiConnect](https://ankiweb.net/shared/info/2055492153) add-on.

```bash
# Clone repository and enter directory
cd ~/Projects/English

# Install dependencies
pip install -r requirements.txt

# Copy configuration template
cp .env.example .env
```

### 2. CLI Commands Overview
```bash
# Check AnkiConnect connectivity
python3 -m src.cli check-anki

# Validate JSON files against canonical schema
python3 -m src.cli validate-json sample.json

# Analyze single or multiple files
python3 -m src.cli analyze sample.json notes.txt

# Import vocabulary into Anki
python3 -m src.cli import sample.json

# Test audio retrieval and caching for a word
python3 -m src.cli audio "meticulous"

# List cached audio assets
python3 -m src.cli cache list
```

### 3. Desktop Application
```bash
python3 main.py
```

---

## Testing & Verification

Run the automated test suite:
```bash
PYTHONPATH=. pytest tests/
```

---

## License

MIT
