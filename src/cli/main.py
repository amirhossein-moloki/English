import sys
import argparse
from pathlib import Path
from typing import List, Dict
from src.core.config import get_config, setup_logging
from src.database.repository import Database
from src.core.pipeline import ProcessingPipeline, PipelineStats
from src.anki.client import AnkiConnectClient
from src.core.models import validate_canonical_json


def main():
    parser = argparse.ArgumentParser(description="ChatGPT to Anki CLI Tool")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # check-anki
    subparsers.add_parser("check-anki", help="Check AnkiConnect connection status")

    # validate-json
    val_parser = subparsers.add_parser("validate-json", help="Validate canonical JSON file(s)")
    val_parser.add_argument("files", nargs="+", help="Path to JSON file(s)")

    # analyze
    analyze_parser = subparsers.add_parser("analyze", help="Analyze input text/JSON file(s)")
    analyze_parser.add_argument("files", nargs="+", help="Path to file(s) containing vocabulary")

    # import
    import_parser = subparsers.add_parser("import", help="Import vocabulary file(s) into Anki")
    import_parser.add_argument("files", nargs="+", help="Path to file(s) containing vocabulary")

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

    elif args.command == "validate-json":
        for file_str in args.files:
            filepath = Path(file_str)
            if not filepath.exists():
                print(f"[ERROR] File not found: {filepath}")
                continue
            text = filepath.read_text(encoding="utf-8")
            report = validate_canonical_json(text)
            print(f"\n--- Validation Report: {filepath.name} ---")
            print(f"Status: {'VALID' if report.is_valid else 'INVALID'}")
            print(f"Total Entries: {report.total_entries}")
            print(f"Valid Entries: {len(report.valid_entries)}")
            print(f"Errors: {len(report.errors)}")
            for err in report.errors:
                print(f"  [Index {err.entry_index}] Field '{err.field}': {err.message}")

    elif args.command == "analyze":
        sources: Dict[str, str] = {}
        for file_str in args.files:
            filepath = Path(file_str)
            if not filepath.exists():
                print(f"[ERROR] File not found: {filepath}")
                continue
            sources[filepath.name] = filepath.read_text(encoding="utf-8")

        items = pipeline.analyze_sources(sources) if len(sources) > 1 else (
            pipeline.analyze_text(next(iter(sources.values())), source_name=next(iter(sources.keys()))) if sources else []
        )
        print(f"Analyzed {len(items)} vocabulary items from {len(sources)} source(s):")
        for item in items:
            meaning = item.meaning_en or item.meaning_fa or item.meaning or "N/A"
            print(f"- [{item.source}] {item.word} | Meaning: {meaning} | Status: {item.status.value}")

    elif args.command == "import":
        sources: Dict[str, str] = {}
        for file_str in args.files:
            filepath = Path(file_str)
            if not filepath.exists():
                print(f"[ERROR] File not found: {filepath}")
                continue
            sources[filepath.name] = filepath.read_text(encoding="utf-8")

        items = pipeline.analyze_sources(sources) if len(sources) > 1 else (
            pipeline.analyze_text(next(iter(sources.values())), source_name=next(iter(sources.keys()))) if sources else []
        )
        print(f"Importing {len(items)} items from {len(sources)} source(s)...")

        def _prog(item, idx, total, stats: PipelineStats):
            print(f"[{idx}/{total}] [{item.source}] {item.word} -> {item.status.value}")

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
