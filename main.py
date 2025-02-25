import pandas as pd
import os
import sys
import csv
import re  # Add this import
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

# Add after existing column name constants
REVOLUT_DATE_COLUMN = 'Started Date'
REVOLUT_PAYEE_COLUMN = 'Description'
REVOLUT_TYPE_COLUMN = 'Type'
REVOLUT_AMOUNT_COLUMN = 'Amount'
REVOLUT_FEE_COLUMN = 'Fee'
REVOLUT_STATE_COLUMN = 'State'
REVOLUT_CURRENCY_COLUMN = 'Currency'

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

# Add to required columns section
REVOLUT_REQUIRED_COLUMNS = [
    REVOLUT_DATE_COLUMN,
    REVOLUT_PAYEE_COLUMN,
    REVOLUT_TYPE_COLUMN,
    REVOLUT_AMOUNT_COLUMN,
    REVOLUT_FEE_COLUMN,
    REVOLUT_STATE_COLUMN
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
    if (missing_columns):
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

def process_revolut_operations(df: pd.DataFrame) -> pd.DataFrame:
    """Process the Revolut Export and convert it to YNAB format."""
    validate_dataframe(df, REVOLUT_REQUIRED_COLUMNS)
    
    try:
        # Filter out non-completed transactions
        df = df[df[REVOLUT_STATE_COLUMN] == 'COMPLETED']
        
        ynab_df = pd.DataFrame()
        
        # Convert date to YNAB format
        ynab_df['Date'] = pd.to_datetime(
            df[REVOLUT_DATE_COLUMN]
        ).dt.strftime(DATE_FORMAT_YNAB)
        
        if ynab_df['Date'].isna().any():
            raise ValueError(f"Invalid date format found in {REVOLUT_DATE_COLUMN}")
        
        # Set payee and memo
        ynab_df['Payee'] = df[REVOLUT_PAYEE_COLUMN]
        ynab_df['Memo'] = df[REVOLUT_TYPE_COLUMN]
        
        # Calculate total amount including fees
        amounts = df[REVOLUT_AMOUNT_COLUMN].apply(convert_amount)
        fees = df[REVOLUT_FEE_COLUMN].apply(convert_amount)
        
        # If amount is negative, add negative fee, otherwise add positive fee
        ynab_df['Amount'] = amounts.where(
            amounts >= 0,
            amounts - fees  # For negative amounts, subtract fee to make it more negative
        ).where(
            amounts < 0,
            amounts + fees  # For positive amounts, add fee normally
        ).round(2)
        
        return ynab_df
        
    except Exception as e:
        raise ValueError(f"Error processing Revolut operations: {str(e)}")

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
    """Remove transactions that are older or equal to the latest transaction in previous export.
    
    Args:
        new_df: DataFrame with new transactions
        prev_df: DataFrame with previous transactions
        
    Returns:
        pd.DataFrame: DataFrame with only new transactions
    """
    if prev_df.empty:
        return new_df
        
    # Convert dates to datetime for comparison
    new_df['Date'] = pd.to_datetime(new_df['Date'])
    prev_df['Date'] = pd.to_datetime(prev_df['Date'])
    
    # Find the latest date in previous transactions
    latest_prev_date = prev_df['Date'].max()
    
    # Keep only transactions newer than the latest previous transaction
    mask_newer = new_df['Date'] > latest_prev_date
    filtered_df = new_df[mask_newer].copy()
    
    # Convert dates back to string format
    filtered_df['Date'] = filtered_df['Date'].dt.strftime(DATE_FORMAT_YNAB)
    
    excluded_count = len(new_df) - len(filtered_df)
    if excluded_count > 0:
        logging.info(f"Excluded {excluded_count} transactions (older than or equal to {latest_prev_date.strftime(DATE_FORMAT_YNAB)})")
    
    return filtered_df

def extract_date_from_filename(filename: str) -> str:
    """Extract date from filename if present.
    
    Args:
        filename: Name of the file to check
        
    Returns:
        str: Date in YYYY-MM-DD format if found, empty string otherwise
    """
    import re
    # Match patterns like "25-02-2025" or "2025-02-25"
    patterns = [
        r'(\d{2})-(\d{2})-(\d{4})',  # DD-MM-YYYY
        r'(\d{4})-(\d{2})-(\d{2})'   # YYYY-MM-DD
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            groups = match.groups()
            if len(groups[0]) == 4:  # YYYY-MM-DD format
                return f"{groups[0]}-{groups[1]}-{groups[2]}"
            else:  # DD-MM-YYYY format
                return f"{groups[2]}-{groups[1]}-{groups[0]}"
    return ""

def generate_output_filename(input_file: str, is_revolut: bool = False) -> str:
    """Generate output filename with appropriate date.
    
    Args:
        input_file: Path to the input file
        is_revolut: Whether the file is a Revolut export
        
    Returns:
        str: Path to the output CSV file
    """
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    
    # For Revolut exports, always use current date
    if is_revolut:
        date_str = datetime.now().strftime('%Y-%m-%d')
    else:
        # Try to extract date from filename
        date_str = extract_date_from_filename(base_name)
        if not date_str:
            # If no date in filename, use current date
            date_str = datetime.now().strftime('%Y-%m-%d')
    
    # Remove any existing date from base_name
    base_name = re.sub(r'_?\d{2}-\d{2}-\d{4}', '', base_name)
    
    return os.path.join(
        os.path.dirname(input_file),
        f"{base_name}_{date_str}_ynab.csv"
    )

def convert_nbg_to_ynab(xlsx_file: str, previous_ynab: str = None) -> None:
    """Convert bank export file to YNAB CSV format."""
    try:
        # Try reading as Excel first
        try:
            df = pd.read_excel(xlsx_file)
        except:
            # If Excel read fails, try CSV
            df = pd.read_csv(xlsx_file)
        
        # Add debug logging
        logging.debug(f"Found columns in file: {list(df.columns)}")
        
        # Determine file type and process accordingly
        is_revolut = False
        if set(REVOLUT_REQUIRED_COLUMNS).issubset(df.columns):
            logging.info("Processing as Revolut statement")
            ynab_df = process_revolut_operations(df)
            is_revolut = True
        elif set(ACCOUNT_REQUIRED_COLUMNS).issubset(df.columns):
            logging.info("Processing as NBG account statement")
            ynab_df = process_account_operations(df)
        elif set(CARD_REQUIRED_COLUMNS).issubset(df.columns):
            logging.info("Processing as NBG card statement")
            ynab_df = process_card_operations(df)
        else:
            raise ValueError("File format not recognized")
            
        # After creating ynab_df but before saving:
        if previous_ynab:
            prev_df = load_previous_transactions(previous_ynab)
            ynab_df = exclude_existing_transactions(ynab_df, prev_df)
            
        # Generate output filename with file type info
        csv_file = generate_output_filename(xlsx_file, is_revolut)
        
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
        logging.error("Usage: python main.py <path_to_statement_file> [path_to_previous_ynab.csv]")
        logging.error("Supported formats:")
        logging.error("  - NBG statements: .xlsx, .xls")
        logging.error("  - Revolut exports: .csv")
        sys.exit(1)
    
    input_file_path = sys.argv[1]
    previous_ynab_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Check if file exists
    if not os.path.exists(input_file_path):
        logging.error(f"File not found: '{input_file_path}'")
        sys.exit(1)
    
    # Check file extension
    file_ext = os.path.splitext(input_file_path)[1].lower()
    if file_ext not in ('.xlsx', '.xls', '.csv'):
        logging.error(f"Unsupported file type: '{file_ext}' (must be .xlsx, .xls, or .csv)")
        sys.exit(1)
        
    convert_nbg_to_ynab(input_file_path, previous_ynab_path)