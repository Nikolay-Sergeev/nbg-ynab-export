# NBG/Revolut to YNAB Converter

This Python script converts transaction data from National Bank of Greece (NBG) and Revolut exports to YNAB-compatible CSV format. It supports NBG account statements, NBG card statements, and Revolut CSV exports.

## Features

- **Multiple Statement Types:** 
  - NBG Account Operations
  - NBG Card Operations
  - Revolut CSV exports
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
  - Optional: Exclude previously imported transactions
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

## Usage

### Basic Usage

Convert a statement to YNAB format:
```bash
python main.py path/to/statement.[xlsx|csv]
```

### Advanced Usage

Convert excluding previously imported transactions:
```bash
python main.py path/to/statement.[xlsx|csv] path/to/previous_ynab.csv
```

### Examples

```bash
# NBG Account Statement
python main.py Downloads/Finance/statementexport25-02-2025.xlsx

# NBG Card Statement
python main.py Downloads/Finance/CardStatementExport.xlsx

# Revolut Export
python main.py Downloads/Finance/account-statement.csv

# With Previous Transactions
python main.py Downloads/Finance/new_statement.xlsx Downloads/Finance/previous_ynab.csv
```

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

Run tests:
```bash
# Using unittest (default)
python -m unittest test_main.py -v

# Or using pytest
pytest
```

Check code style (linting):
```bash
flake8 main.py test_main.py
```

## GUI Wizard

For an interactive GUI, launch:
```bash
python ui/wizard.py
```

The wizard will guide you through:
1. Step 1: Select your input file (dialog remembers last-used folder).
2. Step 2: Enter and securely save your YNAB personal access token.
3. Step 3: Choose YNAB budget and account.
4. Step 4: Confirm and generate/upload transactions.

Settings are stored in `~/.nbg-ynab-export/nbg_ynab_settings.txt`.

## License

MIT License - See LICENSE file for details
