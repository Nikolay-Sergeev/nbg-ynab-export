# converter/account.py
import pandas as pd
from constants import (
    DATE_FMT_ACCOUNT,
    DATE_FMT_YNAB,
    ACCOUNT_REQUIRED_COLUMNS,
)
from config import get_logger
from .utils import validate_dataframe, convert_amount

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
        raise ValueError("Invalid dates in account export")
    df_copy['Payee'] = df_copy['Ονοματεπώνυμο αντισυμβαλλόμενου']
    df_copy['Memo'] = df_copy['Περιγραφή']
    # Amount with robust sign handling based on debit/credit column
    df_copy['Amount'] = df_copy['Ποσό συναλλαγής'].apply(convert_amount)
    indicator = df_copy['Χρέωση / Πίστωση'].astype(str).str.strip().str.upper()
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
    return df_copy[['Date', 'Payee', 'Memo', 'Amount']]
