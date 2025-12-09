# Repository Guidelines

## Project Structure & Modules
- `cli.py` / `main.py`: CLI entry points for conversions.
- `converter/`: Parsers for NBG account, NBG card, and Revolut (`account.py`, `card.py`, `revolut.py`, `utils.py`).
- `services/`: Core logic and API clients (`conversion_service.py`, `ynab_client.py`, `actual_client.py`, `token_manager.py`).
- `ui/`: PyQt5 wizard (`wizard.py`), controller, and pages.
- `resources/`: UI assets (e.g., `icons/`, `style.qss`).
- `tests/`: Pytest suite (`test_*.py`).

## Build, Test, and Development
Initialize environment and install deps:
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```
Run locally:
```bash
python cli.py path/to/statement.[xlsx|csv]
python ui/wizard.py  # GUI wizard
```
Quality checks:
```bash
pytest -q           # run tests
flake8 .            # style check (max line length 120)
```

## Coding Style & Naming
- Python 3.6+; 4-space indentation; keep lines ≤120 chars (see `.flake8`).
- Prefer type hints and small, focused functions.
- Naming: modules/functions `snake_case`, classes `CapWords`, constants `UPPER_SNAKE`.
- Keep CLI/GUI entry points thin; place logic in `services/` and `converter/`.

## Testing Guidelines
- Framework: `pytest`; tests live in `tests/` and are named `test_*.py`.
- Add tests for new behavior and edge cases (date parsing, sign handling, duplicate detection).
- Use fixtures/utilities from existing tests; avoid networked tests in unit scope.
- Run `pytest` before pushing; do not reduce coverage or delete tests to pass.

## Commit & Pull Requests
- Commits: short, imperative mood. Optional scope prefixes seen in history: `UI:`, `Actual API:`, `test:`, `refactor:`, `fix:`.
- PRs must include: clear description, rationale, before/after notes; link issues; screenshots/GIFs for UI.
- Checklist: `pytest` green, `flake8` clean, docs updated (README/CLAUDE.md/this file) when behavior changes.

## Security & Configuration
- Do not commit secrets. The wizard stores tokens securely; user config lives under `~/.nbg-ynab-export/`.
- Log files may be created there as well; prefer local paths in development when debugging.
- When handling files, never overwrite inputs; outputs follow `original_name_YYYY-MM-DD_ynab.csv`.

