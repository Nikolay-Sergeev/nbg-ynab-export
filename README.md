# NBG/Revolut to YNAB / Actual Budget Converter

Convert bank exports from National Bank of Greece (NBG) and Revolut into:
- YNAB-compatible CSV
- Actual Budget imports (via API from the GUI, or CSV via service API)

The project ships with:
- CLI (`cli.py`) for fast file conversion
- PyQt5 wizard (`ui/wizard.py`) for guided import/upload workflows

## Supported Inputs

The converter auto-detects source format from required columns.

- NBG Account statement (`.xlsx` / `.xls`)
- NBG Card statement (`.xlsx` / `.xls`)
- Revolut export (`.csv`, EUR only)

Format detection is strict: required column names must match the expected headers.

## What The Converter Does

- Normalizes dates to `YYYY-MM-DD`
- Normalizes amounts (supports `1.234,56` and `1,234.56` style numbers)
- Applies debit/credit sign rules for NBG account/card files
- Filters Revolut rows to `State == COMPLETED`
- Subtracts Revolut `Fee` from `Amount`
- Cleans common NBG prefixes like `E-COMMERCE ΑΓΟΡΑ - ...`
- Adds optional `ImportId` in-memory when `Αριθμός αναφοράς` exists (used by UI duplicate/upload logic)
- Escapes formula-like strings in exported CSV text fields for spreadsheet safety

## Installation

Requirements:
- Python 3.8+
- Node.js + npm (required for Actual API mode)

Setup:

```bash
python3 -m venv venv
source venv/bin/activate  # Windows: .\\venv\\Scripts\\activate
pip install -r requirements.txt
npm install --save @actual-app/api
```

## CLI Usage

Basic conversion:

```bash
python cli.py path/to/statement.[xlsx|xls|csv]
```

With de-duplication against a previous YNAB export:

```bash
python cli.py path/to/statement.[xlsx|xls|csv] --previous path/to/previous_ynab.csv
```

Behavior of `--previous`:
- Removes exact duplicates using `(Date, Payee, Amount, Memo)`
- `Payee`/`Memo` matching is case-insensitive and whitespace-trimmed
- Does **not** drop older transactions by date in default CLI flow

Output naming:
- `original_name_YYYY-MM-DD_ynab.csv`
- NBG files reuse date found in filename when possible
- Revolut CLI conversion uses today's date

## GUI Wizard Usage

Start GUI:

```bash
python ui/wizard.py
```

### Mode: YNAB
Flow:
1. Attach file
2. Verify YNAB token
3. Select budget/account
4. Preview latest account transactions
5. Review rows (duplicates preselected as skipped)
6. Upload

### Mode: Actual Budget (API)
Flow:
1. Attach file
2. Verify Actual server URL/password
3. Select budget/account
4. Preview latest account transactions
5. Review rows
6. Upload via Node bridge (`scripts/actual_bridge.js`)

Notes:
- Remote servers must use `https://` (UI rejects insecure `http://` except localhost)
- Optional encryption password is supported for encrypted Actual budgets
- If bridge/API version mismatch is detected (`out-of-sync-migrations`), client attempts one automatic `npm install --save @actual-app/api` and retries

### Mode: File Converter
Flow:
1. Attach file
2. Review/select rows
3. Export CSV locally (no API calls)

## Actual Budget CSV Export (Service API)

For programmatic usage, `ConversionService.convert_to_actual(...)` writes CSV columns:
- `date`, `payee`, `amount`, `notes`

Write location fallback order:
1. `~/.nbg-ynab-export/`
2. project-local `.nbg-ynab-export/`
3. input file directory

## Settings, Secrets, and Logs

Local app directory:
- `~/.nbg-ynab-export/`

Files:
- `settings.txt`: encrypted YNAB token (`TOKEN:`), last folder (`FOLDER:`), last mode (`MODE:`)
- `settings.key`: Fernet key
- `actual_settings.txt`: encrypted Actual URL/password (+ optional encryption password)
- `ynab_api.log`: YNAB API log

Security behavior:
- Secret files are written with `0600` permissions when possible
- `YNAB_TOKEN` environment variable overrides saved YNAB token
- `YNAB_LOG_DIR` overrides YNAB log location
- `YNAB_API_DEBUG=1` enables verbose YNAB payload logging

## Development

Run quality checks:

```bash
pytest -q
flake8 .
```

Current test suite status at last scan: `200 passed`.

## Project Structure

- `cli.py`, `main.py`: CLI entry points (`main.py` keeps legacy API-style exports)
- `converter/`: source-specific converters and utilities
- `services/`: conversion service, YNAB client, Actual client/bridge runner, token manager
- `ui/`: wizard, pages, async workers/controller
- `scripts/`: Node bridge and Actual diagnostics
- `tests/`: unit/integration/UI/performance tests

## License

GNU GPL v2.0 (`LICENSE`).
