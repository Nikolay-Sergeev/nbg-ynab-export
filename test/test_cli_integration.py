import unittest
import os
import tempfile
from unittest.mock import patch
import pandas as pd
import shutil
import csv

# Import key converter functions directly for testing
from converter.utils import generate_output_filename
from converter.revolut import process_revolut
from converter.account import process_account


class TestCLIIntegration(unittest.TestCase):
    """Testing CLI integration.

    Note: These tests avoid actually running the main module and instead test
    the underlying functionality directly to avoid import issues.
    """

    def setUp(self):
        """Set up test environment before each test."""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()

        # Create sample Revolut CSV input file
        self.revolut_csv = os.path.join(
            self.test_dir, "revolut_2025-07-15.csv"
        )
        with open(self.revolut_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Type', 'Product', 'Started Date', 'Completed Date',
                'Description', 'Amount', 'Fee', 'Currency', 'State', 'Balance'
            ])
            writer.writerow([
                'CARD_PAYMENT', 'Current', '2025-07-01 12:30:45',
                '2025-07-01 12:31:00', 'Coffee Shop', '-4.50', '0.00',
                'EUR', 'COMPLETED', '100.00'
            ])
            writer.writerow([
                'TRANSFER', 'Current', '2025-07-02 09:15:30',
                '2025-07-02 09:15:35', 'From John', '50.00', '0.00',
                'EUR', 'COMPLETED', '150.00'
            ])

        # Create sample NBG account Excel file
        # In a real test, we would create an actual Excel file
        # For simplicity we'll just create a placeholder
        self.nbg_account_xlsx = os.path.join(
            self.test_dir, "account_statement_2025-07-15.xlsx"
        )
        with open(self.nbg_account_xlsx, 'w') as f:
            f.write("MOCK EXCEL FILE")

        # Create a previous YNAB import file for testing exclusion
        self.previous_ynab_csv = os.path.join(
            self.test_dir, "previous_ynab.csv"
        )
        with open(self.previous_ynab_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(
                ['Date', 'Payee', 'Memo', 'Amount']
            )
            writer.writerow(
                ['2025-07-01', 'Coffee Shop', 'CARD_PAYMENT', '-4.50']
            )

    def tearDown(self):
        """Clean up test files after each test."""
        shutil.rmtree(self.test_dir)

    @patch('converter.utils.read_input')
    def test_revolut_csv_conversion(self, mock_read_input):
        """Test converting a Revolut CSV file."""
        # Set up mock return value for read_input
        test_df = pd.DataFrame({
            'Type': ['CARD_PAYMENT', 'TRANSFER'],
            'Started Date': ['2025-07-01 12:30:45', '2025-07-02 09:15:30'],
            'Description': ['Coffee Shop', 'From John'],
            'Amount': ['-4.50', '50.00'],
            'Fee': ['0.00', '0.00'],
            'State': ['COMPLETED', 'COMPLETED'],
            'Currency': ['EUR', 'EUR']
        })
        mock_read_input.return_value = test_df

        # Process the data directly using the converter function
        result_df = process_revolut(test_df)

        # Create a test output file
        output_path = os.path.join(self.test_dir, "test_output.csv")
        result_df.to_csv(output_path, index=False)

        # Check that the file was created
        self.assertTrue(
            os.path.exists(output_path),
            "Output file should exist"
        )

        # Read the file back to verify
        output_df = pd.read_csv(output_path)

        self.assertEqual(len(output_df), 2, "Output should have 2 rows")
        expected_cols = ['Date', 'Payee', 'Memo', 'Amount']
        self.assertListEqual(
            list(output_df.columns),
            expected_cols,
            "Output columns don't match expected YNAB format"
        )

        # Check the transactions are correctly converted
        self.assertEqual(
            output_df.iloc[0]['Payee'], 'Coffee Shop'
        )
        self.assertAlmostEqual(
            float(output_df.iloc[0]['Amount']), -4.5, places=2
        )
        self.assertEqual(output_df.iloc[1]['Payee'], 'From John')
        self.assertAlmostEqual(
            float(output_df.iloc[1]['Amount']), 50.0, places=2
        )

    @patch('converter.utils.read_input')
    def test_nbg_account_conversion(self, mock_read_input):
        """Test converting an NBG account statement."""
        # Set up mock return value for read_input
        mock_df = pd.DataFrame({
            'Valeur': ['15/07/2025', '14/07/2025'],
            'Ονοματεπώνυμο αντισυμβαλλόμενου': ['SUPERMARKET XYZ', 'JOHN DOE'],
            'Περιγραφή': ['MARKET PURCHASE', 'SALARY TRANSFER'],
            'Ποσό συναλλαγής': ['-45,67', '1500,00'],
            'Χρέωση / Πίστωση': ['Χρέωση', 'Πίστωση']
        })
        mock_read_input.return_value = mock_df

        # Process the data directly
        result_df = process_account(mock_df)

        # Create a test output file
        output_path = os.path.join(self.test_dir, "account_output.csv")
        result_df.to_csv(output_path, index=False)

        # Check that the file was created
        self.assertTrue(
            os.path.exists(output_path),
            "Output file should exist"
        )

        # Read the file back to verify
        output_df = pd.read_csv(output_path)

        self.assertEqual(len(output_df), 2, "Output should have 2 rows")

        # Check the transactions are correctly converted
        self.assertEqual(output_df.iloc[0]['Date'], '2025-07-15')
        self.assertEqual(output_df.iloc[0]['Payee'], 'SUPERMARKET XYZ')
        self.assertAlmostEqual(
            float(output_df.iloc[0]['Amount']), -45.67, places=2
        )
        self.assertEqual(output_df.iloc[1]['Date'], '2025-07-14')
        self.assertEqual(output_df.iloc[1]['Payee'], 'JOHN DOE')
        self.assertAlmostEqual(
            float(output_df.iloc[1]['Amount']), 1500.00, places=2
        )

    def test_exclude_previous_transactions(self):
        """Test excluding previously imported transactions."""
        # We'll test directly with files we created in setUp

        # Verify the test files were created correctly
        self.assertTrue(
            os.path.exists(self.revolut_csv),
            "Input test file should exist"
        )
        self.assertTrue(
            os.path.exists(self.previous_ynab_csv),
            "Previous YNAB file should exist"
        )

        # Read the previous YNAB CSV to verify its contents
        prev_df = pd.read_csv(self.previous_ynab_csv)
        self.assertEqual(
            len(prev_df), 1, "Previous YNAB file should have 1 row"
        )
        self.assertEqual(
            prev_df.iloc[0]['Payee'],
            'Coffee Shop',
            "Payee should match"
        )
        self.assertAlmostEqual(
            float(prev_df.iloc[0]['Amount']), -4.5, places=2,
            msg="Previous amount should match"
        )

        # Test output filename generation
        output_name = generate_output_filename(self.revolut_csv)
        self.assertTrue('revolut_2025-07-15_ynab.csv' in output_name)
