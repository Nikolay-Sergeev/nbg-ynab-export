# NBG/Revolut to YNAB / Actual Budget Converter

This project converts transaction exports from National Bank of Greece (NBG) and Revolut into:
- **YNAB-compatible CSV** (CLI and GUI)
- **Actual Budget-compatible CSV / direct upload** (GUI, via Node bridge)

Supported inputs:
- NBG account statements (`.xlsx` / `.xls`)
- NBG card statements (`.xlsx` / `.xls`)
- Revolut exports (`.csv`, EUR only)

## Features

- **Multiple Statement Types:** 
  - NBG Account Operations
  - NBG Card Operations
  - Revolut CSV exports
- **Multiple Export Targets (GUI):**
  - YNAB upload
  - Actual Budget API upload
  - File converter (no upload, just a YNAB CSV)
- **Date Handling:** 
  - NBG Account statements: Uses 'Valeur' (value date)
  - NBG Card statements: Extracts date from datetime field
  - Revolut: Uses 'Started Date'
- **Amount Processing:**
  - Handles European number format (NBG)
  - Processes fees in Revolut transactions (automatically deducts from amount)
  - Correctly signs amounts based on transaction type
  - Rounds all amounts to 2 decimal places
- **Description Cleanup:**
  - NBG: Removes e-commerce prefixes:
    - `E-COMMERCE ΑΓΟΡΑ - `
    - `3D SECURE E-COMMERCE ΑΓΟΡΑ - `
  - Revolut: Uses Description as payee and Type as memo
- **Error Handling:**
  - Validates required columns
  - Checks file format and existence
  - Provides detailed error messages
- **Transaction Filtering:**
  - NBG: Processes all transactions
  - Revolut: Only includes COMPLETED transactions
  - Optional: Exclude previously imported transactions (see `--previous`)
- **Smart File Naming:**
  - Uses date from input filename (NBG)
  - Uses current date for Revolut exports
  - Format: `{original_name}_{YYYY-MM-DD}_ynab.csv`

## Implemented Improvements

### API Rate Limit Optimization
- Session-level cache for fetched YNAB transactions
- Only fetch transactions once per account per session
- Navigating back/forth or re-reviewing does not trigger extra API requests
- Cache is invalidated if budget/account selection changes
- All uploads use batch API endpoint

### UI/UX Improvements
- SVG icons for error, success, upload, info
- No unnecessary left margins in drag/drop or error areas
- Only filename shown in file input
- Error messages wrap and are never cut off
- Tooltips for all icons

## Requirements

- Python 3.6+
- pandas
- openpyxl
- PyQt5>=5.15
- requests
- cryptography
- flake8 (development)
- pytest (development)
- Node.js + npm (required for Actual API mode)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Nikolay-Sergeev/nbg-ynab-export.git
cd nbg-ynab-export
```

2. Create and activate a virtual environment:
```bash
# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
.\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. (Actual API mode only) Install Node dependencies:
```bash
npm install
```

## Usage

Convert a statement to YNAB format (recommended CLI entry point):
```bash
python cli.py path/to/statement.[xlsx|csv]
```

Exclude previously imported transactions:
```bash
python cli.py path/to/statement.[xlsx|csv] --previous path/to/previous_ynab.csv
```

De-duplication semantics:
- Transactions older than the latest date in the previous export are dropped.
- Remaining rows are deduplicated by `(Date, Payee, Amount, Memo)` (case-insensitive for Payee/Memo).

### Supported File Types

- NBG Account Statements: `.xlsx`, `.xls`
- NBG Card Statements: `.xlsx`, `.xls`
- Revolut Exports: `.csv`

### Output

The script generates a YNAB-compatible CSV file in the same directory as the input file:
- NBG files: Uses date from filename or current date
- Revolut files: Always uses current date
- Format: `original_name_YYYY-MM-DD_ynab.csv`

## Development

See [CLAUDE.md](CLAUDE.md) for contributor guidelines, environment setup, and
additional architectural details. Run the test suite with `pytest` and check
style using `flake8` before submitting changes.

## GUI Wizard

For an interactive GUI, launch:
```bash
python ui/wizard.py
```

On the first page you can choose an export mode:
- **YNAB**: verify token, select budget/account, review & upload to YNAB.
- **Actual API**: verify Actual server URL/password, select budget/account, review & upload to Actual Budget.
- **File Converter**: review & choose rows to export; generates a YNAB CSV without uploading anywhere.

### Settings and Logs

All local config is stored under `~/.nbg-ynab-export/` with file mode `0600`:
- `settings.txt`: encrypted YNAB token (`TOKEN:` line) and last-used folder (`FOLDER:` line).
- `settings.key`: Fernet key used to encrypt/decrypt tokens.
- `actual_settings.txt`: encrypted Actual server URL/password (`ACTUAL_URL:` / `ACTUAL_PWD:`).
- `ynab_api.log`: YNAB API debug log (request/response summaries).

Environment variables:
- `YNAB_TOKEN`: overrides the saved YNAB token.
- `YNAB_LOG_DIR`: overrides where `ynab_api.log` is written.

Duplicate checking in GUI uses configurable range in `config.py` (`DUP_CHECK_DAYS`, `DUP_CHECK_COUNT`).

### Actual Budget Notes

Actual API mode uses a small Node bridge (`scripts/actual_bridge.js`) backed by `@actual-app/api`.
If `node_modules/` is missing, run `npm install` in the repo root.
For connectivity troubleshooting, run:
```bash
python scripts/actual_diag.py https://your-actual-host/api yourPassword
```

### Known Limitations

- Format detection requires exact column names; if your export headers differ slightly (extra spaces/case),
  rename the columns in the input file to match the expected bank format.
- Revolut exports must be EUR-only; mixed-currency files are rejected.

## License

GNU General Public License v2.0 - See LICENSE file for details
