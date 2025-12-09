# converter/utils.py
from pathlib import Path
from datetime import datetime
import pandas as pd
import csv
import re
from typing import Union
import unicodedata
from constants import DATE_FMT_YNAB
from config import get_logger

logger = get_logger(__name__)


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
    df.to_csv(out_path, index=False, quoting=csv.QUOTE_MINIMAL)
    return out_path


def exclude_existing(
    new_df: pd.DataFrame,
    prev_df: pd.DataFrame
) -> pd.DataFrame:
    logger.info("Excluding existing transactions")

    def make_key(df):
        # Date, payee, amount, memo (empty if missing)
        date = df['Date'].astype(str)
        payee = df['Payee'].astype(str).str.lower().str.strip()
        amount = df['Amount'].astype(str)
        if 'Memo' in df.columns:
            memo = df['Memo'].astype(str).str.lower().str.strip()
        else:
            memo = pd.Series([''] * len(df), index=df.index)
        return date + '|' + payee + '|' + amount + '|' + memo
    new_keys = make_key(new_df)
    prev_keys = set(make_key(prev_df))
    mask = ~new_keys.isin(prev_keys)
    return new_df[mask].copy()


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


def generate_output_filename(input_file: str) -> str:
    """
    Generate YNAB CSV output filename based on input file path, stripping existing date.
    """
    path = Path(input_file)
    base = path.stem
    # Remove existing trailing date patterns
    base = re.sub(r'(_)?(\d{4}-\d{2}-\d{2}|\d{2}-\d{2}-\d{4})$', '', base)
    date_str = extract_date_from_filename(path.stem)
    if not date_str:
        date_str = datetime.now().strftime(DATE_FMT_YNAB)
    filename = f"{base}_{date_str}_ynab.csv"
    return str(path.with_name(filename))
