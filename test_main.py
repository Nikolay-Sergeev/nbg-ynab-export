import unittest
import pandas as pd
import os
from datetime import datetime
from main import (
    convert_amount,
    extract_date_from_filename,
    generate_output_filename,
    exclude_existing_transactions,
    process_card_operations,
    process_account_operations,
    validate_dataframe
)

class TestNBGToYNAB(unittest.TestCase):
    def setUp(self):
        """Set up test data."""
        # Card statement test data - add income transaction
        self.card_data = pd.DataFrame({
            'Αριθμός Κάρτας': ['1234****5678', '1234****5678'],
            'Περίοδος Από': ['25/1/2025', '25/1/2025'],
            'Περίοδος Έως': ['27/2/2025', '27/2/2025'],
            'Α/Α': [3, 4],
            'Ημερομηνία/Ώρα Συναλλαγής': ['21/2/2025 10:00 μμ', '14/2/2025 4:51 μμ'],
            'Περιγραφή Κίνησης': ['E-COMMERCE ΑΓΟΡΑ - SHOP.EXAMPLE.COM', 'ΦΟΡΤΙΣΗ'],
            'Χ/Π': ['Χ', 'Π'],
            'Ποσό': ['-12,34', '100'],
            'Νόμισμα Λογαριασμού': ['EUR', 'EUR'],
            'Ποσό εντολής': ['12,34', '100'],
            'Νόμισμα Συναλλαγής': ['EUR', 'EUR'],
            'Ισοτιμία Συναλλαγής': [1, 1],
            'Στοιχεία Εμπόρου': ['123456789', ''],
            'Αριθμός Κάρτας.1': ['1234****5678', '1234****5678']
        })

        # Account statement test data - add income transaction
        self.account_data = pd.DataFrame({
            'Α/Α Συναλλαγής': [20, 95],
            'Ημερομηνία': ['18/02/2025', '31/01/2025'],
            'Ώρα': ['19:20', '09:53'],
            'Valeur': ['17/02/2025', '31/01/2025'],
            'Κατάστημα': ['705', '679'],
            'Κατηγορία συναλλαγής': ['40 ΑΓΟΡΑ', '13 ΠΡΟΙΟΝ ΕΝΤΟΛΗΣ'],
            'Είδος εργασίας': [
                '83210 Aγορά με χρήση χρεωστικής κάρτας',
                '90001 Εισερχόμενα Εμβάσματα Ευρώ'
            ],
            'Ποσό συναλλαγής': ['-12,34', '1234,56'],
            'Ποσό εντολής': ['-12,34', '1234,56'],
            'Νόμισμα': ['', ''],
            'Χρέωση / Πίστωση': ['Χρέωση', 'Πίστωση'],
            'Ισοτιμία': ['', ''],
            'Περιγραφή': ['SHOP.EXAMPLE.COM', 'EXAMPLE COMPANY LTD'],
            'Λογιστικό Υπόλοιπο': ['1000,00', '2000,00'],
            'Ονοματεπώνυμο συμβαλλόμενου': ['JOHN DOE', ''],
            'Ονοματεπώνυμο αντισυμβαλλόμενου': ['SHOP.EXAMPLE.COM', 'JOHN DOE'],
            'Λογαριασμός αντισυμβαλλόμενου': ['', ''],
            'Τράπεζα αντισυμβαλλόμενου': ['', ''],
            'Επιπρόσθετες πληροφορίες': ['', ''],
            'Αριθμός αναφοράς': ['TX123456', 'TX789012'],
            'Κανάλι': ['ECOMMERCE', ''],
            'Ονοματεπώνυμο αντιπροσώπου': ['', ''],
            'Είδος προμήθειας': ['', ''],
            'Κωδικός εμπόρου/οργανισμού': ['1234', ''],
            'Σκοπός συναλλαγής': ['', ''],
            'Ημερομηνία Συναλλαγής με χρεωστική κάρτα': ['16/02/2025', ''],
            'Ώρα Συναλλαγής με χρεωστική κάρτα': ['13:41', ''],
            'Χρεωστική Κάρτα': ['1234****5678', '']
        })

    def test_convert_amount(self):
        """Test amount conversion with different formats."""
        test_cases = [
            # Update test cases to match actual formats
            ("7", 7.0),              # Simple integer
            ("-7", -7.0),           # Negative integer
            ("7,99", 7.99),         # Decimal with comma
            ("-7,99", -7.99),       # Negative decimal with comma
            ("769,53", 769.53),     # Balance amount
            (1234.56, 1234.56),     # Float input
            (-1234.56, -1234.56)    # Negative float input
        ]
        for input_val, expected in test_cases:
            with self.subTest(input_val=input_val):
                self.assertEqual(convert_amount(input_val), expected)

    def test_extract_date_from_filename(self):
        """Test date extraction from different filename formats."""
        test_cases = [
            ("statementexport25-02-2025", "2025-02-25"),
            ("statement_2025-02-25_test", "2025-02-25"),
            ("CardStatementExport", ""),
            ("nodate", ""),
            ("statement_25-02-2025_ynab", "2025-02-25")
        ]
        for filename, expected in test_cases:
            with self.subTest(filename=filename):
                self.assertEqual(extract_date_from_filename(filename), expected)

    def test_generate_output_filename(self):
        """Test output filename generation."""
        test_cases = [
            ("/path/to/statementexport25-02-2025.xlsx", 
             "/path/to/statementexport_2025-02-25_ynab.csv"),
            ("/path/to/CardStatementExport.xlsx", 
             f"/path/to/CardStatementExport_{datetime.now().strftime('%Y-%m-%d')}_ynab.csv")
        ]
        for input_path, expected in test_cases:
            with self.subTest(input_path=input_path):
                self.assertEqual(generate_output_filename(input_path), expected)

    def test_exclude_existing_transactions(self):
        """Test exclusion of existing transactions."""
        new_df = pd.DataFrame({
            'Date': ['2025-02-25', '2025-02-26'],
            'Payee': ['SPOTIFY', 'NETFLIX'],
            'Amount': [-7.99, -15.99]
        })
        prev_df = pd.DataFrame({
            'Date': ['2025-02-25'],
            'Payee': ['SPOTIFY'],
            'Amount': [-7.99]
        })
        result = exclude_existing_transactions(new_df, prev_df)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['Payee'], 'NETFLIX')

    def test_process_card_operations(self):
        """Test card operations processing."""
        result = process_card_operations(self.card_data)
        
        # Test expense transaction
        self.assertEqual(result.iloc[0]['Date'], '2025-02-21')
        self.assertEqual(result.iloc[0]['Payee'], 'SHOP.EXAMPLE.COM')
        self.assertEqual(result.iloc[0]['Amount'], -12.34)
        
        # Test income transaction
        self.assertEqual(result.iloc[1]['Date'], '2025-02-14')
        self.assertEqual(result.iloc[1]['Payee'], 'ΦΟΡΤΙΣΗ')
        self.assertEqual(result.iloc[1]['Amount'], 100.0)
        
        self.assertEqual(list(result.columns), ['Date', 'Payee', 'Memo', 'Amount'])

    def test_process_account_operations(self):
        """Test account operations processing."""
        result = process_account_operations(self.account_data)
        
        # Test expense transaction
        self.assertEqual(result.iloc[0]['Date'], '2025-02-17')
        self.assertEqual(result.iloc[0]['Payee'], 'SHOP.EXAMPLE.COM')
        self.assertEqual(result.iloc[0]['Amount'], -12.34)
        self.assertEqual(result.iloc[0]['Memo'], 'SHOP.EXAMPLE.COM')
        
        # Test income transaction
        self.assertEqual(result.iloc[1]['Date'], '2025-01-31')
        self.assertEqual(result.iloc[1]['Payee'], 'JOHN DOE')
        self.assertEqual(result.iloc[1]['Amount'], 1234.56)
        self.assertEqual(result.iloc[1]['Memo'], 'EXAMPLE COMPANY LTD')
        
        self.assertEqual(list(result.columns), ['Date', 'Payee', 'Memo', 'Amount'])

    def test_validate_dataframe(self):
        """Test DataFrame validation."""
        # Valid case
        validate_dataframe(self.card_data, ['Ημερομηνία/Ώρα Συναλλαγής', 'Περιγραφή Κίνησης'])
        
        # Invalid case
        with self.assertRaises(ValueError):
            validate_dataframe(self.card_data, ['NonExistentColumn'])

if __name__ == '__main__':
    unittest.main(verbosity=2)