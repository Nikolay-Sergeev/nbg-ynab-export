# converter/revolut.py
import pandas as pd
from constants import (
    DATE_FMT_YNAB,
    REVOLUT_REQUIRED_COLUMNS,
)
from config import get_logger
from .utils import validate_dataframe, convert_amount

logger = get_logger(__name__)

REQUIRED = REVOLUT_REQUIRED_COLUMNS


def validate_revolut_currency(df: pd.DataFrame) -> None:
    """
    Ensure all transactions are in EUR.
    """
    if not (df['Currency'] == 'EUR').all():
        raise ValueError("Revolut export must only contain EUR transactions.")


def process_revolut(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert Revolut export to YNAB CSV format.
    Returns DataFrame with columns ['Date', 'Payee', 'Memo', 'Amount'].
    """
    validate_dataframe(df, REQUIRED)
    validate_revolut_currency(df)

    df_copy = df.copy()
    # Parse and format date
    try:
        df_copy['Date'] = pd.to_datetime(df_copy['Started Date'])
    except pd.errors.ParserError as e:
        raise ValueError(f"Date parsing failed: {str(e)}")
    # Amount minus fee
    amounts = df_copy['Amount'].apply(convert_amount)
    fees = df_copy['Fee'].apply(convert_amount)
    df_copy['Amount_sum'] = amounts - fees
    # Filter only completed transactions
    completed = df_copy['State'] == 'COMPLETED'
    df_out = pd.DataFrame({
        'Date': df_copy.loc[completed, 'Date'],
        'Payee': df_copy.loc[completed, 'Description'],
        'Memo': df_copy.loc[completed, 'Type'],
        'Amount': df_copy.loc[completed, 'Amount_sum'].round(2)
    })
    # Show newest first
    df_out = df_out.sort_values(by='Date', ascending=False, kind='mergesort')
    df_out['Date'] = df_out['Date'].dt.strftime(DATE_FMT_YNAB)
    return df_out.reset_index(drop=True)
