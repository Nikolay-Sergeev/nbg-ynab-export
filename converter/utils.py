# converter/utils.py
from pathlib import Path
from datetime import datetime
import pandas as pd
import csv
import re
from typing import Optional, Union
import unicodedata
from constants import (
    DATE_FMT_YNAB,
    ECOMMERCE_CLEANUP_PATTERN,
    PURCHASE_CLEANUP_PATTERN,
    SECURE_ECOMMERCE_CLEANUP_PATTERN,
)
from config import get_logger

logger = get_logger(__name__)

FORMULA_PREFIXES = ('=', '+', '-', '@')


def escape_csv_formula(value: object) -> object:
    """Prevent spreadsheet formula injection by prefixing risky strings."""
    if isinstance(value, str):
        stripped = value.lstrip()
        if stripped.startswith(FORMULA_PREFIXES):
            return "'" + value
    return value


def sanitize_csv_formulas(df: pd.DataFrame, columns: Optional[list] = None) -> pd.DataFrame:
    """Return a copy of df with formula-like strings escaped for CSV output."""
    safe_df = df.copy()
    target_columns = columns or [
        col for col in safe_df.columns
        if safe_df[col].dtype == object
    ]
    for col in target_columns:
        if col in safe_df.columns:
            safe_df[col] = safe_df[col].apply(escape_csv_formula)
    return safe_df


def read_input(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == '.csv':
        return pd.read_csv(path)
    return pd.read_excel(path)


def write_output(
    in_path: Path,
    df: pd.DataFrame,
    date_fmt: str = DATE_FMT_YNAB
) -> Path:
    date_str = datetime.now().strftime(date_fmt)
    stem = in_path.stem
    out_name = f"{stem}_{date_str}_ynab.csv"
    out_path = in_path.with_name(out_name)
    safe_columns = [col for col in ('Payee', 'Memo', 'payee', 'memo', 'notes') if col in df.columns]
    safe_df = sanitize_csv_formulas(df, columns=safe_columns or None)
    safe_df.to_csv(out_path, index=False, quoting=csv.QUOTE_MINIMAL)
    return out_path


def exclude_existing(
    new_df: pd.DataFrame,
    prev_df: pd.DataFrame
) -> pd.DataFrame:
    """Remove duplicate and older transactions.

    Behavior matches legacy main.py exclusion:
    - If a previous export is provided, drop any new transactions older than
      the latest date in the previous export.
    - Then drop exact duplicates based on Date, Payee, Amount, and Memo
      (case-insensitive for Payee/Memo).
    """
    logger.info("Excluding existing transactions")

    if prev_df is None or prev_df.empty:
        return new_df

    new_copy = new_df.copy()
    prev_copy = prev_df.copy()

    new_copy['Date'] = pd.to_datetime(new_copy['Date'], errors='coerce')
    prev_copy['Date'] = pd.to_datetime(prev_copy['Date'], errors='coerce')

    latest_prev_date = prev_copy['Date'].max()
    if pd.isna(latest_prev_date):
        mask_newer = pd.Series([True] * len(new_copy), index=new_copy.index)
    else:
        mask_newer = new_copy['Date'] >= latest_prev_date

    def make_key(df: pd.DataFrame) -> pd.Series:
        date_part = df['Date'].dt.strftime(DATE_FMT_YNAB).fillna('')
        payee_part = df['Payee'].astype(str).str.lower().str.strip()
        amount_part = df['Amount'].astype(str)
        if 'Memo' in df.columns:
            memo_part = df['Memo'].astype(str).str.lower().str.strip()
        else:
            memo_part = pd.Series([''] * len(df), index=df.index)
        return date_part + '|' + payee_part + '|' + amount_part + '|' + memo_part

    new_keys = make_key(new_copy)
    prev_keys = set(make_key(prev_copy))
    mask_unique = ~new_keys.isin(prev_keys)

    filtered = new_copy[mask_newer & mask_unique].copy()
    filtered['Date'] = filtered['Date'].dt.strftime(DATE_FMT_YNAB)

    excluded_count = len(new_copy) - len(filtered)
    if excluded_count > 0:
        logger.info("Excluded %d duplicate or older transactions", excluded_count)

    # Preserve original column order
    return filtered[new_df.columns].copy()


def validate_dataframe(df: pd.DataFrame, required_columns: list) -> None:
    """
    Ensure df has required columns (exact match) and is not empty.
    """
    if df.empty and len(df.columns) == 0:
        raise ValueError("Empty DataFrame provided")
    actual = {col.strip() for col in df.columns}
    required = set(required_columns)
    missing = required - actual
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    if len(df) == 0:
        raise ValueError("DataFrame contains no data")


def convert_amount(amount: Union[str, float, int]) -> float:
    """
    Convert amount strings with either comma or dot as decimal separator
    and optional thousands separators to float.
    Examples of supported formats: "1234,56", "1.234,56", "1,234.56".
    """
    if isinstance(amount, str):
        s = amount.strip()
        # Remove common thousands separators
        s = s.replace("'", "").replace("\u00a0", "").replace(" ", "")
        if "," in s and "." in s:
            # The rightmost of comma or dot is the decimal separator
            if s.rfind(',') > s.rfind('.'):
                s = s.replace('.', '')
                s = s.replace(',', '.')
            else:
                s = s.replace(',', '')
        elif "," in s:
            # Only comma present -> treat as decimal separator
            s = s.replace('.', '')
            s = s.replace(',', '.')
        return float(s)
    return float(amount)


def strip_accents(value: Union[str, pd.Series]) -> Union[str, pd.Series]:
    """
    Remove diacritical marks from Greek/Latin strings. Accepts a string or a pandas Series.
    Useful for normalizing values like 'Χρέωση' -> 'Χρεωση' before uppercasing.
    """
    def _strip(s: str) -> str:
        if s is None:
            return ''
        # Normalize to NFD and remove all combining marks (Mn)
        nf = unicodedata.normalize('NFD', str(s))
        return ''.join(ch for ch in nf if unicodedata.category(ch) != 'Mn')

    if isinstance(value, pd.Series):
        return value.astype(str).map(_strip)
    return _strip(value)


def strip_transaction_prefixes(values: pd.Series) -> pd.Series:
    """Remove standard NBG prefixes from transaction text fields."""
    cleaned = values.fillna('').astype(str)
    for pattern in (
        SECURE_ECOMMERCE_CLEANUP_PATTERN,
        ECOMMERCE_CLEANUP_PATTERN,
        PURCHASE_CLEANUP_PATTERN,
    ):
        cleaned = cleaned.str.replace(pattern, '', regex=True)
    return cleaned


def normalize_column_name(column: str) -> str:
    """
    Normalize a column name by stripping whitespace and collapsing multiple spaces.
    """
    return ' '.join(column.strip().split())


def extract_date_from_filename(filename: str) -> str:
    """
    Extract first occurrence of date pattern YYYY-MM-DD or DD-MM-YYYY from filename.
    """
    # Try YYYY-MM-DD
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", filename)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    # Try DD-MM-YYYY
    match = re.search(r"(\d{2})-(\d{2})-(\d{4})", filename)
    if match:
        return f"{match.group(3)}-{match.group(2)}-{match.group(1)}"
    return ''


def generate_output_filename(
    input_file: str,
    *,
    output_dir: Optional[Union[str, Path]] = None,
    force_today: bool = False,
) -> str:
    """
    Generate YNAB CSV output filename based on input file path, stripping existing date.
    """
    path = Path(input_file)
    base = path.stem
    # Remove existing trailing date patterns
    base = re.sub(r'(_)?(\d{4}-\d{2}-\d{2}|\d{2}-\d{2}-\d{4})$', '', base)
    date_str = ''
    if not force_today:
        date_str = extract_date_from_filename(path.stem)
    if not date_str:
        date_str = datetime.now().strftime(DATE_FMT_YNAB)
    filename = f"{base}_{date_str}_ynab.csv"
    directory = Path(output_dir) if output_dir else path.parent
    return str(directory / filename)
