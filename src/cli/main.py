import sys
import argparse
from pathlib import Path
from src.core.config import get_config, setup_logging
from src.database.repository import Database
from src.core.pipeline import ProcessingPipeline
from src.anki.client import AnkiConnectClient


def main():
    parser = argparse.ArgumentParser(description="ChatGPT to Anki CLI Tool")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # check-anki
    subparsers.add_parser("check-anki", help="Check AnkiConnect connection status")

    # analyze
    analyze_parser = subparsers.add_parser("analyze", help="Analyze input text file")
    analyze_parser.add_argument("file", help="Path to text file containing ChatGPT output")

    # import
    import_parser = subparsers.add_parser("import", help="Import text file directly into Anki")
    import_parser.add_argument("file", help="Path to text file containing ChatGPT output")

    # audio
    audio_parser = subparsers.add_parser("audio", help="Fetch and cache audio for a single word")
    audio_parser.add_argument("word", help="English word")

    # cache
    cache_parser = subparsers.add_parser("cache", help="Manage audio cache")
    cache_parser.add_argument("action", choices=["list"], help="Cache operation")

    args = parser.parse_args()

    config = get_config()
    logger = setup_logging(config)
    db = Database(config.db_path)
    pipeline = ProcessingPipeline(config, db)

    if args.command == "check-anki":
        client = AnkiConnectClient(config)
        connected = client.is_connected()
        if connected:
            print("[SUCCESS] Connected to AnkiConnect successfully!")
            print("Available Decks:", client.get_deck_names())
        else:
            print(f"[ERROR] Could not connect to AnkiConnect at {config.anki_connect_url}")
            sys.exit(1)

    elif args.command == "analyze":
        filepath = Path(args.file)
        if not filepath.exists():
            print(f"[ERROR] File not found: {filepath}")
            sys.exit(1)
        text = filepath.read_text(encoding="utf-8")
        items = pipeline.analyze_text(text)
        print(f"Analyzed {len(items)} vocabulary items:")
        for item in items:
            print(f"- {item.word} | Meaning: {item.meaning or 'N/A'} | Status: {item.status.value}")

    elif args.command == "import":
        filepath = Path(args.file)
        if not filepath.exists():
            print(f"[ERROR] File not found: {filepath}")
            sys.exit(1)
        text = filepath.read_text(encoding="utf-8")
        items = pipeline.analyze_text(text)
        print(f"Importing {len(items)} items...")

        def _prog(item, idx, total):
            print(f"[{idx}/{total}] {item.word} -> {item.status.value}")

        pipeline.process_items(items, progress_callback=_prog)
        print("Import completed!")

    elif args.command == "audio":
        from src.core.models import WordItem
        item = WordItem(word=args.word, normalized_word=args.word.lower())
        asset = pipeline.audio_manager.resolve_audio(item)
        if asset:
            print(f"[SUCCESS] Audio cached: {asset.filename} (Provider: {asset.provider})")
        else:
            print(f"[FAILED] Could not retrieve audio for '{args.word}'")

    elif args.command == "cache":
        if args.action == "list":
            assets = db.list_cached_audio()
            print(f"Total Cached Audio Files: {len(assets)}")
            for a in assets:
                print(f"- {a['word']} | File: {a['filename']} | Provider: {a['provider']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
