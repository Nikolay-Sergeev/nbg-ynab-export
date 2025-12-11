# converter/card.py
import pandas as pd
from constants import (
    DATE_FMT_CARD,
    DATE_FMT_YNAB,
    CARD_REQUIRED_COLUMNS,
    ECOMMERCE_CLEANUP_PATTERN,
    SECURE_ECOMMERCE_CLEANUP_PATTERN,
)
from config import get_logger
from .utils import validate_dataframe, convert_amount, strip_accents

logger = get_logger(__name__)

REQUIRED = CARD_REQUIRED_COLUMNS

# Cleanup patterns imported from constants


def process_card(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert NBG card export into YNAB CSV format.
    Returns DataFrame with columns ['Date', 'Payee', 'Memo', 'Amount'].
    """
    validate_dataframe(df, REQUIRED)
    df_copy = df.copy()
    # Parse and format date
    df_copy['Date'] = pd.to_datetime(
        df_copy['Ημερομηνία/Ώρα Συναλλαγής'].str.split().str[0],
        format=DATE_FMT_CARD,
        errors='coerce'
    ).dt.strftime(DATE_FMT_YNAB)
    if df_copy['Date'].isna().any():
        raise ValueError("Invalid date format in card export")
    # Clean up payee
    raw_payee = df_copy['Περιγραφή Κίνησης']
    # Remove any parentheses and their contents
    payee = raw_payee.str.replace(r'\s*\([^)]*\)', '', regex=True)
    # Remove secure ecommerce prefix first
    payee = payee.str.replace(SECURE_ECOMMERCE_CLEANUP_PATTERN, '', regex=True)
    # Remove standard ecommerce prefix
    payee = payee.str.replace(ECOMMERCE_CLEANUP_PATTERN, '', regex=True)
    df_copy['Payee'] = payee.str.strip()
    df_copy['Memo'] = df_copy['Περιγραφή Κίνησης']
    # Convert and sign amount robustly using debit/credit indicator when present
    df_copy['Amount'] = df_copy['Ποσό'].apply(convert_amount)
    if 'Χ/Π' in df_copy.columns:
        indicator = strip_accents(df_copy['Χ/Π'].astype(str).str.strip()).str.upper()
        is_debit = indicator.eq('Χ') | indicator.eq('DEBIT') | indicator.eq('D')
        is_credit = indicator.eq('Π') | indicator.eq('CREDIT') | indicator.eq('C')
        df_copy.loc[is_debit, 'Amount'] = -df_copy.loc[is_debit, 'Amount'].abs()
        df_copy.loc[is_credit, 'Amount'] = df_copy.loc[is_credit, 'Amount'].abs()
    df_copy['Amount'] = df_copy['Amount'].round(2)
    return df_copy[['Date', 'Payee', 'Memo', 'Amount']]
