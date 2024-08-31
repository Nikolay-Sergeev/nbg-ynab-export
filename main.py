import pandas as pd
import os
import sys
import csv
from datetime import datetime

# Constants for Account Operations Export
ACCOUNT_REQUIRED_COLUMNS = [
    'Valeur',  # Ημερομηνία αξίας
    'Περιγραφή',  # Description
    'Ονοματεπώνυμο αντισυμβαλλόμενου',  # Counterparty name
    'Ποσό συναλλαγής',  # Transaction amount
    'Χρέωση / Πίστωση'  # Debit / Credit
]
ACCOUNT_DATE_COLUMN = 'Valeur'  # Ημερομηνία αξίας
ACCOUNT_PAYEE_COLUMN = 'Περιγραφή'  # Description
ACCOUNT_MEMO_COLUMN = 'Ονοματεπώνυμο αντισυμβαλλόμενου'  # Counterparty name
ACCOUNT_AMOUNT_COLUMN = 'Ποσό συναλλαγής'  # Transaction amount
ACCOUNT_DEBIT_CREDIT_COLUMN = 'Χρέωση / Πίστωση'  # Debit / Credit

# Constants for Card Operations Export
CARD_REQUIRED_COLUMNS = [
    'Ημερομηνία/Ώρα Συναλλαγής',  # Date and time of transaction
    'Περιγραφή Κίνησης',  # Transaction description
    'Ποσό',  # Amount
]
CARD_DATE_COLUMN = 'Ημερομηνία/Ώρα Συναλλαγής'  # Date and time of transaction
CARD_PAYEE_COLUMN = 'Περιγραφή Κίνησης'  # Transaction description
CARD_AMOUNT_COLUMN = 'Ποσό'  # Amount


def convert_amount(amount):
    """
    Convert amount to float, handling both string and numeric inputs.
    """
    if isinstance(amount, str):
        return float(amount.replace(',', '.'))
    return float(amount)


def process_account_operations(df):
    """
    Process the Account Operations Export and convert it to YNAB format.
    """
    ynab_df = pd.DataFrame()
    ynab_df['Date'] = pd.to_datetime(df[ACCOUNT_DATE_COLUMN], format='%d.%m.%Y', errors='coerce').dt.strftime(
        '%Y-%m-%d')
    ynab_df['Payee'] = df[ACCOUNT_PAYEE_COLUMN]
    ynab_df['Memo'] = df[ACCOUNT_MEMO_COLUMN]

    # Convert amounts
    ynab_df['Amount'] = df[ACCOUNT_AMOUNT_COLUMN].apply(convert_amount)
    ynab_df.loc[df[ACCOUNT_DEBIT_CREDIT_COLUMN] == 'Χρέωση', 'Amount'] *= -1  # 'Χρέωση' means 'Debit'
    ynab_df['Amount'] = ynab_df['Amount'].round(2)

    return ynab_df


def process_card_operations(df):
    """
    Process the Card Operations Export and convert it to YNAB format.
    """
    ynab_df = pd.DataFrame()
    ynab_df['Date'] = pd.to_datetime(df[CARD_DATE_COLUMN].apply(lambda x: datetime.strptime(x.split()[0], '%d/%m/%Y')),
                                     errors='coerce').dt.strftime('%Y-%m-%d')
    ynab_df['Payee'] = df[CARD_PAYEE_COLUMN]
    ynab_df['Memo'] = df[CARD_PAYEE_COLUMN].str.replace(
        r'^E-COMMERCE ΑΓΟΡΑ - |^3D SECURE E-COMMERCE ΑΓΟΡΑ - |^3D SECURE E-COMMERCE ΑΓΟΡΑ \(ΕΞΟΥΣΙΟΔΟΤΗΣΗ\) - |^ΑΓΟΡΑ - ',
        '',
        regex=True
    )

    # Convert amounts
    ynab_df['Amount'] = df[CARD_AMOUNT_COLUMN].apply(convert_amount)
    ynab_df['Amount'] = ynab_df['Amount'].round(2)

    return ynab_df


def convert_nbg_to_ynab(xlsx_file):
    """
    Convert NBG Excel file to YNAB CSV format.

    :param xlsx_file: Path to the input XLSX file
    """
    try:
        # Read the XLSX file
        df = pd.read_excel(xlsx_file)

        # Determine which type of export the file is
        if set(ACCOUNT_REQUIRED_COLUMNS).issubset(df.columns):
            ynab_df = process_account_operations(df)
        elif set(CARD_REQUIRED_COLUMNS).issubset(df.columns):
            ynab_df = process_card_operations(df)
        else:
            raise ValueError(
                "The provided Excel file does not match the required format for either Account or Card operations.")

        # Save to CSV
        csv_file = f"{os.path.splitext(xlsx_file)[0]}_ynab.csv"
        ynab_df.to_csv(csv_file, index=False, quoting=csv.QUOTE_MINIMAL)
        print(f"Conversion complete. The CSV file is saved as: {csv_file}")

    except FileNotFoundError:
        print(f"Error: The file '{xlsx_file}' was not found.")
    except pd.errors.EmptyDataError:
        print(f"Error: The file '{xlsx_file}' is empty or could not be read.")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_xlsx_file>")
        print("Example: python main.py /Users/user/Documents/file.xlsx")
    else:
        xlsx_file_path = sys.argv[1]
        if not xlsx_file_path.endswith(('.xlsx', '.xls')):
            print(f"Error: The file '{xlsx_file_path}' is not a valid Excel file.")
        else:
            convert_nbg_to_ynab(xlsx_file_path)
