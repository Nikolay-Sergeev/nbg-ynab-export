import pandas as pd
import os
import sys
import csv

# Constants
REQUIRED_COLUMNS = ['Valeur', 'Περιγραφή', 'Ονοματεπώνυμο αντισυμβαλλόμενου', 'Ποσό συναλλαγής', 'Χρέωση / Πίστωση']
DATE_COLUMN = 'Valeur'
PAYEE_COLUMN = 'Περιγραφή'
MEMO_COLUMN = 'Ονοματεπώνυμο αντισυμβαλλόμενου'
AMOUNT_COLUMN = 'Ποσό συναλλαγής'
DEBIT_CREDIT_COLUMN = 'Χρέωση / Πίστωση'


def convert_amount(amount):
    """
    Convert amount to float, handling both string and numeric inputs.
    """
    if isinstance(amount, str):
        return float(amount.replace(',', '.'))
    return float(amount)


def convert_nbg_to_ynab(xlsx_file):
    """
    Convert NBG Excel file to YNAB CSV format.

    :param xlsx_file: Path to the input XLSX file
    """
    try:
        # Read the XLSX file
        df = pd.read_excel(xlsx_file)

        # Check for required columns
        missing_columns = set(REQUIRED_COLUMNS) - set(df.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

        # Convert to YNAB format
        ynab_df = pd.DataFrame()
        ynab_df['Date'] = pd.to_datetime(df[DATE_COLUMN], format='%d.%m.%Y', errors='coerce').dt.strftime('%Y-%m-%d')
        ynab_df['Payee'] = df[PAYEE_COLUMN]
        ynab_df['Memo'] = df[MEMO_COLUMN]

        # Convert amounts
        ynab_df['Amount'] = df[AMOUNT_COLUMN].apply(convert_amount)
        ynab_df.loc[df[DEBIT_CREDIT_COLUMN] == 'Χρέωση', 'Amount'] *= -1
        ynab_df['Amount'] = ynab_df['Amount'].round(2)

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
