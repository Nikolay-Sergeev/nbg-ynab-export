import csv
import logging
import os
from pathlib import Path
from typing import Optional

import pandas as pd

from config import SETTINGS_DIR, SUPPORTED_EXT
from converter.account import process_account
from converter.card import process_card
from converter.revolut import process_revolut, validate_revolut_currency
from converter.dispatcher import detect_processor
from converter.utils import (
    read_input,
    exclude_existing,
    extract_date_from_filename,
    generate_output_filename as utils_generate_output_filename,
    normalize_column_name,
    validate_dataframe,
    convert_amount,
    strip_accents,
    sanitize_csv_formulas,
)

__all__ = [
    'normalize_column_name',
    'validate_dataframe',
    'convert_amount',
    'strip_accents',
    'sanitize_csv_formulas',
    'process_account_operations',
    'process_card_operations',
    'process_revolut_operations',
    'validate_revolut_currency',
    'exclude_existing_transactions',
    'extract_date_from_filename',
    'generate_output_filename',
    'generate_actual_output_filename',
    'validate_input_file',
    'ConversionService',
    'load_previous_transactions',
    'detect_processor',
]

# Keep shared helpers imported from converter.utils to avoid divergence.
exclude_existing_transactions = exclude_existing


def process_account_operations(df: pd.DataFrame) -> pd.DataFrame:
    try:
        return process_account(df)
    except Exception as exc:
        raise ValueError(f"Error processing account operations: {exc}")


def process_card_operations(df: pd.DataFrame) -> pd.DataFrame:
    try:
        return process_card(df)
    except Exception as exc:
        raise ValueError(f"Error processing card operations: {exc}")


def process_revolut_operations(df: pd.DataFrame) -> pd.DataFrame:
    try:
        return process_revolut(df)
    except Exception as exc:
        raise ValueError(f"Error processing Revolut operations: {exc}")


PROCESSOR_MAP = {
    'revolut': process_revolut_operations,
    'account': process_account_operations,
    'card': process_card_operations,
}


def _load_input_dataframe(input_file: str) -> pd.DataFrame:
    return read_input(Path(input_file))


def generate_output_filename(
    input_file: str,
    is_revolut: bool = False,
    output_dir: Optional[str] = None,
) -> str:
    """Consistently build YNAB output filenames without duplicating logic."""
    if output_dir:
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
    else:
        target_dir = Path(input_file).parent
    return utils_generate_output_filename(
        input_file,
        output_dir=target_dir,
        force_today=is_revolut,
    )


def load_previous_transactions(csv_file: str) -> pd.DataFrame:
    try:
        return pd.read_csv(csv_file)
    except Exception as e:
        raise ValueError(f"Failed to load previous transactions: {str(e)}")


def _normalize_prev_df_for_dedup(prev_df: pd.DataFrame) -> pd.DataFrame:
    lower_cols = {col.lower(): col for col in prev_df.columns}
    if {'date', 'payee', 'amount'}.issubset(lower_cols):
        rename_map = {
            lower_cols['date']: 'Date',
            lower_cols['payee']: 'Payee',
            lower_cols['amount']: 'Amount',
        }
        if 'memo' in lower_cols:
            rename_map[lower_cols['memo']] = 'Memo'
        elif 'notes' in lower_cols:
            rename_map[lower_cols['notes']] = 'Memo'
        return prev_df.rename(columns=rename_map)
    if {'Date', 'Payee', 'Amount'}.issubset(prev_df.columns):
        return prev_df
    raise ValueError("Previous transactions file must include date/payee/amount columns")


def generate_actual_output_filename(input_file: str, is_revolut: bool = False) -> str:
    ynab_path = Path(
        generate_output_filename(
            input_file,
            is_revolut=is_revolut,
            output_dir=SETTINGS_DIR,
        )
    )
    actual_name = ynab_path.name.replace('_ynab.csv', '_actual.csv')
    return str(ynab_path.with_name(actual_name))


def validate_input_file(file_path: str) -> None:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: '{file_path}'")
    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext not in SUPPORTED_EXT:
        raise ValueError(f"Unsupported file type: '{file_ext}' (must be .xlsx, .xls, or .csv)")


class ConversionService:
    """Service for converting NBG/Revolut exports to YNAB format."""

    @staticmethod
    def convert_to_ynab(
        input_file: str,
        previous_ynab: Optional[str] = None,
        write_output: bool = True,
        output_dir: Optional[str] = None,
    ) -> pd.DataFrame:
        validate_input_file(input_file)
        df = _load_input_dataframe(input_file)
        processor, is_revolut, source = detect_processor(df, PROCESSOR_MAP)
        logging.info("Processing as %s", source)
        ynab_df = processor(df)
        if previous_ynab:
            prev_df = load_previous_transactions(previous_ynab)
            ynab_df = exclude_existing_transactions(ynab_df, prev_df)
        if write_output:
            csv_file = generate_output_filename(
                input_file,
                is_revolut,
                output_dir=output_dir,
            )
            write_df = ynab_df.drop(columns=['ImportId'], errors='ignore')
            safe_df = sanitize_csv_formulas(write_df, columns=['Payee', 'Memo'])
            safe_df.to_csv(csv_file, index=False, quoting=csv.QUOTE_MINIMAL)
            logging.info("Conversion complete. The CSV file is saved as: %s", csv_file)
        return ynab_df

    @staticmethod
    def convert_to_actual(input_file: str, previous_ynab: Optional[str] = None) -> str:
        """Convert to a CSV suitable for Actual Budget import.

        Generates columns: date, payee, amount, notes
        Amount is negative for outflow, positive for inflow.
        """
        validate_input_file(input_file)
        df = _load_input_dataframe(input_file)
        processor, is_revolut, source = detect_processor(df, PROCESSOR_MAP)
        logging.info("Processing as %s for Actual export", source)
        base_df = processor(df)
        if previous_ynab:
            prev_df = load_previous_transactions(previous_ynab)
            prev_df = _normalize_prev_df_for_dedup(prev_df)
            base_df = exclude_existing_transactions(base_df, prev_df)

        # Map to Actual Budget friendly columns
        actual_df = base_df.rename(columns={
            'Date': 'date',
            'Payee': 'payee',
            'Memo': 'notes',
            'Amount': 'amount',
        })[['date', 'payee', 'amount', 'notes']]

        # Write CSV for Actual with fallback if home dir is not writable
        csv_file = generate_actual_output_filename(input_file, is_revolut)
        safe_df = sanitize_csv_formulas(actual_df, columns=['payee', 'notes'])
        try:
            os.makedirs(os.path.dirname(csv_file), exist_ok=True)
            safe_df.to_csv(csv_file, index=False, quoting=csv.QUOTE_MINIMAL)
        except Exception:
            try:
                # Fallback to project-local directory
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                fallback_dir = os.path.join(project_root, '.nbg-ynab-export')
                os.makedirs(fallback_dir, exist_ok=True)
                base = os.path.basename(csv_file)
                csv_file = os.path.join(fallback_dir, base)
                safe_df.to_csv(csv_file, index=False, quoting=csv.QUOTE_MINIMAL)
            except Exception:
                # Final fallback: write next to the input file
                in_dir = os.path.dirname(os.path.abspath(input_file))
                base = os.path.basename(csv_file)
                csv_file = os.path.join(in_dir, base)
                safe_df.to_csv(csv_file, index=False, quoting=csv.QUOTE_MINIMAL)
        logging.info(f"Actual export complete. The CSV file is saved as: {csv_file}")
        return csv_file
