# converter/account.py
import pandas as pd
from constants import (
    DATE_FMT_ACCOUNT,
    DATE_FMT_YNAB,
    ACCOUNT_REQUIRED_COLUMNS,
    ECOMMERCE_CLEANUP_PATTERN,
    SECURE_ECOMMERCE_CLEANUP_PATTERN,
)
from config import get_logger
from .utils import validate_dataframe, convert_amount, strip_accents

logger = get_logger(__name__)

REQUIRED = ACCOUNT_REQUIRED_COLUMNS


def process_account(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert NBG account export into YNAB CSV format.
    Returns DataFrame with columns ['Date', 'Payee', 'Memo', 'Amount'].
    """
    validate_dataframe(df, REQUIRED)
    df_copy = df.copy()
    df_copy['Date'] = (
        pd.to_datetime(df_copy['Valeur'], format=DATE_FMT_ACCOUNT, errors='coerce')
          .dt.strftime(DATE_FMT_YNAB)
    )
    if df_copy['Date'].isna().any():
        raise ValueError("Invalid date format in account export")
    payee = df_copy['Ονοματεπώνυμο αντισυμβαλλόμενου'].fillna('')
    payee = payee.astype(str)
    payee = payee.str.replace(SECURE_ECOMMERCE_CLEANUP_PATTERN, '', regex=True)
    payee = payee.str.replace(ECOMMERCE_CLEANUP_PATTERN, '', regex=True)
    df_copy['Payee'] = payee.str.strip()
    df_copy['Memo'] = df_copy['Περιγραφή']
    # Fallback: use memo text when payee is missing/blank
    df_copy['Payee'] = df_copy['Payee'].mask(
        df_copy['Payee'].isnull() | (df_copy['Payee'].astype(str).str.strip() == ''),
        df_copy['Memo']
    )
    # Amount with robust sign handling based on debit/credit column
    df_copy['Amount'] = df_copy['Ποσό συναλλαγής'].apply(convert_amount)
    indicator = strip_accents(df_copy['Χρέωση / Πίστωση'].astype(str).str.strip()).str.upper()
    is_debit = (
        indicator.eq('ΧΡΕΩΣΗ') |
        indicator.eq('Χ') |
        indicator.eq('DEBIT') |
        indicator.eq('D')
    )
    is_credit = (
        indicator.eq('ΠΙΣΤΩΣΗ') |
        indicator.eq('Π') |
        indicator.eq('CREDIT') |
        indicator.eq('C')
    )
    df_copy.loc[is_debit, 'Amount'] = -df_copy.loc[is_debit, 'Amount'].abs()
    df_copy.loc[is_credit, 'Amount'] = df_copy.loc[is_credit, 'Amount'].abs()
    df_copy['Amount'] = df_copy['Amount'].round(2)
    if 'Αριθμός αναφοράς' in df_copy.columns:
        df_copy['ImportId'] = df_copy['Αριθμός αναφοράς'].fillna('').astype(str).str.strip()
    columns = ['Date', 'Payee', 'Memo', 'Amount']
    if 'ImportId' in df_copy.columns:
        columns.append('ImportId')
    return df_copy[columns]
