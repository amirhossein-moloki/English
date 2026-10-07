# ChatGPT to Anki Importer (Desktop & CLI)

A fast, automated Linux desktop application and CLI tool designed for **Arch Linux / CachyOS** (and other Linux distros) that ingests ChatGPT output, parses English vocabulary & expressions, fetches high-quality native audio pronunciations with fallback TTS, checks for duplicate cards, and directly pushes notes to **Anki** via **AnkiConnect**.

---

## Documentation Index

- [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed software architecture and data pipeline design
- [SETUP.md](docs/SETUP.md) - Prerequisites, installation, and setup instructions
- [ANKI_SETUP.md](docs/ANKI_SETUP.md) - AnkiConnect configuration and custom Note Model guide
- [AUDIO_PROVIDERS.md](docs/AUDIO_PROVIDERS.md) - Audio provider hierarchy, fallback, validation, and caching
- [DEVELOPMENT.md](docs/DEVELOPMENT.md) - Project structure, running tests, and adding features
- [LICENSES.md](docs/LICENSES.md) - Media asset licensing policy and API terms compliance
- [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - Common problems and solutions

---

## Key Features

1. **Direct Anki Integration**: Uses `AnkiConnect` API to create decks, models, store media files (`[sound:filename.mp3]`), and batch add cards without manual file importing.
2. **Robust Multi-Format Parsing**: Parses structured `[ANKI]` blocks, Markdown lists, key-value pairs (`Word:`, `Meaning:`), and free-form vocabulary text.
3. **High-Quality Audio Pipeline**:
   - Provider priority order: Official Dictionary APIs (Oxford, Merriam-Webster, Cambridge) -> TTS Fallback (Edge TTS / gTTS).
   - Strict audio file validation (HTTP status, size, MIME type, binary checksum).
   - Persistent SQLite Audio Cache to prevent duplicate downloads.
4. **Duplicate Detection & Policies**:
   - Normalization (`lowercase`, `trim`, phrase handling).
   - Configurable policy: `SKIP` (default), `UPDATE`, or `CREATE`.
5. **Per-Item Error Isolation**: Batch processing never fails due to a single bad word or missing audio.
6. **Linux Desktop GUI & CLI**:
   - Modern **PyQt6** desktop UI with real-time stats and batch selection.
   - Comprehensive **CLI** interface for command-line automation and debugging.

---

## Quick Start Guide

### 1. Requirements & Setup
- Python 3.10+
- Anki installed and running with the [AnkiConnect](https://ankiweb.net/shared/info/2055492153) add-on.

```bash
# Clone repository and enter directory
cd /path/to/repo

# Install dependencies
pip install -r requirements.txt

# Copy configuration template
cp .env.example .env
```

### 2. Verify Anki Connection
Make sure Anki is running, then test connection via CLI:
```bash
python3 -m src.cli check-anki
```

### 3. Run Desktop Application
```bash
python3 main.py
```

---

## License

MIT
