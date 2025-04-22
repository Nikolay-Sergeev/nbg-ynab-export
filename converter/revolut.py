# converter/revolut.py
import pandas as pd
from config import DATE_FMT_YNAB, get_logger
from .utils import validate_dataframe, convert_amount

logger = get_logger(__name__)

REQUIRED = [
    'Started Date', 'Description', 'Type', 'Amount', 'Fee', 'State', 'Currency'
]

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
    df_copy['Date'] = pd.to_datetime(df_copy['Started Date']).dt.strftime(DATE_FMT_YNAB)
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
    return df_out.reset_index(drop=True)
