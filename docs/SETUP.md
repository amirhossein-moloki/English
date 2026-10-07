# Setup Guide

## System Requirements
- Linux (Arch Linux / CachyOS / Fedora / Ubuntu / Debian)
- Python 3.10+
- Anki 2.1.x running locally with AnkiConnect extension (code: `2055492153`)

## Installation Steps

1. **Clone repository & prepare environment**:
   ```bash
   git clone <repo_url>
   cd <repo_dir>
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Environment Settings**:
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` to set your desired default Deck, Note Type, or Dictionary API credentials if available.

3. **Launch GUI Application**:
   ```bash
   python3 main.py
   ```

4. **Run CLI Tool**:
   ```bash
   python3 -m src.cli --help
   ```
