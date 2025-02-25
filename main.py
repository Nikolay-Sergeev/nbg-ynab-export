import pandas as pd
import os
import sys
import csv
import logging
from datetime import datetime
from typing import Union, List

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Date format constants
DATE_FORMAT_ACCOUNT = '%d.%m.%Y'
DATE_FORMAT_CARD = '%d/%m/%Y'
DATE_FORMAT_YNAB = '%Y-%m-%d'

# ...existing constants (ACCOUNT_REQUIRED_COLUMNS, etc.)...

def validate_dataframe(df: pd.DataFrame, required_columns: List[str]) -> None:
    """Validate that DataFrame contains all required columns.
    
    Args:
        df: DataFrame to validate
        required_columns: List of required column names
        
    Raises:
        ValueError: If any required columns are missing
    """
    missing_columns = set(required_columns) - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

def convert_amount(amount: Union[str, float, int]) -> float:
    """Convert amount to float, handling both string and numeric inputs.
    
    Args:
        amount: The amount to convert as string or number
        
    Returns:
        float: The converted amount
    """
    if isinstance(amount, str):
        return float(amount.replace(',', '.'))
    return float(amount)

def process_account_operations(df: pd.DataFrame) -> pd.DataFrame:
    """Process the Account Operations Export and convert it to YNAB format.
    
    Args:
        df: Input DataFrame with account operations
        
    Returns:
        pd.DataFrame: Processed DataFrame in YNAB format
    """
    validate_dataframe(df, ACCOUNT_REQUIRED_COLUMNS)
    
    try:
        ynab_df = pd.DataFrame()
        ynab_df['Date'] = pd.to_datetime(
            df[ACCOUNT_DATE_COLUMN], format=DATE_FORMAT_ACCOUNT, errors='coerce'
        ).dt.strftime(DATE_FORMAT_YNAB)
        
        if ynab_df['Date'].isna().any():
            raise ValueError(f"Invalid date format found in {ACCOUNT_DATE_COLUMN}")

        ynab_df['Payee'] = df[ACCOUNT_PAYEE_COLUMN].where(
            df[ACCOUNT_PAYEE_COLUMN].notna() & (df[ACCOUNT_PAYEE_COLUMN] != ''), 
            df[ACCOUNT_MEMO_COLUMN]
        )
        ynab_df['Memo'] = df[ACCOUNT_MEMO_COLUMN]

        ynab_df['Amount'] = df[ACCOUNT_AMOUNT_COLUMN].apply(convert_amount)
        df[ACCOUNT_DEBIT_CREDIT_COLUMN] = df[ACCOUNT_DEBIT_CREDIT_COLUMN].str.strip()

        debit_condition = (df[ACCOUNT_DEBIT_CREDIT_COLUMN] == 'Χρέωση') & (ynab_df['Amount'] > 0)
        ynab_df.loc[debit_condition, 'Amount'] *= -1

        ynab_df['Amount'] = ynab_df['Amount'].round(2)

        return ynab_df
    except Exception as e:
        raise ValueError(f"Error processing account operations: {str(e)}")

def process_card_operations(df: pd.DataFrame) -> pd.DataFrame:
    """Process the Card Operations Export and convert it to YNAB format.
    
    Args:
        df: Input DataFrame with card operations
        
    Returns:
        pd.DataFrame: Processed DataFrame in YNAB format
    """
    validate_dataframe(df, CARD_REQUIRED_COLUMNS)
    
    try:
        ynab_df = pd.DataFrame()
        ynab_df['Date'] = pd.to_datetime(
            df[CARD_DATE_COLUMN].apply(lambda x: datetime.strptime(x.split()[0], DATE_FORMAT_CARD)),
            errors='coerce'
        ).dt.strftime(DATE_FORMAT_YNAB)
        
        if ynab_df['Date'].isna().any():
            raise ValueError(f"Invalid date format found in {CARD_DATE_COLUMN}")

        ynab_df['Payee'] = df[CARD_PAYEE_COLUMN]
        ynab_df['Memo'] = df[CARD_PAYEE_COLUMN].str.replace(MEMO_CLEANUP_PATTERN, '', regex=True)
        ynab_df['Amount'] = df[CARD_AMOUNT_COLUMN].apply(convert_amount)
        ynab_df['Amount'] = ynab_df['Amount'].round(2)

        return ynab_df
    except Exception as e:
        raise ValueError(f"Error processing card operations: {str(e)}")

def convert_nbg_to_ynab(xlsx_file: str) -> None:
    """Convert NBG Excel file to YNAB CSV format.
    
    Args:
        xlsx_file: Path to the input XLSX file
    """
    try:
        df = pd.read_excel(xlsx_file)

        if set(ACCOUNT_REQUIRED_COLUMNS).issubset(df.columns):
            ynab_df = process_account_operations(df)
        elif set(CARD_REQUIRED_COLUMNS).issubset(df.columns):
            ynab_df = process_card_operations(df)
        else:
            raise ValueError("File format does not match Account or Card operations format")

        csv_file = f"{os.path.splitext(xlsx_file)[0]}_ynab.csv"
        ynab_df.to_csv(csv_file, index=False, quoting=csv.QUOTE_MINIMAL)
        logging.info(f"Conversion complete. The CSV file is saved as: {csv_file}")

    except FileNotFoundError:
        logging.error(f"File not found: '{xlsx_file}'")
    except pd.errors.EmptyDataError:
        logging.error(f"Empty or unreadable file: '{xlsx_file}'")
    except ValueError as e:
        logging.error(f"Validation error: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logging.error("Usage: python main.py <path_to_xlsx_file>")
        logging.error("Example: python main.py /Users/user/Documents/file.xlsx")
        sys.exit(1)
    
    xlsx_file_path = sys.argv[1]
    if not xlsx_file_path.endswith(('.xlsx', '.xls')):
        logging.error(f"Invalid file type: '{xlsx_file_path}'")
        sys.exit(1)
    
    convert_nbg_to_ynab(xlsx_file_path)