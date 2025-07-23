import pandas as pd
import os
import csv
import logging
from typing import Optional
from datetime import datetime
import re
from config import SETTINGS_DIR
from constants import (
    DATE_FMT_ACCOUNT,
    DATE_FMT_CARD,
    DATE_FMT_YNAB,
    ACCOUNT_REQUIRED_COLUMNS,
    CARD_REQUIRED_COLUMNS,
    REVOLUT_REQUIRED_COLUMNS,
    ACCOUNT_DATE_COLUMN,
    ACCOUNT_PAYEE_COLUMN,
    ACCOUNT_MEMO_COLUMN,
    ACCOUNT_AMOUNT_COLUMN,
    ACCOUNT_DEBIT_CREDIT_COLUMN,
    CARD_DATE_COLUMN,
    CARD_PAYEE_COLUMN,
    CARD_AMOUNT_COLUMN,
    CARD_DEBIT_CREDIT_COLUMN,
    REVOLUT_DATE_COLUMN,
    REVOLUT_PAYEE_COLUMN,
    REVOLUT_TYPE_COLUMN,
    REVOLUT_AMOUNT_COLUMN,
    REVOLUT_FEE_COLUMN,
    REVOLUT_STATE_COLUMN,
    REVOLUT_CURRENCY_COLUMN,
    MEMO_CLEANUP_PATTERN,
    ECOMMERCE_CLEANUP_PATTERN,
    SECURE_ECOMMERCE_CLEANUP_PATTERN,
)
from converter.utils import (
    normalize_column_name,
    validate_dataframe,
    convert_amount,
)

# --- Conversion functions ---
def process_account_operations(df: pd.DataFrame) -> pd.DataFrame:
    validate_dataframe(df, ACCOUNT_REQUIRED_COLUMNS)
    try:
        ynab_df = pd.DataFrame()
        ynab_df['Date'] = pd.to_datetime(
            df[ACCOUNT_DATE_COLUMN], format=DATE_FORMAT_ACCOUNT, errors='coerce'
        ).dt.strftime(DATE_FORMAT_YNAB)
        if ynab_df['Date'].isna().any():
            raise ValueError(f"Invalid date format found in {ACCOUNT_DATE_COLUMN}")
        ynab_df['Payee'] = df[ACCOUNT_PAYEE_COLUMN].str.replace(ECOMMERCE_CLEANUP_PATTERN, '', regex=True)
        ynab_df['Payee'] = ynab_df['Payee'].str.replace(SECURE_ECOMMERCE_CLEANUP_PATTERN, '', regex=True)
        ynab_df['Memo'] = df[ACCOUNT_MEMO_COLUMN]
        # Fallback: if Payee is empty, use Memo
        ynab_df['Payee'] = ynab_df['Payee'].mask(ynab_df['Payee'].isnull() | (
            ynab_df['Payee'].astype(str).str.strip() == ''), ynab_df['Memo'])
        ynab_df['Amount'] = df[ACCOUNT_AMOUNT_COLUMN].apply(convert_amount)
        df[ACCOUNT_DEBIT_CREDIT_COLUMN] = df[ACCOUNT_DEBIT_CREDIT_COLUMN].str.strip()
        debit_condition = (df[ACCOUNT_DEBIT_CREDIT_COLUMN] == 'Χρέωση') & (ynab_df['Amount'] > 0)
        ynab_df.loc[debit_condition, 'Amount'] *= -1
        ynab_df['Amount'] = ynab_df['Amount'].round(2)
        return ynab_df
    except Exception as e:
        raise ValueError(f"Error processing account operations: {str(e)}")


def process_card_operations(df: pd.DataFrame) -> pd.DataFrame:
    validate_dataframe(df, CARD_REQUIRED_COLUMNS)
    try:
        ynab_df = pd.DataFrame()
        ynab_df['Date'] = pd.to_datetime(
            df[CARD_DATE_COLUMN].apply(lambda x: x.split()[0]),
            format=DATE_FORMAT_CARD
        ).dt.strftime(DATE_FORMAT_YNAB)
        if ynab_df['Date'].isna().any():
            raise ValueError(f"Invalid date format found in {CARD_DATE_COLUMN}")
        # Clean up payee: remove parenthetical text, then ecommerce prefixes
        raw_payee = df[CARD_PAYEE_COLUMN].str.replace(MEMO_CLEANUP_PATTERN, '', regex=True)
        payee = raw_payee.str.replace(SECURE_ECOMMERCE_CLEANUP_PATTERN, '', regex=True)
        payee = payee.str.replace(ECOMMERCE_CLEANUP_PATTERN, '', regex=True)
        ynab_df['Payee'] = payee.str.strip()
        ynab_df['Memo'] = df[CARD_PAYEE_COLUMN]
        ynab_df['Amount'] = df[CARD_AMOUNT_COLUMN].apply(convert_amount)
        df[CARD_DEBIT_CREDIT_COLUMN] = df[CARD_DEBIT_CREDIT_COLUMN].str.strip()
        debit_condition = (df[CARD_DEBIT_CREDIT_COLUMN] == 'Χ') & (ynab_df['Amount'] > 0)
        ynab_df.loc[debit_condition, 'Amount'] *= -1
        ynab_df['Amount'] = ynab_df['Amount'].round(2)
        return ynab_df
    except Exception as e:
        raise ValueError(f"Error processing card operations: {str(e)}")


def validate_revolut_currency(df: pd.DataFrame) -> None:
    if not all(df[REVOLUT_CURRENCY_COLUMN] == 'EUR'):
        raise ValueError("Revolut export must only contain EUR transactions.")


def process_revolut_operations(df: pd.DataFrame) -> pd.DataFrame:
    validate_dataframe(df, REVOLUT_REQUIRED_COLUMNS)
    validate_revolut_currency(df)
    try:
        ynab_df = pd.DataFrame()
        ynab_df['Date'] = pd.to_datetime(df[REVOLUT_DATE_COLUMN]).dt.strftime(DATE_FORMAT_YNAB)
        ynab_df['Payee'] = df[REVOLUT_PAYEE_COLUMN]
        ynab_df['Memo'] = df[REVOLUT_TYPE_COLUMN]
        # Amount minus fee, only for COMPLETED
        completed = df[REVOLUT_STATE_COLUMN] == 'COMPLETED'
        amounts = df[REVOLUT_AMOUNT_COLUMN].apply(convert_amount)
        fees = df[REVOLUT_FEE_COLUMN].apply(convert_amount)
        ynab_df['Amount'] = amounts - fees
        ynab_df = ynab_df[completed].copy()
        ynab_df['Amount'] = ynab_df['Amount'].round(2)
        return ynab_df
    except Exception as e:
        raise ValueError(f"Error processing Revolut operations: {str(e)}")


def load_previous_transactions(csv_file: str) -> pd.DataFrame:
    try:
        return pd.read_csv(csv_file)
    except Exception as e:
        raise ValueError(f"Failed to load previous transactions: {str(e)}")


def exclude_existing_transactions(new_df: pd.DataFrame, prev_df: pd.DataFrame) -> pd.DataFrame:
    def create_key(df):
        return (
            df['Date'].astype(str) + '|' +
            df['Payee'].astype(str).str.lower().str.strip() + '|' +
            df['Amount'].astype(str) + '|' +
            df['Memo'].astype(str).str.lower().str.strip()
        )
    new_keys = create_key(new_df)
    prev_keys = set(create_key(prev_df))
    mask = ~new_keys.isin(prev_keys)
    return new_df[mask].copy()


def extract_date_from_filename(filename: str) -> str:
    match = re.search(r'(\d{2}-\d{2}-\d{4})', filename)
    if match:
        dt = datetime.strptime(match.group(1), '%d-%m-%Y')
        return dt.strftime(DATE_FORMAT_YNAB)
    return ''


def generate_output_filename(input_file: str, is_revolut: bool = False) -> str:
    base, _ = os.path.splitext(os.path.basename(input_file))
    base = re.sub(r'(?:_)?(\d{2}-\d{2}-\d{4}|\d{4}-\d{2}-\d{2})$', '', base)
    if is_revolut:
        date_str = datetime.now().strftime(DATE_FORMAT_YNAB)
    else:
        date_str = extract_date_from_filename(os.path.basename(input_file))
        if not date_str:
            date_str = datetime.now().strftime(DATE_FORMAT_YNAB)
    suffix = 'ynab.csv'
    return os.path.join(SETTINGS_DIR, f"{base}_{date_str}_{suffix}")


def validate_input_file(file_path: str) -> None:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: '{file_path}'")
    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext not in ('.xlsx', '.xls', '.csv'):
        raise ValueError(f"Unsupported file type: '{file_ext}' (must be .xlsx, .xls, or .csv)")


class ConversionService:
    """Service for converting NBG/Revolut exports to YNAB format."""

    @staticmethod
    def convert_to_ynab(input_file: str, previous_ynab: Optional[str] = None) -> pd.DataFrame:
        validate_input_file(input_file)
        file_ext = os.path.splitext(input_file)[1].lower()
        if file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(input_file)
        elif file_ext == '.csv':
            df = pd.read_csv(input_file)
        else:
            raise ValueError(f"Unsupported file extension: {file_ext}")
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
