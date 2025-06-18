import pandas as pd
import os
import sys
import csv
import re  # Add this import
import logging
from datetime import datetime
from typing import Union, List

# Configuration
LOGGING_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOGGING_LEVEL = logging.INFO

# File formats
SUPPORTED_EXTENSIONS = ('.xlsx', '.xls', '.csv')
OUTPUT_FORMAT = 'csv'

# Set up logging
logging.basicConfig(
    level=LOGGING_LEVEL,
    format=LOGGING_FORMAT
)

# Date format constants
DATE_FORMAT_ACCOUNT = '%d/%m/%Y'
DATE_FORMAT_CARD = '%d/%m/%Y'
DATE_FORMAT_YNAB = '%Y-%m-%d'

# Column name constants for account statements
ACCOUNT_DATE_COLUMN = 'Valeur'
ACCOUNT_PAYEE_COLUMN = 'Ονοματεπώνυμο αντισυμβαλλόμενου'
ACCOUNT_MEMO_COLUMN = 'Περιγραφή'
ACCOUNT_AMOUNT_COLUMN = 'Ποσό συναλλαγής'
ACCOUNT_DEBIT_CREDIT_COLUMN = 'Χρέωση / Πίστωση'

# Column name constants for card statements
CARD_DATE_COLUMN = 'Ημερομηνία/Ώρα Συναλλαγής'
CARD_PAYEE_COLUMN = 'Περιγραφή Κίνησης'
CARD_AMOUNT_COLUMN = 'Ποσό'
CARD_DEBIT_CREDIT_COLUMN = 'Χ/Π'

# Column name constants for Revolut exports
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

def normalize_column_name(column: str) -> str:
    """Normalize column names by removing extra spaces and normalizing Unicode."""
    return ' '.join(column.strip().split())

def validate_dataframe(df: pd.DataFrame, required_columns: List[str]) -> None:
    """Validate DataFrame with normalized column names."""
    if df.empty and len(df.columns) == 0:
        raise ValueError("Empty DataFrame provided")
    
    # Normalize both actual and required column names
    actual_columns = {normalize_column_name(col) for col in df.columns}
    required_norm = {normalize_column_name(col) for col in required_columns}
    
    missing_columns = required_norm - actual_columns
    if missing_columns:
        raise ValueError(
            f"Missing required columns: {', '.join(missing_columns)}\n"
            f"Available columns: {', '.join(actual_columns)}"
        )
    
    if len(df) == 0:
        raise ValueError("DataFrame contains no data")

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

def validate_revolut_currency(df: pd.DataFrame) -> None:
    """Validate that all transactions are in EUR.
    
    Args:
        df: DataFrame with Revolut transactions
        
    Raises:
        ValueError: If non-EUR transactions are found
    """
    non_eur = df[df[REVOLUT_CURRENCY_COLUMN] != 'EUR']
    if not non_eur.empty:
        raise ValueError("Non-EUR transactions found. Only EUR is supported.")

def process_revolut_operations(df: pd.DataFrame) -> pd.DataFrame:
    """Process Revolut export and convert it to YNAB format."""
    validate_dataframe(df, REVOLUT_REQUIRED_COLUMNS)
    validate_revolut_currency(df)
    
    try:
        df = df[df[REVOLUT_STATE_COLUMN] == 'COMPLETED']
        ynab_df = pd.DataFrame()
        
        ynab_df['Date'] = pd.to_datetime(df[REVOLUT_DATE_COLUMN]).dt.strftime(DATE_FORMAT_YNAB)
        
        if ynab_df['Date'].isna().any():
            raise ValueError(f"Invalid date format found in {REVOLUT_DATE_COLUMN}")
        
        ynab_df['Payee'] = df[REVOLUT_PAYEE_COLUMN]
        ynab_df['Memo'] = df[REVOLUT_TYPE_COLUMN]
        
        # Always treat fees as positive values that reduce the final amount
        amounts = df[REVOLUT_AMOUNT_COLUMN].apply(convert_amount)
        fees = df[REVOLUT_FEE_COLUMN].apply(convert_amount).abs()  # Ensure fees are positive
        
        # Fees always reduce the amount (make expenses more negative, income less positive)
        ynab_df['Amount'] = (amounts - fees).round(2)
        
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
    """Remove duplicate and older transactions."""
    if prev_df.empty:
        return new_df
        
    new_df = new_df.copy()
    new_df['Date'] = pd.to_datetime(new_df['Date'])
    prev_df['Date'] = pd.to_datetime(prev_df['Date'])
    
    latest_prev_date = prev_df['Date'].max()
    
    # Allow same-day transactions if they're not duplicates
    mask_newer = new_df['Date'] >= latest_prev_date
    
    # Create unique transaction identifier
    def create_key(df: pd.DataFrame) -> pd.Series:
        return (df['Date'].dt.strftime('%Y-%m-%d') + '_' + 
                df['Payee'] + '_' + 
                df['Amount'].astype(str))
    
    new_keys = create_key(new_df)
    prev_keys = create_key(prev_df)
    mask_unique = ~new_keys.isin(prev_keys)
    
    filtered_df = new_df[mask_newer & mask_unique].copy()
    filtered_df['Date'] = filtered_df['Date'].dt.strftime(DATE_FORMAT_YNAB)
    
    excluded_count = len(new_df) - len(filtered_df)
    if excluded_count > 0:
        logging.info(f"Excluded {excluded_count} duplicate or older transactions")
    
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
    
    # Remove any existing date from base_name (supports DD-MM-YYYY and YYYY-MM-DD)
    base_name = re.sub(r'_?(\d{2}-\d{2}-\d{4}|\d{4}-\d{2}-\d{2})', '', base_name)
    
    return os.path.join(
        os.path.dirname(input_file),
        f"{base_name}_{date_str}_ynab.{OUTPUT_FORMAT}"
    )

def validate_input_file(file_path: str) -> None:
    """Validate input file existence and format.
    
    Args:
        file_path: Path to input file
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is not supported
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: '{file_path}'")
    
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: '{ext}' (must be {', '.join(SUPPORTED_EXTENSIONS)})")

def convert_nbg_to_ynab(xlsx_file: str, previous_ynab: str = None) -> None:
    """Convert bank export file to YNAB CSV format.
    
    Args:
        xlsx_file: Path to the input file
        previous_ynab: Optional path to previous YNAB export
        
    Returns:
        None
    
    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If file format is not recognized
        pd.errors.EmptyDataError: If file is empty
    """
    try:
        validate_input_file(xlsx_file)
        
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
    if file_ext not in SUPPORTED_EXTENSIONS:
        logging.error(f"Unsupported file type: '{file_ext}' (must be .xlsx, .xls, or .csv)")
        sys.exit(1)
        
    convert_nbg_to_ynab(input_file_path, previous_ynab_path)

__all__ = [
    'convert_amount',
    'extract_date_from_filename',
    'generate_output_filename',
    'exclude_existing_transactions',
    'process_card_operations',
    'process_account_operations',
    'process_revolut_operations',  # Add this
    'validate_dataframe'
]