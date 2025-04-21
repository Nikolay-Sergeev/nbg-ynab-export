import pandas as pd
import os
import csv
import logging
from typing import Optional
from main import (
    ACCOUNT_REQUIRED_COLUMNS, CARD_REQUIRED_COLUMNS, REVOLUT_REQUIRED_COLUMNS,
    process_account_operations, process_card_operations, process_revolut_operations,
    load_previous_transactions, exclude_existing_transactions, generate_output_filename, validate_input_file
)

class ConversionService:
    """Service for converting NBG/Revolut exports to YNAB format."""

    @staticmethod
    def convert_to_ynab(input_file: str, previous_ynab: Optional[str] = None) -> pd.DataFrame:
        """Convert a bank export file to YNAB CSV format and return the DataFrame."""
        validate_input_file(input_file)
        file_ext = os.path.splitext(input_file)[1].lower()
        if file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(input_file)
        elif file_ext == '.csv':
            df = pd.read_csv(input_file)
        else:
            raise ValueError(f"Unsupported file extension: {file_ext}")
        # Determine file type and process accordingly
        is_revolut = False
        if set(REVOLUT_REQUIRED_COLUMNS).issubset(df.columns):
            ynab_df = process_revolut_operations(df)
            is_revolut = True
        elif set(ACCOUNT_REQUIRED_COLUMNS).issubset(df.columns):
            ynab_df = process_account_operations(df)
        elif set(CARD_REQUIRED_COLUMNS).issubset(df.columns):
            ynab_df = process_card_operations(df)
        else:
            raise ValueError("File format not recognized")
        if previous_ynab:
            prev_df = load_previous_transactions(previous_ynab)
            ynab_df = exclude_existing_transactions(ynab_df, prev_df)
        csv_file = generate_output_filename(input_file, is_revolut)
        ynab_df.to_csv(csv_file, index=False, quoting=csv.QUOTE_MINIMAL)
        logging.info(f"Conversion complete. The CSV file is saved as: {csv_file}")
        return ynab_df
