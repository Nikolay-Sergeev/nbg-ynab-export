# flake8: noqa
import os
import tempfile
import unittest
import pandas as pd
from datetime import datetime
from PyQt5.QtWidgets import QApplication
from ui.wizard import StepLabel, load_style
from main import (
    convert_amount,
    extract_date_from_filename,
    generate_output_filename,
    exclude_existing_transactions,
    process_card_operations,
    process_account_operations,
    process_revolut_operations,  # Add this import
    validate_dataframe,
    validate_revolut_currency,  # Add this
    REVOLUT_REQUIRED_COLUMNS,
    validate_input_file,
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

        # Add Revolut test data
        self.revolut_data = pd.DataFrame({
            'Type': ['CARD_PAYMENT', 'CARD_PAYMENT', 'TRANSFER', 'TRANSFER'],
            'Product': ['Current'] * 4,
            'Started Date': [
                '2024-12-22 12:40:01',  # Payment with fee
                '2024-11-24 11:36:16',  # Another payment with fee
                '2024-11-27 15:16:00',  # Incoming transfer
                '2025-02-02 09:51:52'   # Another incoming transfer
            ],
            'Completed Date': [
                '2024-12-23 06:06:09',
                '2024-11-24 17:21:49',
                '2024-11-27 15:16:00',
                '2025-02-02 09:51:53'
            ],
            'Description': ['OpenAI', 'Yandex Plus', 'From JOHN DOE', 'From JANE DOE'],
            'Amount': ['-19.26', '-27.72', '8.00', '500.00'],
            'Fee': ['0.19', '0.28', '0.00', '0.00'],
            'Currency': ['EUR', 'EUR', 'EUR', 'EUR'],
            'State': ['COMPLETED', 'COMPLETED', 'COMPLETED', 'COMPLETED'],
            'Balance': ['314.64', '484.21', '492.21', '797.24']
        })

    def test_convert_amount(self):
        """Test amount conversion with different formats.

        Test cases:
        - Simple integer values
        - Negative integers
        - Decimal with comma (European format)
        - Negative decimals
        - Balance amounts
        - Float inputs
        """
        test_cases = [
            # Update test cases to match actual formats
            ("7", 7.0),              # Simple integer
            ("-7", -7.0),           # Negative integer
            ("7,99", 7.99),         # Decimal with comma
            ("-7,99", -7.99),       # Negative decimal with comma
            ("1.234,56", 1234.56),  # Thousands with dot, comma decimal
            ("1,234.56", 1234.56),  # Thousands with comma, dot decimal
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

    def test_generate_output_filename_existing_ymd_date(self):
        """Ensure existing YYYY-MM-DD dates are removed from the base name."""
        input_path = "/path/to/statement_2025-02-25.xlsx"
        expected = "/path/to/statement_2025-02-25_ynab.csv"
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

    def test_exclude_existing_complex(self):
        """Test complex scenarios for excluding existing transactions."""
        new_df = pd.DataFrame({
            'Date': ['2025-02-25', '2025-02-25', '2025-02-26', '2025-02-24'],
            'Payee': ['SPOTIFY', 'NETFLIX', 'NETFLIX', 'OLD'],
            'Amount': [-7.99, -15.99, -15.99, -10.00]
        })
        prev_df = pd.DataFrame({
            'Date': ['2025-02-24'],  # Only include old transaction
            'Payee': ['OLD'],
            'Amount': [-10.00]
        })

        result = exclude_existing_transactions(new_df, prev_df)

        # Should keep all transactions after 2025-02-24
        self.assertEqual(len(result), 3)
        self.assertTrue(all(pd.to_datetime(result['Date']) > pd.to_datetime('2025-02-24')))
        self.assertTrue('OLD' not in result['Payee'].values)

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

    def test_process_revolut_operations(self):
        """Test Revolut operations processing."""
        result = process_revolut_operations(self.revolut_data)

        # Test expense transaction with fee
        self.assertEqual(result.iloc[0]['Date'], '2024-12-22')
        self.assertEqual(result.iloc[0]['Payee'], 'OpenAI')
        self.assertEqual(result.iloc[0]['Amount'], -19.45)  # -19.26 - 0.19
        self.assertEqual(result.iloc[0]['Memo'], 'CARD_PAYMENT')

        # Test another expense with fee
        self.assertEqual(result.iloc[1]['Date'], '2024-11-24')
        self.assertEqual(result.iloc[1]['Payee'], 'Yandex Plus')
        self.assertEqual(result.iloc[1]['Amount'], -28.00)  # -27.72 - 0.28
        self.assertEqual(result.iloc[1]['Memo'], 'CARD_PAYMENT')

        # Test incoming transfer without fee
        self.assertEqual(result.iloc[2]['Date'], '2024-11-27')
        self.assertEqual(result.iloc[2]['Payee'], 'From JOHN DOE')
        self.assertEqual(result.iloc[2]['Amount'], 8.00)
        self.assertEqual(result.iloc[2]['Memo'], 'TRANSFER')

        # Test another incoming transfer without fee
        self.assertEqual(result.iloc[3]['Date'], '2025-02-02')
        self.assertEqual(result.iloc[3]['Payee'], 'From JANE DOE')
        self.assertEqual(result.iloc[3]['Amount'], 500.00)
        self.assertEqual(result.iloc[3]['Memo'], 'TRANSFER')

        # Check columns
        self.assertEqual(list(result.columns), ['Date', 'Payee', 'Memo', 'Amount'])

    def test_revolut_filter_reverted(self):
        """Test filtering out reverted Revolut transactions."""
        # Add reverted transaction to test data
        reverted_data = self.revolut_data.copy()
        reverted_data.loc[len(reverted_data)] = [
            'CARD_PAYMENT', 'Current', '2024-11-08 09:32:33', '',
            'Uber', '-21.36', '0.00', 'EUR', 'REVERTED', ''
        ]

        result = process_revolut_operations(reverted_data)

        # Check that reverted transaction was filtered out
        self.assertEqual(len(result), len(self.revolut_data))
        self.assertFalse(any(result['Payee'] == 'Uber'))

    def test_validate_revolut_currency(self):
        """Test Revolut currency validation.

        Test cases:
        - Valid: All EUR transactions
        - Invalid: Contains non-EUR transaction
        """
        # Valid case - all EUR
        validate_revolut_currency(self.revolut_data)

        # Invalid case - mixed currencies
        invalid_data = self.revolut_data.copy()
        invalid_data.loc[len(invalid_data)] = [
            'CARD_PAYMENT', 'Current', '2024-11-08 09:32:33', '',
            'Foreign Payment', '-21.36', '0.00', 'USD', 'COMPLETED', ''
        ]

        with self.assertRaises(ValueError):
            validate_revolut_currency(invalid_data)

    def test_empty_file_handling(self):
        """Test handling of empty input files.

        Test cases:
        - Completely empty DataFrame (no columns, no data)
        - DataFrame with required columns but no data
        - DataFrame with missing required columns
        """
        # Case 1: Completely empty DataFrame
        empty_df = pd.DataFrame()
        with self.assertRaisesRegex(ValueError, "Empty DataFrame provided"):
            validate_dataframe(empty_df, REVOLUT_REQUIRED_COLUMNS)

        # Case 2: DataFrame with required columns but no data
        df_no_data = pd.DataFrame(columns=REVOLUT_REQUIRED_COLUMNS)
        with self.assertRaisesRegex(ValueError, "DataFrame contains no data"):
            validate_dataframe(df_no_data, REVOLUT_REQUIRED_COLUMNS)

        # Case 3: DataFrame with missing required columns
        df_missing_cols = pd.DataFrame({'Type': ['CARD_PAYMENT']})
        with self.assertRaisesRegex(ValueError, "Missing required columns"):
            validate_dataframe(df_missing_cols, REVOLUT_REQUIRED_COLUMNS)


class TestUIComponents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        cls.app = QApplication.instance() or QApplication([])

    def test_load_style_applies_stylesheet(self):
        load_style(self.app)
        self.assertTrue(self.app.styleSheet())


class TestValidateInputFile(unittest.TestCase):
    def test_validate_input_file_success(self):
        with tempfile.NamedTemporaryFile(suffix='.csv') as tmp:
            validate_input_file(tmp.name)

    def test_validate_input_file_missing(self):
        with self.assertRaises(FileNotFoundError):
            validate_input_file('nonexistent.csv')

    def test_validate_input_file_bad_ext(self):
        with tempfile.NamedTemporaryFile(suffix='.txt') as tmp:
            with self.assertRaises(ValueError):
                validate_input_file(tmp.name)


if __name__ == '__main__':
    unittest.main(verbosity=2)
