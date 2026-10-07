# Architecture Overview - ChatGPT to Anki Bridge

## System Architecture Flow

```
ChatGPT Text Input / Clipboard
         │
         ▼
  ┌──────────────┐
  │  Parser      │ (RuleBasedParser / LLMParser)
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │ Word Entries │ (Normalized Word Data)
  └──────┬───────┘
         │
         ├──────────────────────────────┐
         ▼                              ▼
  ┌──────────────┐             ┌─────────────────┐
  │ Audio System │             │ Duplicate Check │ (AnkiConnect + SQLite)
  └──────┬───────┘             └────────┬────────┘
         │                              │
         ▼                              │
  ┌──────────────┐                      │
  │ Provider Chain│                     │
  │ (Oxford/MW/  │                      │
  │  Cambridge/  │                      │
  │  TTS)        │                      │
  └──────┬───────┘                      │
         │                              │
         ▼                              │
  ┌──────────────┐                      │
  │ Validator &  │                      │
  │ SQLite Cache │                      │
  └──────┬───────┘                      │
         │                              │
         └──────────────┬───────────────┘
                        │
                        ▼
               ┌─────────────────┐
               │ Batch Pipeline  │ (Independent per-word status)
               └────────┬────────┘
                        │
                        ▼
               ┌─────────────────┐
               │  AnkiConnect    │ (storeMediaFile + addNotes)
               └─────────────────┘
```

## Component Architecture

1. **`src/core/config.py`**: Configuration manager loading from `.env` and environment variables. Automatically redacts API keys and secrets in logs.
2. **`src/database/`**: SQLite-backed repository maintaining persistent cache for `words`, `audio_assets`, `notes`, `providers`, `processing_jobs`, and `settings`.
3. **`src/parser/`**:
   - `ContentParser`: Base abstraction.
   - `RuleBasedParser`: Parses Markdown formatted text, key-value pairs (`word:`, `meaning:`), standard vocabulary outputs, and `[ANKI]...[/ANKI]` blocks.
   - `LLMParser`: Interface for fallback to LLM when confidence is low.
4. **`src/audio/`**:
   - `AudioProvider`: Abstract base class with lifecycle hooks.
   - Implementations: `OxfordAudioProvider`, `MerriamWebsterAudioProvider`, `CambridgeAudioProvider`, `TTSFallbackProvider` (gTTS / Edge-TTS).
   - `AudioValidator`: Verifies HTTP status, file size limits, MIME types, binary integrity, and computes SHA256 hashes.
   - `AudioCache`: SQLite-backed persistent cache storing full media assets and license metadata.
5. **`src/media/`**:
   - `MediaProvider` & `ImageProvider`: Abstractions ensuring future Image Providers (Wikimedia, Unsplash, Pexels) can be added seamlessly without breaking audio architecture.
6. **`src/anki/`**:
   - `AnkiConnectClient`: High-level wrapper for AnkiConnect API calls (`deckNames`, `modelNames`, `createDeck`, `createModel`, `canAddNotes`, `storeMediaFile`, `addNotes`, `notesInfo`).
   - `DuplicateDetector`: Word normalization (`lowercase`, `trim`, configurable punctuation handling) and duplicate handling policies (`SKIP`, `UPDATE`, `CREATE`).
7. **`src/ui/` & `src/cli/`**:
   - PyQt6 GUI desktop interface with real-time status table, stats counter, selection check-boxes, and settings window.
   - Click/argparse CLI tool for `analyze`, `import`, `audio`, `check-anki`, and `cache`.

## License & Source Metadata Model
Each retrieved media asset records:
- `provider`: Provider identifier (e.g., `oxford`, `merriam_webster`, `edge_tts`)
- `source_url`: Origin URL
- `license`: Verification status (`VERIFIED_API`, `PUBLIC_DOMAIN`, `UNKNOWN`)
- `sha256`: Cryptographic integrity checksum
