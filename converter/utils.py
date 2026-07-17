# converter/utils.py
from pathlib import Path
from datetime import datetime
from hashlib import sha256
from numbers import Number
import os
import tempfile
import zipfile
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
NBG_GENERATED_IMPORT_ID_PREFIX = 'NBG:v1:'
MAX_XLSX_ENTRIES = 10_000
MAX_XLSX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024


def _canonical_import_id_value(value: object) -> str:
    """Normalize a raw bank field before hashing it into a stable import ID."""
    if value is None:
        return ''
    try:
        if pd.isna(value):
            return ''
    except (TypeError, ValueError):
        pass
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, Number) and not isinstance(value, bool):
        return format(value, '.15g')
    text = unicodedata.normalize('NFKC', str(value)).strip()
    return ' '.join(text.split())


def build_nbg_import_ids(
    df: pd.DataFrame,
    fingerprint_columns: list,
    *,
    reference_column: str = 'Αριθμός αναφοράς',
) -> pd.Series:
    """Return stable transaction fingerprints for NBG rows.

    NBG leaves references blank for some transactions and reuses one reference for
    multi-row operations. The reference therefore participates in the fingerprint
    when present but is not used as the ID by itself. Export row numbers are excluded
    because they change between overlapping statement downloads.
    """
    available_columns = [column for column in fingerprint_columns if column in df.columns]
    if not available_columns:
        raise ValueError("No stable columns available for transaction import IDs")

    generated_counts = {}
    import_ids = []
    collision_count = 0

    for _, row in df.iterrows():
        fingerprint_values = [
            f"{column}={_canonical_import_id_value(row[column])}"
            for column in available_columns
        ]
        if reference_column in df.columns:
            fingerprint_values.insert(
                0,
                f"{reference_column}={_canonical_import_id_value(row[reference_column])}",
            )
        payload = '\x1f'.join(fingerprint_values)
        base_id = NBG_GENERATED_IMPORT_ID_PREFIX + sha256(
            payload.encode('utf-8')
        ).hexdigest()[:24]
        occurrence = generated_counts.get(base_id, 0) + 1
        generated_counts[base_id] = occurrence
        if occurrence > 1:
            collision_count += 1
            import_ids.append(f"{base_id}:{occurrence}")
        else:
            import_ids.append(base_id)

    if collision_count:
        logger.warning(
            "Disambiguated %d identical NBG transaction fingerprints",
            collision_count,
        )
    return pd.Series(import_ids, index=df.index, dtype='object')


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


def validate_xlsx_archive(path: Path) -> None:
    """Reject malformed or excessively expanded XLSX archives before XML parsing."""
    if path.suffix.lower() != '.xlsx' or not path.exists() or path.stat().st_size == 0:
        return
    try:
        with zipfile.ZipFile(path) as workbook:
            entries = workbook.infolist()
            if len(entries) > MAX_XLSX_ENTRIES:
                raise ValueError("Excel workbook contains too many archive entries")
            expanded_size = sum(entry.file_size for entry in entries)
            if expanded_size > MAX_XLSX_UNCOMPRESSED_BYTES:
                raise ValueError("Excel workbook expands beyond the safe size limit")
    except zipfile.BadZipFile as exc:
        raise ValueError("Invalid Excel workbook archive") from exc


def read_input(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == '.csv':
        return pd.read_csv(path)
    validate_xlsx_archive(path)
    return pd.read_excel(path)


def write_csv_securely(df: pd.DataFrame, out_path: Union[str, Path]) -> Path:
    """Atomically write a private CSV without following a pre-existing symlink."""
    path = Path(out_path)
    if path.is_symlink():
        raise OSError(f"Refusing to overwrite symlinked output file: {path}")
    if not path.parent.is_dir():
        raise FileNotFoundError(f"Output directory does not exist: {path.parent}")

    fd, temp_name = tempfile.mkstemp(prefix=f'.{path.name}.', dir=str(path.parent))
    try:
        if os.name == 'posix':
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as output_file:
            fd = -1
            df.to_csv(output_file, index=False, quoting=csv.QUOTE_MINIMAL)
            output_file.flush()
            os.fsync(output_file.fileno())
        os.replace(temp_name, path)
    except Exception:
        if fd >= 0:
            os.close(fd)
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise
    return path


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
    return write_csv_securely(safe_df, out_path)


def exclude_existing(
    new_df: pd.DataFrame,
    prev_df: pd.DataFrame,
    *,
    drop_older_than_latest_prev: bool = False,
) -> pd.DataFrame:
    """Remove duplicate and older transactions.

    Default behavior removes only exact duplicates based on Date, Payee, Amount,
    and Memo (case-insensitive for Payee/Memo).

    Optionally, legacy behavior can be enabled via
    ``drop_older_than_latest_prev=True`` to also drop any new transactions older
    than the latest date in the previous export.
    """
    logger.info("Excluding existing transactions")

    if prev_df is None or prev_df.empty:
        return new_df

    new_copy = new_df.copy()
    prev_copy = prev_df.copy()

    new_copy['Date'] = pd.to_datetime(new_copy['Date'], errors='coerce')
    prev_copy['Date'] = pd.to_datetime(prev_copy['Date'], errors='coerce')

    if drop_older_than_latest_prev:
        latest_prev_date = prev_copy['Date'].max()
        if pd.isna(latest_prev_date):
            mask_newer = pd.Series([True] * len(new_copy), index=new_copy.index)
        else:
            mask_newer = new_copy['Date'] >= latest_prev_date
    else:
        mask_newer = pd.Series([True] * len(new_copy), index=new_copy.index)

    def make_key(df: pd.DataFrame) -> pd.Series:
        date_part = df['Date'].dt.strftime(DATE_FMT_YNAB).fillna('')
        payee_part = df['Payee'].astype(str).str.lower().str.strip()
        amount_numeric = pd.to_numeric(df['Amount'], errors='coerce')
        amount_part = amount_numeric.map(
            lambda value: '' if pd.isna(value) else f"{value:.3f}"
        )
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
