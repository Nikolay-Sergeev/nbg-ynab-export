# Repository Guidelines

## Project Structure & Modules
- `cli.py` / `main.py`: CLI entry points; `cli.py` is the recommended user-facing entry.
- `converter/`: format-specific parsers and shared helpers.
- `services/`: conversion orchestration, YNAB client, Actual client/bridge runner, token storage.
- `ui/`: PyQt5 wizard shell (`wizard.py`), controller/workers, and page components.
- `scripts/`: Node bridge (`actual_bridge.js`) and diagnostics (`actual_diag.py`).
- `tests/`: unit/integration/UI/performance suites.

## Build, Test, and Development

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
npm install --save @actual-app/api

pytest -q
flake8 .
```

Run app:

```bash
python cli.py path/to/statement.[xlsx|xls|csv]
python ui/wizard.py
```

## Coding Style & Naming
- Python, 4-space indentation, line length <= 120.
- Prefer small, focused functions with explicit validation and errors.
- Naming: `snake_case` for functions/modules, `CapWords` for classes, `UPPER_SNAKE` for constants.
- Keep UI/CLI pages thin and move business logic into `services/` and `converter/`.

## Testing Rules
- Framework: `pytest`.
- Do not remove tests to pass changes.
- Add coverage for changed behavior (converter logic, dedupe behavior, worker flow, API mapping).
- Prefer deterministic tests; avoid live network calls in unit scope.

## Security & Configuration
- Never commit secrets.
- Use `services/token_manager.py` for encrypted token/password handling.
- Keep secure file permissions (`0600`) on settings/key/log files where possible.
- Local settings directory: `~/.nbg-ynab-export/`.

Settings files:
- `settings.txt` (`TOKEN:`, `FOLDER:`, `MODE:`)
- `settings.key` (Fernet key)
- `actual_settings.txt` (`ACTUAL_URL:`, `ACTUAL_PWD:`, optional `ACTUAL_E2E_PWD:`)
- `ynab_api.log` (path override with `YNAB_LOG_DIR`)

Env behavior:
- `YNAB_TOKEN` overrides saved token.
- `YNAB_API_DEBUG=1` enables verbose YNAB API payload logging.

## Consistency Rules (Important)

1. De-duplication consistency
- Always use `converter/utils.py:exclude_existing` (or its re-export from `services/conversion_service.py`).
- Default behavior is exact duplicate removal; do not silently reintroduce date-cutoff filtering.

2. Format detection consistency
- Required columns are defined in `constants.py` and checked by `converter/dispatcher.py`.
- If changing required headers, update converters and related tests together.

3. CSV output safety
- Keep formula sanitization (`sanitize_csv_formulas`) before writing CSV files.

4. Actual bridge contract
- Preserve JSON-line command contract between Python runner and `scripts/actual_bridge.js`.
- Keep amount unit conversions stable (milliunits in Python payloads).

## PR Expectations
- Clear summary of behavior change and rationale.
- Mention impacted modules and user-visible effects.
- Include `pytest -q` and `flake8 .` results.
- Include screenshots/GIFs for UI changes.
