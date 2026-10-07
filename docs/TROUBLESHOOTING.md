# Troubleshooting Guide

## 1. AnkiConnect Connection Error
- **Symptom**: `Failed to connect to AnkiConnect at http://localhost:8765`
- **Solution**:
  1. Ensure Anki application is actively running on your system.
  2. Verify AnkiConnect add-on is installed (Code: `2055492153`).
  3. Ensure no firewall or VPN is blocking `127.0.0.1:8765`.

## 2. Audio Fetch Failures
- **Symptom**: Status shows `TTS_FALLBACK` or `AUDIO_UNAVAILABLE`.
- **Solution**:
  1. Check internet connectivity.
  2. Check if dictionary API keys (`OXFORD_APP_ID`, `MERRIAM_WEBSTER_API_KEY`) are configured in `.env`.
  3. If API limits are reached, the system gracefully falls back to Edge-TTS / gTTS.

## 3. Duplicate Cards Skipped
- **Symptom**: Action status shows `SKIP` for existing words.
- **Solution**:
  Change `DUPLICATE_POLICY` in `.env` or application settings dialog to `UPDATE` or `CREATE`.
