import pandas as pd
import os
import sys
import csv


def convert_nbg_to_ynab(xlsx_file, ynab_export_tsv=None):
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
    ynab_df['Amount'] = df['Ποσό συναλλαγής'].apply(lambda x: float(str(x).replace(',', '.')))

    # Amounts should be negative for expenses and positive for income
    ynab_df['Amount'] = ynab_df['Amount'].apply(lambda x: x if df['Χρέωση / Πίστωση'].iloc[0] == 'Πίστωση' else -x)

    # If YNAB export is provided, filter out older transactions
    if ynab_export_tsv:
        ynab_export_df = pd.read_csv(ynab_export_tsv, sep='\t')

        # Convert "Date" in YNAB export to datetime
        ynab_export_df['Date'] = pd.to_datetime(ynab_export_df['Date'])

        # Group by Payee and get the 2 latest transactions for each Payee
        latest_transactions = ynab_export_df.sort_values('Date').groupby('Payee').tail(2)

        # Merge with import data to find common transactions
        merged_df = pd.merge(ynab_df, latest_transactions, on=['Date', 'Payee', 'Amount'], how='inner')

        # Remove all transactions from ynab_df that are older or equal to the latest ones found in the export
        if not merged_df.empty:
            ynab_df = ynab_df[~ynab_df.apply(
                lambda row: (row['Date'] <= merged_df['Date'].max()) & (row['Payee'] == merged_df['Payee'].iloc[0]) & (
                            row['Amount'] == merged_df['Amount'].iloc[0]), axis=1)]

    # Step 3: Save to CSV in YNAB format
    csv_file = os.path.splitext(xlsx_file)[0] + '.csv'

    # Save the YNAB DataFrame to a CSV file
    ynab_df.to_csv(csv_file, index=False, quoting=csv.QUOTE_MINIMAL)

    print(f"Conversion complete. The CSV file is saved as: {csv_file}")


if __name__ == "__main__":
    # Check if the script was provided with the file path argument
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_xlsx_file> [<ynab_export_tsv>]")
        print("Example: python main.py /Users/nikolaysergeev/Documents/file.xlsx /Users/nikolaysergeev/Documents/export.tsv")
    else:
        # Get the file path from the command line arguments
        xlsx_file_path = sys.argv[1]
        ynab_export_tsv = sys.argv[2] if len(sys.argv) > 2 else None

        # Check if the file exists
        if not os.path.exists(xlsx_file_path):
            print(f"Error: The file '{xlsx_file_path}' does not exist.")
        elif ynab_export_tsv and not os.path.exists(ynab_export_tsv):
            print(f"Error: The file '{ynab_export_tsv}' does not exist.")
        else:
            # Run the conversion function
            convert_nbg_to_ynab(xlsx_file_path, ynab_export_tsv)
