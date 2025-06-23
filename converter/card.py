# converter/card.py
import pandas as pd
import re
from typing import List
from config import DATE_FMT_ACCOUNT, DATE_FMT_YNAB, get_logger
from .utils import validate_dataframe, convert_amount

logger = get_logger(__name__)

REQUIRED = [
    'Ημερομηνία/Ώρα Συναλλαγής',
    'Περιγραφή Κίνησης',
    'Ποσό',
    'Χ/Π'
]

# Cleanup patterns
ECOMMERCE_CLEANUP_PATTERN = r'E-COMMERCE ΑΓΟΡΑ - '
SECURE_ECOMMERCE_CLEANUP_PATTERN = r'3D SECURE E-COMMERCE ΑΓΟΡΑ - '

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
        format=DATE_FMT_ACCOUNT,
        errors='coerce'
    ).dt.strftime(DATE_FMT_YNAB)
    if df_copy['Date'].isna().any():
        raise ValueError("Invalid dates in card export")
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
    # Convert and sign amount
    df_copy['Amount'] = df_copy['Ποσό'].apply(convert_amount)
    debit_mask = (df_copy['Χ/Π'] == 'Χ') & (df_copy['Amount'] > 0)
    df_copy.loc[debit_mask, 'Amount'] *= -1
    df_copy['Amount'] = df_copy['Amount'].round(2)
    return df_copy[['Date', 'Payee', 'Memo', 'Amount']]
