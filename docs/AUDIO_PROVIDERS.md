# Audio Providers, Fallbacks & Caching Architecture

## 1. Provider Abstraction & Priority
The application uses an extensible provider model:
1. `OxfordAudioProvider`: Native pronunciations from Oxford Dictionaries API.
2. `MerriamWebsterAudioProvider`: Native pronunciations from Merriam-Webster API.
3. `CambridgeAudioProvider`: API audio adapter for Cambridge pronunciation resources.
4. `TTSFallbackProvider`: High quality TTS fallback using Edge-TTS or gTTS.

## 2. Validation Standard
Before any audio file is stored or added to Anki, it passes `AudioValidator`:
- Successful HTTP response code (200 OK)
- Valid MIME type (`audio/mpeg`, `audio/mp3`, `audio/wav`, `audio/ogg`)
- Non-empty binary content
- Maximum file size compliance (default 5MB)
- Integrity check generating SHA256 checksum

## 3. Persistent SQLite Audio Cache
Downloaded audio files are stored in `CACHE_DIR` and recorded in SQLite database `audio_cache`:
- Cache checks prevent redundant HTTP downloads and bandwidth overuse.
- Enables offline card generation for previously queried vocabulary.
