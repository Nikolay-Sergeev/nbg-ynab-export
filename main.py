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
DATE_FORMAT_ACCOUNT = '%d/%m/%Y'  # Changed from '%d.%m.%Y' to match your file's format  # Changed from '%d.%m.%Y' to match your file's format
DATE_FORMAT_CARD = '%d/%m/%Y'
DATE_FORMAT_YNAB = '%Y-%m-%d'

# Column name constants
ACCOUNT_DATE_COLUMN = 'Valeur'  # Changed from 'Ημερομηνία' to use Valeur as date source
ACCOUNT_PAYEE_COLUMN = 'Ονοματεπώνυμο αντισυμβαλλόμενου'  # Changed from 'Δικαιούχος'μο αντισυμβαλλόμενου'  # Changed from 'Δικαιούχος'
ACCOUNT_MEMO_COLUMN = 'Περιγραφή'  # Changed from 'Περιγραφή Συναλλαγής' from 'Περιγραφή Συναλλαγής'
ACCOUNT_AMOUNT_COLUMN = 'Ποσό συναλλαγής'  # Changed from 'Ποσό'συναλλαγής'  # Changed from 'Ποσό'
ACCOUNT_DEBIT_CREDIT_COLUMN = 'Χρέωση / Πίστωση'  # Added space around "/"η'  # Added space around "/"

# Column name constants for card statements
CARD_DATE_COLUMN = 'Ημερομηνία/Ώρα Συναλλαγής'  # Changed from 'Transaction Date'
CARD_PAYEE_COLUMN = 'Περιγραφή Κίνησης'  # Changed from 'Description'
CARD_AMOUNT_COLUMN = 'Ποσό'  # Changed from 'Amount'
CARD_DEBIT_CREDIT_COLUMN = 'Χ/Π'  # Added for Greek card statements

# Required columns for validation
ACCOUNT_REQUIRED_COLUMNS = [
    'Valeur',  # Changed from 'Ημερομηνία'
    ACCOUNT_PAYEE_COLUMN,
    ACCOUNT_MEMO_COLUMN,
    ACCOUNT_AMOUNT_COLUMN,
    ACCOUNT_DEBIT_CREDIT_COLUMN
]

CARD_REQUIRED_COLUMNS = [
    CARD_DATE_COLUMN,
    CARD_PAYEE_COLUMN,
    CARD_AMOUNT_COLUMN
]

# Cleanup pattern for transaction descriptions
MEMO_CLEANUP_PATTERN = r'\s*\([^)]*\)'  # Removes text in parentheses with whitespace
 # Add new cleanup patterns after the existing MEMO_CLEANUP_PATTERN
ECOMMERCE_CLEANUP_PATTERN = r'E-COMMERCE ΑΓΟΡΑ - '
# Add new cleanup patterns after ECOMMERCE_CLEANUP_PATTERN
SECURE_ECOMMERCE_CLEANUP_PATTERN = r'3D SECURE E-COMMERCE ΑΓΟΡΑ - '

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
    """Process the Account Operations Export and convert it to YNAB format."""
    validate_dataframe(df, ACCOUNT_REQUIRED_COLUMNS)
    
    try:
        ynab_df = pd.DataFrame()
        # Convert Valeur date to YNAB format
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
    """Process the Card Operations Export and convert it to YNAB format."""
    validate_dataframe(df, CARD_REQUIRED_COLUMNS)
    
    try:
        ynab_df = pd.DataFrame()
        
        # Extract date from datetime string (removes time portion)
        ynab_df['Date'] = pd.to_datetime(
            df[CARD_DATE_COLUMN].apply(lambda x: x.split()[0]),
            format=DATE_FORMAT_CARD
        ).dt.strftime(DATE_FORMAT_YNAB)
        
        if ynab_df['Date'].isna().any():
            raise ValueError(f"Invalid date format found in {CARD_DATE_COLUMN}")

        # Clean up payee name by removing prefixes and parentheses
        ynab_df['Payee'] = (df[CARD_PAYEE_COLUMN]
            .str.replace(SECURE_ECOMMERCE_CLEANUP_PATTERN, '', regex=True)  # Remove 3D Secure prefix first
            .str.replace(ECOMMERCE_CLEANUP_PATTERN, '', regex=True)         # Then remove regular e-commerce prefix
            .str.replace(MEMO_CLEANUP_PATTERN, '', regex=True)              # Finally remove parentheses
        )
        ynab_df['Memo'] = df[CARD_PAYEE_COLUMN]  # Keep original description in memo
        ynab_df['Amount'] = df[CARD_AMOUNT_COLUMN].apply(convert_amount)
        
        # Handle debit/credit indicator
        df[CARD_DEBIT_CREDIT_COLUMN] = df[CARD_DEBIT_CREDIT_COLUMN].str.strip()
        debit_condition = (df[CARD_DEBIT_CREDIT_COLUMN] == 'Χ') & (ynab_df['Amount'] > 0)
        ynab_df.loc[debit_condition, 'Amount'] *= -1

        ynab_df['Amount'] = ynab_df['Amount'].round(2)

        return ynab_df
    except Exception as e:
        raise ValueError(f"Error processing card operations: {str(e)}")

def load_previous_transactions(csv_file: str) -> pd.DataFrame:
    """Load previously exported transactions from YNAB CSV file.
    
    Args:
        csv_file: Path to previous YNAB export CSV
        
    Returns:
        pd.DataFrame: DataFrame with previous transactions
    """
    try:
        return pd.read_csv(csv_file)
    except Exception as e:
        logging.warning(f"Could not load previous transactions: {str(e)}")
        return pd.DataFrame(columns=['Date', 'Payee', 'Memo', 'Amount'])

def exclude_existing_transactions(new_df: pd.DataFrame, prev_df: pd.DataFrame) -> pd.DataFrame:
    """Remove transactions that already exist in previous export.
    
    Args:
        new_df: DataFrame with new transactions
        prev_df: DataFrame with previous transactions
        
    Returns:
        pd.DataFrame: DataFrame with only new transactions
    """
    if prev_df.empty:
        return new_df
        
    # Create a composite key for comparison
    def get_key(df):
        return df['Date'] + '|' + df['Payee'] + '|' + df['Amount'].astype(str)
    
    new_keys = get_key(new_df)
    prev_keys = get_key(prev_df)
    
    # Keep only transactions that don't exist in previous export
    mask = ~new_keys.isin(prev_keys)
    filtered_df = new_df[mask].copy()
    
    excluded_count = len(new_df) - len(filtered_df)
    if excluded_count > 0:
        logging.info(f"Excluded {excluded_count} previously imported transactions")
    
    return filtered_df

def convert_nbg_to_ynab(xlsx_file: str, previous_ynab: str = None) -> None:
    """Convert NBG Excel file to YNAB CSV format.
    
    Args:
        xlsx_file: Path to the input XLSX file
        previous_ynab: Optional path to previous YNAB export CSV
    """
    try:
        df = pd.read_excel(xlsx_file)
                
        # Add debug logging
        logging.debug(f"Found columns in file: {list(df.columns)}")
        logging.debug(f"Required account columns: {ACCOUNT_REQUIRED_COLUMNS}")
        logging.debug(f"Required card columns: {CARD_REQUIRED_COLUMNS}")

        if set(ACCOUNT_REQUIRED_COLUMNS).issubset(df.columns):
            logging.info("Processing as account statement")
            ynab_df = process_account_operations(df)
        elif set(CARD_REQUIRED_COLUMNS).issubset(df.columns):
            logging.info("Processing as card statement")
            ynab_df = process_card_operations(df)
        else:
            raise ValueError("File format does not match Account or Card operations format")

        # After creating ynab_df but before saving:
        if previous_ynab:
            prev_df = load_previous_transactions(previous_ynab)
            ynab_df = exclude_existing_transactions(ynab_df, prev_df)
            
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
        logging.error("Usage: python main.py <path_to_xlsx_file> [path_to_previous_ynab.csv]")
        sys.exit(1)
        
    xlsx_file_path = sys.argv[1]
    previous_ynab_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not xlsx_file_path.endswith(('.xlsx', '.xls')):
        logging.error(f"Invalid file type: '{xlsx_file_path}'")
        sys.exit(1)
        
    convert_nbg_to_ynab(xlsx_file_path, previous_ynab_path)