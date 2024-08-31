# NBG to YNAB Converter

This Python script converts transaction data from an XLSX file (in the format provided by National Bank of Greece) to a CSV file compatible with YNAB (You Need A Budget). The script processes the necessary columns and formats the data to ensure it aligns with YNAB's import requirements.

## Features

- **Date Formatting:** Converts dates from `dd.mm.yyyy` format to `yyyy-mm-dd`.
- **Amount Conversion:** Handles European decimal format (comma as a decimal separator) and correctly signs amounts based on whether the transaction is a debit or credit.
- **Custom Mapping:** Maps Greek column names to YNAB-friendly fields (e.g., `Περιγραφή` to `Payee`, `Ονοματεπώνυμο αντισυμβαλλόμενου` to `Memo`).
- **Support for Account and Card Operations Exports:** The script now supports both Account Operations and Card Operations exports from NBG, automatically identifying the file type and processing it accordingly.
- **Memo Field Cleanup:** Removes prefixes like "E-COMMERCE ΑΓΟΡΑ - " and "3D SECURE E-COMMERCE ΑΓΟΡΑ - " from the `Memo` field for a cleaner and more accurate description.

## Requirements

- Python 3.6+
- Pandas

## Installation

1. **Clone the repository:**

    ```bash
    git clone https://github.com/Nikolay-Sergeev/nbg-to-ynab.git
    cd nbg-to-ynab
    ```

2. **Install the required Python packages:**

    You can install the necessary dependencies using pip:

    ```bash
    pip install pandas
    ```

## Usage

To convert an NBG XLSX file to a YNAB-compatible CSV file:

```bash
python main.py <path_to_xlsx_file>