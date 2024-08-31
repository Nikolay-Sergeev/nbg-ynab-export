import pandas as pd
import os
import sys
import csv

def convert_nbg_to_ynab(xlsx_file):
    # Step 1: Read the XLSX file
    df = pd.read_excel(xlsx_file)

    # Step 2: Convert the columns to match the YNAB format
    ynab_df = pd.DataFrame()

    # Convert "Valeur" to "Date" in YYYY-MM-DD format
    ynab_df['Date'] = pd.to_datetime(df['Valeur'], format='%d.%m.%Y').dt.strftime('%Y-%m-%d')

    # "Περιγραφή" to "Payee"
    ynab_df['Payee'] = df['Περιγραφή']

    # "Ονοματεπώνυμο αντισυμβαλλόμενου" to "Memo"
    ynab_df['Memo'] = df['Ονοματεπώνυμο αντισυμβαλλόμενου']

    # "Ποσό συναλλαγής" to "Amount"
    # Correctly handle the European decimal format (comma as a decimal separator)
    ynab_df['Amount'] = df['Ποσό συναλλαγής'].apply(lambda x: float(str(x).replace(',', '.')))

    # Amounts should be negative for expenses and positive for income
    ynab_df['Amount'] = ynab_df['Amount'].apply(lambda x: x if df['Χρέωση / Πίστωση'].iloc[0] == 'Πίστωση' else -x)

    # Step 3: Save to CSV in YNAB format
    csv_file = os.path.splitext(xlsx_file)[0] + '.csv'

    # Save the YNAB DataFrame to a CSV file
    ynab_df.to_csv(csv_file, index=False, quoting=csv.QUOTE_MINIMAL)

    print(f"Conversion complete. The CSV file is saved as: {csv_file}")


if __name__ == "__main__":
    # Check if the script was provided with the file path argument
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_xlsx_file>")
        print("Example: python main.py /Users/user/Documents/file.xlsx")
    else:
        # Get the file path from the command line arguments
        xlsx_file_path = sys.argv[1]

        # Check if the file exists
        if not os.path.exists(xlsx_file_path):
            print(f"Error: The file '{xlsx_file_path}' does not exist.")
        else:
            # Run the conversion function
            convert_nbg_to_ynab(xlsx_file_path)
