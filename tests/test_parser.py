from src.parser.rule_based import RuleBasedParser


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
