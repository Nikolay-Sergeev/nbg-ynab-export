import unittest
import os
import tempfile
import pandas as pd
from unittest.mock import patch

from services.conversion_service import (
    normalize_column_name,
    validate_dataframe,
    convert_amount,
    process_account_operations,
    process_card_operations,
    validate_revolut_currency,
    process_revolut_operations,
    exclude_existing_transactions,
    extract_date_from_filename,
    generate_output_filename,
    validate_input_file
)


class TestConversionServiceCore(unittest.TestCase):
    """Tests for core functions in conversion_service.py."""

    def test_normalize_column_name(self):
        """Test column name normalization."""
        test_cases = [
            (" Column  Name ", "Column Name"),
            ("Column\tName", "Column Name"),
            ("Column\nName", "Column Name"),
            ("  Extra   Spaces  ", "Extra Spaces"),
            ("NoChange", "NoChange"),
            ("", "")
        ]
        
        for input_col, expected in test_cases:
            with self.subTest(input_col=input_col):
                result = normalize_column_name(input_col)
                self.assertEqual(result, expected)

    def test_validate_dataframe_empty(self):
        """Test validating empty DataFrame."""
        # Empty DataFrame with no columns
        empty_df = pd.DataFrame()
        with self.assertRaises(ValueError) as cm:
            validate_dataframe(empty_df, ["Column1"])
        self.assertIn("Empty DataFrame", str(cm.exception))

        # DataFrame with columns but no data
        empty_data_df = pd.DataFrame(columns=["Column1", "Column2"])
        with self.assertRaises(ValueError) as cm:
            validate_dataframe(empty_data_df, ["Column1"])
        self.assertIn("contains no data", str(cm.exception))

    def test_validate_dataframe_missing_columns(self):
        """Test validating DataFrame with missing required columns."""
        df = pd.DataFrame({
            "Column1": [1, 2],
            "Column2": ["a", "b"]
        })
        
        # Test with one missing column
        with self.assertRaises(ValueError) as cm:
            validate_dataframe(df, ["Column1", "Column3"])
        self.assertIn("Missing required columns", str(cm.exception))
        
        # Test with multiple missing columns
        with self.assertRaises(ValueError) as cm:
            validate_dataframe(df, ["Column1", "Column3", "Column4"])
        self.assertIn("Missing required columns", str(cm.exception))
        
        # Test with normalized column names
        df_messy = pd.DataFrame({
            " Column1 ": [1, 2],
            "Column2  ": ["a", "b"]
        })
        
        # This should pass despite the space differences
        validate_dataframe(df_messy, ["Column1", "Column2"])

    def test_validate_dataframe_success(self):
        """Test successful DataFrame validation."""
        df = pd.DataFrame({
            "Column1": [1, 2],
            "Column2": ["a", "b"]
        })
        
        # Should not raise an exception
        validate_dataframe(df, ["Column1", "Column2"])
        validate_dataframe(df, ["Column1"])  # Only validating subset of columns

    def test_convert_amount(self):
        """Test amount conversion with various formats."""
        test_cases = [
            ("1234,56", 1234.56),
            ("1234.56", 1234.56),
            ("1.234,56", 1234.56),
            ("1,234.56", 1234.56),
            ("-1234,56", -1234.56),
            ("0,00", 0.0),
            (1234.56, 1234.56),  # Already a float
            (0, 0.0)  # Integer
        ]
        
        for input_amount, expected in test_cases:
            with self.subTest(input_amount=input_amount):
                result = convert_amount(input_amount)
                self.assertEqual(result, expected)
                self.assertIsInstance(result, float)

    def test_extract_date_from_filename(self):
        """Test extracting date from filename patterns."""
        test_cases = [
            ("statement_15-07-2025.csv", "2025-07-15"),
            ("statement_15-07-2025_extra.csv", "2025-07-15"),
            ("prefix_15-07-2025_suffix.csv", "2025-07-15"),
            ("no_date_here.csv", "")
        ]
        
        for filename, expected in test_cases:
            with self.subTest(filename=filename):
                result = extract_date_from_filename(filename)
                self.assertEqual(result, expected)

    def test_generate_output_filename(self):
        """Test generating output filename."""
        test_dir = tempfile.mkdtemp()
        test_cases = [
            # With date in filename
            (os.path.join(test_dir, "statement_15-07-2025.xlsx"), "statement_2025-07-15_ynab.csv"),
            # Without date in filename
            (os.path.join(test_dir, "statement.xlsx"), lambda x: x.endswith("_ynab.csv"))
        ]
        
        for input_file, expected in test_cases:
            with self.subTest(input_file=input_file):
                result = generate_output_filename(input_file)
                if callable(expected):
                    self.assertTrue(expected(os.path.basename(result)))
                else:
                    self.assertTrue(os.path.basename(result).endswith(expected))

    def test_validate_input_file_nonexistent(self):
        """Test validating non-existent input file."""
        nonexistent_file = "/path/to/nonexistent.xlsx"
        with self.assertRaises(FileNotFoundError):
            validate_input_file(nonexistent_file)

    @patch('os.path.exists', return_value=True)
    def test_validate_input_file_unsupported(self, mock_exists):
        """Test validating file with unsupported extension."""
        unsupported_files = [
            "/path/to/file.txt",
            "/path/to/file.pdf",
            "/path/to/file.docx"
        ]
        
        for file_path in unsupported_files:
            with self.subTest(file_path=file_path):
                with self.assertRaises(ValueError) as cm:
                    validate_input_file(file_path)
                self.assertIn("Unsupported file type", str(cm.exception))

    @patch('os.path.exists', return_value=True)
    def test_validate_input_file_supported(self, mock_exists):
        """Test validating file with supported extension."""
        supported_files = [
            "/path/to/file.xlsx",
            "/path/to/file.xls",
            "/path/to/file.csv"
        ]
        
        for file_path in supported_files:
            with self.subTest(file_path=file_path):
                # Should not raise an exception
                validate_input_file(file_path)


class TestAccountOperations(unittest.TestCase):
    """Tests for account operations processing."""

    def setUp(self):
        """Set up test data."""
        self.account_data = pd.DataFrame({
            'Valeur': ['15/07/2025', '14/07/2025'],
            'Ονοματεπώνυμο αντισυμβαλλόμενου': ['SUPERMARKET XYZ', 'JOHN DOE'],
            'Περιγραφή': ['MARKET PURCHASE', 'SALARY TRANSFER'],
            'Ποσό συναλλαγής': ['45,67', '1500,00'],
            'Χρέωση / Πίστωση': ['Χρέωση', 'Πίστωση']
        })

    def test_process_account_operations(self):
        """Test processing account operations."""
        result = process_account_operations(self.account_data)
        
        # Check basic structure
        self.assertEqual(len(result), 2)
        self.assertListEqual(list(result.columns), ['Date', 'Payee', 'Memo', 'Amount'])
        
        # Check conversion of first row (debit)
        self.assertEqual(result.iloc[0]['Date'], '2025-07-15')
        self.assertEqual(result.iloc[0]['Payee'], 'SUPERMARKET XYZ')
        self.assertEqual(result.iloc[0]['Memo'], 'MARKET PURCHASE')
        self.assertAlmostEqual(result.iloc[0]['Amount'], -45.67)
        
        # Check conversion of second row (credit)
        self.assertEqual(result.iloc[1]['Date'], '2025-07-14')
        self.assertEqual(result.iloc[1]['Payee'], 'JOHN DOE')
        self.assertEqual(result.iloc[1]['Memo'], 'SALARY TRANSFER')
        self.assertAlmostEqual(result.iloc[1]['Amount'], 1500.00)

    def test_process_account_operations_with_ecommerce(self):
        """Test processing account operations with E-COMMERCE prefixes."""
        # Add a row with E-COMMERCE prefix
        ecommerce_data = self.account_data.copy()
        ecommerce_data.loc[2] = [
            '13/07/2025',
            'E-COMMERCE ΑΓΟΡΑ - ONLINE SHOP',
            'ONLINE PURCHASE',
            '25,99',
            'Χρέωση'
        ]
        
        result = process_account_operations(ecommerce_data)
        
        # Check the E-COMMERCE row
        self.assertEqual(result.iloc[2]['Date'], '2025-07-13')
        self.assertEqual(result.iloc[2]['Payee'], 'ONLINE SHOP')
        self.assertEqual(result.iloc[2]['Memo'], 'ONLINE PURCHASE')
        self.assertAlmostEqual(result.iloc[2]['Amount'], -25.99)

    def test_process_account_operations_with_empty_payee(self):
        """Test processing account operations with empty payee (fallback to memo)."""
        # Add a row with empty payee
        empty_payee_data = self.account_data.copy()
        empty_payee_data.loc[2] = [
            '13/07/2025',
            '',  # Empty payee
            'ATM WITHDRAWAL',
            '100,00',
            'Χρέωση'
        ]
        
        result = process_account_operations(empty_payee_data)
        
        # Check that Memo was used as Payee
        self.assertEqual(result.iloc[2]['Date'], '2025-07-13')
        self.assertEqual(result.iloc[2]['Payee'], 'ATM WITHDRAWAL')
        self.assertEqual(result.iloc[2]['Memo'], 'ATM WITHDRAWAL')
        self.assertAlmostEqual(result.iloc[2]['Amount'], -100.00)

    def test_process_account_operations_invalid_date(self):
        """Test processing account operations with invalid date format."""
        invalid_date_data = self.account_data.copy()
        invalid_date_data.iloc[0, 0] = 'Invalid date'
        
        with self.assertRaises(ValueError) as cm:
            process_account_operations(invalid_date_data)
        self.assertIn("Invalid date format", str(cm.exception))

    def test_process_account_operations_missing_columns(self):
        """Test processing account operations with missing required columns."""
        missing_columns_data = pd.DataFrame({
            'Valeur': ['15/07/2025'],
            # Missing other required columns
        })
        
        with self.assertRaises(ValueError) as cm:
            process_account_operations(missing_columns_data)
        self.assertIn("Missing required columns", str(cm.exception))


class TestCardOperations(unittest.TestCase):
    """Tests for card operations processing."""

    def setUp(self):
        """Set up test data."""
        self.card_data = pd.DataFrame({
            'Ημερομηνία/Ώρα Συναλλαγής': ['21/02/2025 10:00 μμ', '14/02/2025 4:51 μμ'],
            'Περιγραφή Κίνησης': ['E-COMMERCE ΑΓΟΡΑ - SHOP.EXAMPLE.COM', 'ΦΟΡΤΙΣΗ'],
            'Χ/Π': ['Χ', 'Π'],
            'Ποσό': ['12,34', '100,00']
        })

    def test_process_card_operations(self):
        """Test processing card operations."""
        result = process_card_operations(self.card_data)
        
        # Check basic structure
        self.assertEqual(len(result), 2)
        self.assertListEqual(list(result.columns), ['Date', 'Payee', 'Memo', 'Amount'])
        
        # Check conversion of first row (debit)
        self.assertEqual(result.iloc[0]['Date'], '2025-02-21')
        self.assertEqual(result.iloc[0]['Payee'], 'SHOP.EXAMPLE.COM')
        self.assertEqual(result.iloc[0]['Memo'], 'E-COMMERCE ΑΓΟΡΑ - SHOP.EXAMPLE.COM')
        self.assertAlmostEqual(result.iloc[0]['Amount'], -12.34)
        
        # Check conversion of second row (credit)
        self.assertEqual(result.iloc[1]['Date'], '2025-02-14')
        self.assertEqual(result.iloc[1]['Payee'], 'ΦΟΡΤΙΣΗ')
        self.assertEqual(result.iloc[1]['Memo'], 'ΦΟΡΤΙΣΗ')
        self.assertAlmostEqual(result.iloc[1]['Amount'], 100.00)

    def test_process_card_operations_with_parenthesis(self):
        """Test processing card operations with parenthetical text."""
        parenthesis_data = self.card_data.copy()
        parenthesis_data.loc[2] = [
            '13/02/2025 2:30 μμ',
            '3D SECURE E-COMMERCE ΑΓΟΡΑ - AMAZON (REF: 12345)',
            'Χ',
            '45,99'
        ]
        
        result = process_card_operations(parenthesis_data)
        
        # Check parenthesis cleanup
        self.assertEqual(result.iloc[2]['Date'], '2025-02-13')
        self.assertEqual(result.iloc[2]['Payee'], 'AMAZON')
        self.assertEqual(result.iloc[2]['Memo'], '3D SECURE E-COMMERCE ΑΓΟΡΑ - AMAZON (REF: 12345)')
        self.assertAlmostEqual(result.iloc[2]['Amount'], -45.99)

    def test_process_card_operations_invalid_date(self):
        """Test processing card operations with invalid date format."""
        invalid_date_data = self.card_data.copy()
        invalid_date_data.iloc[0, 0] = 'Invalid date'
        
        with self.assertRaises(ValueError) as cm:
            process_card_operations(invalid_date_data)
        self.assertIn("Error processing card operations", str(cm.exception))

    def test_process_card_operations_missing_columns(self):
        """Test processing card operations with missing required columns."""
        missing_columns_data = pd.DataFrame({
            'Ημερομηνία/Ώρα Συναλλαγής': ['21/02/2025 10:00 μμ'],
            # Missing other required columns
        })
        
        with self.assertRaises(ValueError) as cm:
            process_card_operations(missing_columns_data)
        self.assertIn("Missing required columns", str(cm.exception))


class TestRevolutOperations(unittest.TestCase):
    """Tests for Revolut operations processing."""

    def setUp(self):
        """Set up test data."""
        self.revolut_data = pd.DataFrame({
            'Type': ['CARD_PAYMENT', 'TRANSFER'],
            'Started Date': ['2025-07-01 12:30:45', '2025-07-02 09:15:30'],
            'Description': ['Coffee Shop', 'From John'],
            'Amount': ['-4.50', '50.00'],
            'Fee': ['0.00', '0.00'],
            'State': ['COMPLETED', 'COMPLETED'],
            'Currency': ['EUR', 'EUR']
        })

    def test_validate_revolut_currency(self):
        """Test validating Revolut currency."""
        # Valid case - all EUR
        valid_data = self.revolut_data.copy()
        validate_revolut_currency(valid_data)
        
        # Invalid case - mixed currencies
        invalid_data = self.revolut_data.copy()
        invalid_data.loc[1, 'Currency'] = 'USD'
        
        with self.assertRaises(ValueError) as cm:
            validate_revolut_currency(invalid_data)
        self.assertIn("only contain EUR", str(cm.exception))

    def test_process_revolut_operations(self):
        """Test processing Revolut operations."""
        result = process_revolut_operations(self.revolut_data)
        
        # Check basic structure
        self.assertEqual(len(result), 2)
        self.assertListEqual(list(result.columns), ['Date', 'Payee', 'Memo', 'Amount'])
        
        # Check conversion of first row (debit)
        self.assertEqual(result.iloc[0]['Date'], '2025-07-01')
        self.assertEqual(result.iloc[0]['Payee'], 'Coffee Shop')
        self.assertEqual(result.iloc[0]['Memo'], 'CARD_PAYMENT')
        self.assertAlmostEqual(result.iloc[0]['Amount'], -4.50)
        
        # Check conversion of second row (credit)
        self.assertEqual(result.iloc[1]['Date'], '2025-07-02')
        self.assertEqual(result.iloc[1]['Payee'], 'From John')
        self.assertEqual(result.iloc[1]['Memo'], 'TRANSFER')
        self.assertAlmostEqual(result.iloc[1]['Amount'], 50.00)

    def test_process_revolut_operations_with_fee(self):
        """Test processing Revolut operations with fees."""
        fee_data = self.revolut_data.copy()
        fee_data.loc[2] = [
            'ATM_WITHDRAWAL',
            '2025-07-03 14:30:00',
            'ATM Withdrawal',
            '100.00',
            '2.50',  # Fee
            'COMPLETED',
            'EUR'
        ]
        
        result = process_revolut_operations(fee_data)
        
        # Check fee is subtracted from amount
        self.assertEqual(result.iloc[2]['Date'], '2025-07-03')
        self.assertEqual(result.iloc[2]['Payee'], 'ATM Withdrawal')
        self.assertEqual(result.iloc[2]['Memo'], 'ATM_WITHDRAWAL')
        self.assertAlmostEqual(result.iloc[2]['Amount'], 97.50)  # 100 - 2.50

    def test_process_revolut_operations_incomplete_state(self):
        """Test processing Revolut operations with non-COMPLETED state."""
        incomplete_data = self.revolut_data.copy()
        incomplete_data.loc[1, 'State'] = 'PENDING'
        
        result = process_revolut_operations(incomplete_data)
        
        # Only the COMPLETED transaction should remain
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['Payee'], 'Coffee Shop')

    def test_process_revolut_operations_missing_columns(self):
        """Test processing Revolut operations with missing required columns."""
        missing_columns_data = pd.DataFrame({
            'Type': ['CARD_PAYMENT'],
            'Started Date': ['2025-07-01 12:30:45'],
            # Missing other required columns
        })
        
        with self.assertRaises(ValueError) as cm:
            process_revolut_operations(missing_columns_data)
        self.assertIn("Missing required columns", str(cm.exception))


class TestTransactionExclusion(unittest.TestCase):
    """Tests for excluding existing transactions."""

    def setUp(self):
        """Set up test data."""
        self.new_transactions = pd.DataFrame({
            'Date': ['2025-07-01', '2025-07-02', '2025-07-03', '2025-07-04'],
            'Payee': ['Coffee Shop', 'Grocery Store', 'Restaurant', 'Gas Station'],
            'Memo': ['Coffee', 'Food', 'Dinner', 'Fuel'],
            'Amount': [-4.50, -65.30, -45.00, -35.75]
        })
        
        self.previous_transactions = pd.DataFrame({
            'Date': ['2025-07-01', '2025-07-03'],
            'Payee': ['Coffee Shop', 'Restaurant'],
            'Memo': ['Coffee', 'Dinner'],
            'Amount': [-4.50, -45.00]
        })

    def test_exclude_existing_transactions(self):
        """Test excluding existing transactions."""
        result = exclude_existing_transactions(self.new_transactions, self.previous_transactions)
        
        # Should exclude transactions that exist in previous_transactions
        self.assertEqual(len(result), 2)
        self.assertListEqual(list(result['Payee']), ['Grocery Store', 'Gas Station'])
        self.assertListEqual(list(result['Amount']), [-65.30, -35.75])

    def test_exclude_existing_case_insensitive(self):
        """Test excluding transactions with case-insensitive matching."""
        # Modify previous transactions to have different case
        case_insensitive_prev = self.previous_transactions.copy()
        case_insensitive_prev.loc[0, 'Payee'] = 'COFFEE SHOP'
        case_insensitive_prev.loc[0, 'Memo'] = 'COFFEE'
        
        result = exclude_existing_transactions(self.new_transactions, case_insensitive_prev)
        
        # Should still exclude the coffee shop transaction despite case difference
        self.assertEqual(len(result), 2)
        self.assertListEqual(list(result['Payee']), ['Grocery Store', 'Gas Station'])

    def test_exclude_existing_empty_previous(self):
        """Test excluding with empty previous transactions."""
        empty_prev = pd.DataFrame(columns=['Date', 'Payee', 'Memo', 'Amount'])
        
        result = exclude_existing_transactions(self.new_transactions, empty_prev)
        
        # Should return all transactions when previous is empty
        self.assertEqual(len(result), 4)
        self.assertListEqual(list(result['Payee']), ['Coffee Shop', 'Grocery Store', 'Restaurant', 'Gas Station'])

    def test_exclude_existing_all_match(self):
        """Test excluding when all transactions match."""
        all_match_prev = self.new_transactions.copy()
        
        result = exclude_existing_transactions(self.new_transactions, all_match_prev)
        
        # Should return empty DataFrame when all transactions match
        self.assertEqual(len(result), 0)


if __name__ == '__main__':
    unittest.main()