import pandas as pd
import os
import sys
import csv


def convert_nbg_to_ynab(xlsx_file):
    try:
        # Step 1: Read the XLSX file
        df = pd.read_excel(xlsx_file)

        # Check for required columns
        required_columns = [
            'Valeur', 'Περιγραφή', 'Ονοματεπώνυμο αντισυμβαλλόμενου', 'Ποσό συναλλαγής', 'Χρέωση / Πίστωση'
        ]
        if not all(col in df.columns for col in required_columns):
            raise ValueError(f"One or more required columns are missing in the XLSX file: {xlsx_file}")

        # Step 2: Convert the columns to match the YNAB format
        ynab_df = pd.DataFrame()

        # Convert "Valeur" to "Date" in YYYY-MM-DD format
        ynab_df['Date'] = pd.to_datetime(df['Valeur'], format='%d.%m.%Y').dt.strftime('%Y-%m-%d')

        # "Περιγραφή" to "Payee"
        ynab_df['Payee'] = df['Περιγραφή']

        # "Ονοματεπώνυμο αντισυμβαλλόμενου" to "Memo"
        ynab_df['Memo'] = df['Ονοματεπώνυμο αντισυμβαλλόμενου']

        # Convert amounts: negative for "Χρέωση" and positive for "Πίστωση"
        ynab_df['Amount'] = df.apply(
            lambda row: float(str(row['Ποσό συναλλαγής']).replace(',', '.')) *
            (-1 if row['Χρέωση / Πίστωση'] == 'Χρέωση' else 1), axis=1
        )

        # Step 3: Save to CSV in YNAB format
        csv_file = os.path.splitext(xlsx_file)[0] + '.csv'

        # Save the YNAB DataFrame to a CSV file
        ynab_df.to_csv(csv_file, index=False, quoting=csv.QUOTE_MINIMAL)

        print(f"Conversion complete. The CSV file is saved as: {csv_file}")

    except Exception as e:
        print(f"An error occurred during conversion: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_xlsx_file>")
        print("Example: python main.py /Users/user/Documents/file.xlsx")
    else:
        xlsx_file_path = sys.argv[1]

        if not os.path.exists(xlsx_file_path):
            print(f"Error: The file '{xlsx_file_path}' does not exist.")
        elif not xlsx_file_path.endswith(('.xlsx', '.xls')):
            print(f"Error: The file '{xlsx_file_path}' is not a valid Excel file.")
        else:
            convert_nbg_to_ynab(xlsx_file_path)
