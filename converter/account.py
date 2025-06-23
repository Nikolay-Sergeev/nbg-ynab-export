# converter/account.py
import pandas as pd
from config import DATE_FMT_ACCOUNT, DATE_FMT_YNAB, get_logger
from .utils import validate_dataframe, convert_amount

logger = get_logger(__name__)

REQUIRED = [
    'Valeur', 'Ονοματεπώνυμο αντισυμβαλλόμενου',
    'Περιγραφή', 'Ποσό συναλλαγής', 'Χρέωση / Πίστωση'
]

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
    df_copy['Amount'] = df_copy['Ποσό συναλλαγής'].apply(convert_amount)
    # Flip to negative only if debit and amount positive
    debit_mask = (df_copy['Χρέωση / Πίστωση'] == 'Χρέωση') & (df_copy['Amount'] > 0)
    df_copy.loc[debit_mask, 'Amount'] *= -1
    df_copy['Amount'] = df_copy['Amount'].round(2)
    return df_copy[['Date', 'Payee', 'Memo', 'Amount']]
