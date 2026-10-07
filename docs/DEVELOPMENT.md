# Development & Testing Guide

## Project Structure
```
.
├── main.py
├── src/
│   ├── core/           # Config, logging, models
│   ├── database/       # SQLite models & repositories
│   ├── parser/         # RuleBasedParser & LLMParser
│   ├── audio/          # Providers, validator, cache
│   ├── media/          # Base MediaProvider abstractions
│   ├── anki/           # AnkiConnect client & duplicate detector
│   ├── ui/             # PyQt6 desktop UI components
│   └── cli/            # CLI commands
├── tests/              # Pytest unit and integration tests
└── docs/               # Technical documentation
```

## Running Tests
Run pytest with output verbosity:
```bash
pytest -v
```

Run test suite with coverage:
```bash
pytest --cov=src tests/
```
