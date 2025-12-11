import converter.revolut as _revolut
import converter.card as _card
import converter.account as _account
import converter.utils as _utils
import pandas as pd
import os
import sys
import csv
import logging
from typing import Optional

from constants import (
    ACCOUNT_REQUIRED_COLUMNS,
    CARD_REQUIRED_COLUMNS,
    DATE_FMT_YNAB,
)

# Configuration
LOGGING_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOGGING_LEVEL = logging.INFO

# File formats
SUPPORTED_EXTENSIONS = ('.xlsx', '.xls', '.csv')
OUTPUT_FORMAT = 'csv'

# Set up logging
logging.basicConfig(
    level=LOGGING_LEVEL,
    format=LOGGING_FORMAT
)

# Constants moved to constants.py


# Facade overrides to support legacy imports
convert_amount = _utils.convert_amount
validate_dataframe = _utils.validate_dataframe
process_card_operations = _card.process_card
process_account_operations = _account.process_account
process_revolut_operations = _revolut.process_revolut
validate_revolut_currency = _revolut.validate_revolut_currency
REVOLUT_REQUIRED_COLUMNS = _revolut.REQUIRED
REVOLUT_CURRENCY_COLUMN = 'Currency'
extract_date_from_filename = _utils.extract_date_from_filename


def load_previous_transactions(csv_file: str) -> pd.DataFrame:
    """Load previously exported transactions from YNAB CSV file.

    Args:
        csv_file: Path to previous YNAB export CSV

    Returns:
        pd.DataFrame: DataFrame with previous transactions
    """
    try:
        return pd.read_csv(csv_file)
    except Exception as e:
        logging.warning(f"Could not load previous transactions: {str(e)}")
        return pd.DataFrame(columns=['Date', 'Payee', 'Memo', 'Amount'])


def exclude_existing_transactions(
    new_df: pd.DataFrame,
    prev_df: pd.DataFrame,
) -> pd.DataFrame:
    """Remove duplicate and older transactions."""
    if prev_df.empty:
        return new_df

    new_df = new_df.copy()
    new_df['Date'] = pd.to_datetime(new_df['Date'])
    prev_df['Date'] = pd.to_datetime(prev_df['Date'])

    latest_prev_date = prev_df['Date'].max()

    # Allow same-day transactions if they're not duplicates
    mask_newer = new_df['Date'] >= latest_prev_date

    # Create unique transaction identifier
    def create_key(df: pd.DataFrame) -> pd.Series:
        return (df['Date'].dt.strftime('%Y-%m-%d') + '_' +
                df['Payee'] + '_' +
                df['Amount'].astype(str))

    new_keys = create_key(new_df)
    prev_keys = create_key(prev_df)
    mask_unique = ~new_keys.isin(prev_keys)

    filtered_df = new_df[mask_newer & mask_unique].copy()
    filtered_df['Date'] = filtered_df['Date'].dt.strftime(DATE_FMT_YNAB)

    excluded_count = len(new_df) - len(filtered_df)
    if excluded_count > 0:
        logging.info(
            f"Excluded {excluded_count} duplicate or older transactions")

    return filtered_df


def generate_output_filename(input_file: str, is_revolut: bool = False) -> str:
    """Generate output filename with consistent logic used across the app."""
    return _utils.generate_output_filename(
        input_file,
        force_today=is_revolut,
    )


def validate_input_file(file_path: str) -> None:
    """Validate input file existence and format.

    Args:
        file_path: Path to input file

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is not supported
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: '{file_path}'")

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            (
                f"Unsupported file type: '{ext}' (must be "
                f"{', '.join(SUPPORTED_EXTENSIONS)})"
            )
        )


def convert_nbg_to_ynab(
    xlsx_file: str,
    previous_ynab: Optional[str] = None,
) -> pd.DataFrame:
    """Convert bank export file to YNAB CSV format.

    Args:
        xlsx_file: Path to the input file
        previous_ynab: Optional path to previous YNAB export

    Returns:
        pd.DataFrame: DataFrame with converted transactions

    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If file format is not recognized
        pd.errors.EmptyDataError: If file is empty
    """
    try:
        validate_input_file(xlsx_file)

        file_ext = os.path.splitext(xlsx_file)[1].lower()
        df = None
        if file_ext in ['.xlsx', '.xls']:
            try:
                df = pd.read_excel(xlsx_file)
            except Exception as excel_err:
                logging.error(f"Failed to read Excel file: {excel_err}")
                raise ValueError(f"Could not read Excel file: {excel_err}")
        elif file_ext == '.csv':
            try:
                df = pd.read_csv(xlsx_file)
            except Exception as csv_err:
                logging.error(f"Failed to read CSV file: {csv_err}")
                raise ValueError(f"Could not read CSV file: {csv_err}")
        else:
            raise ValueError(f"Unsupported file extension: {file_ext}")

        # Add debug logging
        logging.debug(f"Found columns in file: {list(df.columns)}")

        # Determine file type and process accordingly
        is_revolut = False
        if set(REVOLUT_REQUIRED_COLUMNS).issubset(df.columns):
            logging.info("Processing as Revolut statement")
            ynab_df = process_revolut_operations(df)
            is_revolut = True
        elif set(ACCOUNT_REQUIRED_COLUMNS).issubset(df.columns):
            logging.info("Processing as NBG account statement")
            ynab_df = process_account_operations(df)
        elif set(CARD_REQUIRED_COLUMNS).issubset(df.columns):
            logging.info("Processing as NBG card statement")
            ynab_df = process_card_operations(df)
        else:
            raise ValueError("File format not recognized")

        # After creating ynab_df but before saving:
        if previous_ynab:
            prev_df = load_previous_transactions(previous_ynab)
            ynab_df = exclude_existing_transactions(ynab_df, prev_df)

        # Generate output filename with file type info
        csv_file = generate_output_filename(xlsx_file, is_revolut)

        ynab_df.to_csv(csv_file, index=False, quoting=csv.QUOTE_MINIMAL)
        logging.info(
            f"Conversion complete. The CSV file is saved as: {csv_file}")
        return ynab_df

    except FileNotFoundError:
        logging.error(f"File not found: '{xlsx_file}'")
        raise
    except pd.errors.EmptyDataError:
        logging.error(f"Empty or unreadable file: '{xlsx_file}'")
        raise
    except ValueError as e:
        logging.error(f"Validation error: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        raise


if __name__ == "__main__":
    if len(sys.argv) < 2:
        logging.error(
            "Usage: python main.py <path_to_statement_file> "
            "[path_to_previous_ynab.csv]"
        )
        logging.error("Supported formats:")
        logging.error("  - NBG statements: .xlsx, .xls")
        logging.error("  - Revolut exports: .csv")
        sys.exit(1)

    input_file_path = sys.argv[1]
    previous_ynab_path = sys.argv[2] if len(sys.argv) > 2 else None

    # Check if file exists
    if not os.path.exists(input_file_path):
        logging.error(f"File not found: '{input_file_path}'")
        sys.exit(1)

    # Check file extension
    file_ext = os.path.splitext(input_file_path)[1].lower()
    if file_ext not in SUPPORTED_EXTENSIONS:
        logging.error(
            (
                f"Unsupported file type: '{file_ext}' "
                f"(must be .xlsx, .xls, or .csv)"
            )
        )
        sys.exit(1)

    convert_nbg_to_ynab(input_file_path, previous_ynab_path)

__all__ = [
    'convert_amount',
    'extract_date_from_filename',
    'generate_output_filename',
    'exclude_existing_transactions',
    'process_card_operations',
    'process_account_operations',
    'process_revolut_operations',  # Add this
    'validate_dataframe'
]
