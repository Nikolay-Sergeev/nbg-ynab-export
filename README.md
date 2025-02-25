# NBG to YNAB Converter

This Python script converts transaction data from National Bank of Greece (NBG) XLSX files to YNAB-compatible CSV format. It supports both account statements and card statements.

## Features

- **Multiple Statement Types:** Supports both NBG Account Operations and Card Operations exports
- **Date Handling:** 
  - Account statements: Uses 'Valeur' (value date) instead of transaction date
  - Card statements: Extracts date from datetime field
- **Amount Processing:**
  - Handles European number format (comma as decimal separator)
  - Correctly signs amounts based on debit/credit indicators
  - Rounds all amounts to 2 decimal places
- **Description Cleanup:**
  - Removes e-commerce prefixes:
    - `E-COMMERCE ΑΓΟΡΑ - `
    - `3D SECURE E-COMMERCE ΑΓΟΡΑ - `
  - Removes text in parentheses
  - Example: "3D SECURE E-COMMERCE ΑΓΟΡΑ - SPOTIFY" → "SPOTIFY"
- **Error Handling:**
  - Validates required columns
  - Checks file format and existence
  - Provides detailed error messages
- **Logging:** Includes debug logging for troubleshooting
- **Duplicate Prevention:**
  - Optional: Provide previous YNAB export to exclude already imported transactions
  - Compares Date, Payee, and Amount to identify duplicates
  - Only exports new transactions

## Requirements

- Python 3.6+
- pandas

## Installation

```bash
git clone https://github.com/Nikolay-Sergeev/nbg-to-ynab.git
cd nbg-to-ynab
pip install pandas
```

## Usage

Convert an NBG statement to YNAB format:

```bash
python main.py path/to/statement.xlsx [path/to/previous_ynab.csv]
```

Examples:
```bash
# Basic conversion
python main.py Downloads/Finance/statement.xlsx

# Convert excluding transactions from previous export
python main.py Downloads/Finance/statement.xlsx Downloads/Finance/statement_ynab.csv
```

The script will:
1. Detect the statement type (account or card)
2. Process the data accordingly
3. Save a YNAB-compatible CSV with "_ynab" suffix

Example:
```bash
python main.py Downloads/Finance/statement.xlsx
# Creates: Downloads/Finance/statement_ynab.csv
```
