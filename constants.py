"""Common constant definitions for converters and CLI."""

# Date formats
DATE_FMT_ACCOUNT = "%d/%m/%Y"
DATE_FMT_CARD = "%d/%m/%Y"
DATE_FMT_YNAB = "%Y-%m-%d"

# Column names for NBG account statements
ACCOUNT_DATE_COLUMN = "Valeur"
ACCOUNT_PAYEE_COLUMN = "Ονοματεπώνυμο αντισυμβαλλόμενου"
ACCOUNT_MEMO_COLUMN = "Περιγραφή"
ACCOUNT_AMOUNT_COLUMN = "Ποσό συναλλαγής"
ACCOUNT_DEBIT_CREDIT_COLUMN = "Χρέωση / Πίστωση"

# Column names for NBG card statements
CARD_DATE_COLUMN = "Ημερομηνία/Ώρα Συναλλαγής"
CARD_PAYEE_COLUMN = "Περιγραφή Κίνησης"
CARD_AMOUNT_COLUMN = "Ποσό"
CARD_DEBIT_CREDIT_COLUMN = "Χ/Π"

# Column names for Revolut exports
REVOLUT_DATE_COLUMN = "Started Date"
REVOLUT_PAYEE_COLUMN = "Description"
REVOLUT_TYPE_COLUMN = "Type"
REVOLUT_AMOUNT_COLUMN = "Amount"
REVOLUT_FEE_COLUMN = "Fee"
REVOLUT_STATE_COLUMN = "State"
REVOLUT_CURRENCY_COLUMN = "Currency"

# Required columns per file type
ACCOUNT_REQUIRED_COLUMNS = [
    ACCOUNT_DATE_COLUMN,
    ACCOUNT_PAYEE_COLUMN,
    ACCOUNT_MEMO_COLUMN,
    ACCOUNT_AMOUNT_COLUMN,
    ACCOUNT_DEBIT_CREDIT_COLUMN,
]

CARD_REQUIRED_COLUMNS = [
    CARD_DATE_COLUMN,
    CARD_PAYEE_COLUMN,
    CARD_AMOUNT_COLUMN,
]

REVOLUT_REQUIRED_COLUMNS = [
    REVOLUT_DATE_COLUMN,
    REVOLUT_PAYEE_COLUMN,
    REVOLUT_TYPE_COLUMN,
    REVOLUT_AMOUNT_COLUMN,
    REVOLUT_FEE_COLUMN,
    REVOLUT_STATE_COLUMN,
]

# Cleanup patterns
MEMO_CLEANUP_PATTERN = r"\s*\([^)]*\)"
ECOMMERCE_CLEANUP_PATTERN = r"E-COMMERCE ΑΓΟΡΑ - "
SECURE_ECOMMERCE_CLEANUP_PATTERN = r"3D SECURE E-COMMERCE ΑΓΟΡΑ - "

