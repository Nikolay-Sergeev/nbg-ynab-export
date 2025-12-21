import logging
import sys
from typing import Optional

import pandas as pd

from constants import (
    ACCOUNT_REQUIRED_COLUMNS,
    CARD_REQUIRED_COLUMNS,
    DATE_FMT_YNAB,
    REVOLUT_REQUIRED_COLUMNS,
)
from config import SUPPORTED_EXT
from services.conversion_service import (
    ConversionService,
    convert_amount,
    validate_dataframe,
    process_card_operations,
    process_account_operations,
    process_revolut_operations,
    validate_revolut_currency,
    extract_date_from_filename,
    generate_output_filename,
    exclude_existing_transactions,
    validate_input_file,
    load_previous_transactions,
)

# Configuration
LOGGING_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOGGING_LEVEL = logging.INFO

# File formats
SUPPORTED_EXTENSIONS = tuple(SUPPORTED_EXT)
OUTPUT_FORMAT = 'csv'

# Set up logging
logging.basicConfig(
    level=LOGGING_LEVEL,
    format=LOGGING_FORMAT
)


def convert_nbg_to_ynab(
    xlsx_file: str,
    previous_ynab: Optional[str] = None,
) -> pd.DataFrame:
    """Convert a bank export file to YNAB CSV format."""
    return ConversionService.convert_to_ynab(xlsx_file, previous_ynab=previous_ynab)


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

    try:
        convert_nbg_to_ynab(input_file_path, previous_ynab_path)
    except Exception as exc:
        logging.error("Conversion failed: %s", exc)
        sys.exit(1)

__all__ = [
    'convert_amount',
    'extract_date_from_filename',
    'generate_output_filename',
    'exclude_existing_transactions',
    'process_card_operations',
    'process_account_operations',
    'process_revolut_operations',
    'validate_dataframe',
    'validate_revolut_currency',
    'validate_input_file',
    'load_previous_transactions',
    'convert_nbg_to_ynab',
    'SUPPORTED_EXTENSIONS',
    'ACCOUNT_REQUIRED_COLUMNS',
    'CARD_REQUIRED_COLUMNS',
    'REVOLUT_REQUIRED_COLUMNS',
    'DATE_FMT_YNAB',
]
