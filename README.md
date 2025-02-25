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
  - Processes fees in Revolut transactions
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

## Requirements

- Python 3.6+
- pandas

## Installation

```bash
git clone https://github.com/Nikolay-Sergeev/nbg-to-ynab.git
cd nbg-to-ynab
pip install pandas
```
