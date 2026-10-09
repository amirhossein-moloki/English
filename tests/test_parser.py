import json
from src.parser.rule_based import RuleBasedParser, BatchSourceParser
from src.core.models import validate_canonical_json, WordItem, CanonicalEntrySchema


def test_rule_based_parser_anki_block():
    parser = RuleBasedParser()
    text = """
    [ANKI]
    word: deploy
    meaning: مستقر کردن / منتشر کردن
    example: We deploy the app.
    part_of_speech: verb
    tags: technology backend
    [/ANKI]
    """
    items = parser.parse(text)
    assert len(items) == 1
    item = items[0]
    assert item.word == "deploy"
    assert item.normalized_word == "deploy"
    assert "مستقر" in item.meaning
    assert item.example == "We deploy the app."
    assert item.part_of_speech == "verb"
    assert "technology" in item.tags


def test_rule_based_parser_key_value():
    parser = RuleBasedParser()
    text = """
    Word: database
    Meaning: پایگاه داده
    Example: Relational database system.
    Part of Speech: noun
    ---
    Word: algorithm
    Meaning: الگوریتم
    Example: Efficient search algorithm.
    """
    items = parser.parse(text)
    assert len(items) == 2
    assert items[0].word == "database"
    assert items[0].meaning == "پایگاه داده"
    assert items[1].word == "algorithm"


def test_rule_based_parser_markdown_list():
    parser = RuleBasedParser()
    text = """
    - **access control** (noun): کنترل دسترسی - Example: Access control prevents unauthorized usage.
    - **pipeline** (noun): خط لوله داده
    """
    items = parser.parse(text)
    assert len(items) == 2
    assert items[0].word == "access control"
    assert items[0].normalized_word == "access control"
    assert items[0].part_of_speech == "noun"
    assert items[0].example == "Access control prevents unauthorized usage."
    assert items[1].word == "pipeline"


def test_canonical_json_validation_and_parsing():
    parser = RuleBasedParser()
    json_payload = """
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
          "collocations": ["meticulous planning"],
          "synonyms": ["thorough"],
          "antonyms": ["careless"],
          "notes": "Used to describe a person or work.",
          "custom_meta": "preserved_field"
        }
      ]
    }
    """
    report = validate_canonical_json(json_payload)
    assert report.is_valid is True
    assert report.total_entries == 1
    assert len(report.errors) == 0

    items = parser.parse(json_payload)
    assert len(items) == 1
    item = items[0]
    assert item.word == "meticulous"
    assert item.ipa == "/məˈtɪkjələs/"
    assert item.meaning_en == "Very careful about details and accuracy."
    assert item.meaning_fa == "دقیق و موشکاف"
    assert item.example_en == "She is meticulous about her work."
    assert item.example_fa == "او در کارش بسیار دقیق است."
    assert item.collocations == ["meticulous planning"]
    assert item.extra_fields.get("custom_meta") == "preserved_field"

    # Export round-trip check
    canonical_schema = item.to_canonical_schema()
    dumped = canonical_schema.model_dump(exclude_none=True)
    assert dumped["word"] == "meticulous"
    assert dumped["meaning_fa"] == "دقیق و موشکاف"


def test_canonical_json_invalid_version_and_missing_required():
    bad_version_json = '{"schema_version": "2.0", "entries": [{"word": "test"}]}'
    report = validate_canonical_json(bad_version_json)
    assert report.is_valid is False
    assert len(report.errors) > 0
    assert "2.0" in report.errors[0].message

    missing_word_json = '{"schema_version": "1.0", "entries": [{"part_of_speech": "noun"}]}'
    report2 = validate_canonical_json(missing_word_json)
    assert report2.is_valid is False
    assert any(err.field == "word" or "word" in err.message.lower() for err in report2.errors)


def test_batch_source_parser():
    batch_parser = BatchSourceParser()
    sources = {
        "file1.json": '{"schema_version": "1.0", "entries": [{"word": "source1_word"}]}',
        "file2.txt": "Word: source2_word\nMeaning: meaning2"
    }
    results = batch_parser.parse_sources(sources)
    assert len(results["file1.json"]) == 1
    assert results["file1.json"][0].source == "file1.json"
    assert len(results["file2.txt"]) == 1
    assert results["file2.txt"][0].source == "file2.txt"
