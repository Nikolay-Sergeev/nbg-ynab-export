import unittest
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pandas as pd
import shutil
import csv
import re

# Import from main module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCLIIntegration(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        
        # Create sample Revolut CSV input file
        self.revolut_csv = os.path.join(self.test_dir, "revolut_2025-07-15.csv")
        with open(self.revolut_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Type', 'Product', 'Started Date', 'Completed Date', 
                'Description', 'Amount', 'Fee', 'Currency', 'State', 'Balance'
            ])
            writer.writerow([
                'CARD_PAYMENT', 'Current', '2025-07-01 12:30:45', '2025-07-01 12:31:00',
                'Coffee Shop', '-4.50', '0.00', 'EUR', 'COMPLETED', '100.00'
            ])
            writer.writerow([
                'TRANSFER', 'Current', '2025-07-02 09:15:30', '2025-07-02 09:15:35',
                'From John', '50.00', '0.00', 'EUR', 'COMPLETED', '150.00'
            ])
        
        # Create sample NBG account Excel file
        # In a real test, we would create an actual Excel file, but for simplicity
        # we'll just create a placeholder and patch the read_input function
        self.nbg_account_xlsx = os.path.join(self.test_dir, "account_statement_2025-07-15.xlsx")
        with open(self.nbg_account_xlsx, 'w') as f:
            f.write("MOCK EXCEL FILE")
        
        # Create a previous YNAB import file for testing exclusion
        self.previous_ynab_csv = os.path.join(self.test_dir, "previous_ynab.csv")
        with open(self.previous_ynab_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Date', 'Payee', 'Memo', 'Amount'])
            writer.writerow(['2025-07-01', 'Coffee Shop', 'CARD_PAYMENT', '-4.50'])
    
    def tearDown(self):
        """Clean up test files after each test."""
        shutil.rmtree(self.test_dir)
    
    @patch('converter.utils.read_input')
    def test_revolut_csv_conversion(self, mock_read_input):
        """Test converting a Revolut CSV file."""
        # Set up mock return value for read_input
        mock_df = pd.DataFrame({
            'Type': ['CARD_PAYMENT', 'TRANSFER'],
            'Started Date': ['2025-07-01 12:30:45', '2025-07-02 09:15:30'],
            'Description': ['Coffee Shop', 'From John'],
            'Amount': ['-4.50', '50.00'],
            'Fee': ['0.00', '0.00'],
            'State': ['COMPLETED', 'COMPLETED'],
            'Currency': ['EUR', 'EUR']
        })
        mock_read_input.return_value = mock_df
        
        # Import main here to avoid module-level patching issues
        import main
        
        # Run the conversion
        with patch.object(sys, 'argv', ['main.py', self.revolut_csv]):
            main.main()
        
        # Check if output file was created
        expected_output_pattern = f"{self.test_dir}/revolut_2025-07-15_.*_ynab.csv"
        output_files = [f for f in os.listdir(self.test_dir) if re.match(r'.*_ynab\.csv$', f)]
        self.assertTrue(any(output_files), "No output file was created")
        
        # Check the contents of the first output file
        output_path = os.path.join(self.test_dir, output_files[0])
        output_df = pd.read_csv(output_path)
        
        self.assertEqual(len(output_df), 2, "Output should have 2 rows")
        self.assertListEqual(list(output_df.columns), ['Date', 'Payee', 'Memo', 'Amount'], 
                            "Output columns don't match expected YNAB format")
        
        # Check the transactions are correctly converted
        self.assertEqual(output_df.iloc[0]['Payee'], 'Coffee Shop')
        self.assertEqual(output_df.iloc[0]['Amount'], -4.50)
        self.assertEqual(output_df.iloc[1]['Payee'], 'From John')
        self.assertEqual(output_df.iloc[1]['Amount'], 50.0)
    
    @patch('converter.utils.read_input')
    @patch('main.validate_input_file')  # Skip validation since we're using mock files
    def test_nbg_account_conversion(self, mock_validate, mock_read_input):
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
        mock_validate.return_value = True
        
        # Import main here to avoid module-level patching issues
        import main
        
        # Run the conversion
        with patch.object(sys, 'argv', ['main.py', self.nbg_account_xlsx]):
            main.main()
        
        # Check if output file was created
        expected_output = f"account_statement_2025-07-15_ynab.csv"
        output_files = [f for f in os.listdir(self.test_dir) if f.endswith('_ynab.csv')]
        self.assertTrue(any(output_files), "No output file was created")
        
        # Check the contents of the output file
        output_path = os.path.join(self.test_dir, output_files[0])
        output_df = pd.read_csv(output_path)
        
        self.assertEqual(len(output_df), 2, "Output should have 2 rows")
        
        # Check the transactions are correctly converted
        self.assertEqual(output_df.iloc[0]['Date'], '2025-07-15')
        self.assertEqual(output_df.iloc[0]['Payee'], 'SUPERMARKET XYZ')
        self.assertEqual(output_df.iloc[0]['Amount'], -45.67)
        self.assertEqual(output_df.iloc[1]['Date'], '2025-07-14')
        self.assertEqual(output_df.iloc[1]['Payee'], 'JOHN DOE')
        self.assertEqual(output_df.iloc[1]['Amount'], 1500.00)
    
    @patch('converter.utils.read_input')
    def test_exclude_previous_transactions(self, mock_read_input):
        """Test excluding previously imported transactions."""
        # Set up mock return values for read_input
        # First call for the new statement
        mock_df1 = pd.DataFrame({
            'Type': ['CARD_PAYMENT', 'TRANSFER', 'CARD_PAYMENT'],
            'Started Date': ['2025-07-01 12:30:45', '2025-07-02 09:15:30', '2025-07-03 14:25:10'],
            'Description': ['Coffee Shop', 'From John', 'Grocery Store'],
            'Amount': ['-4.50', '50.00', '-35.75'],
            'Fee': ['0.00', '0.00', '0.00'],
            'State': ['COMPLETED', 'COMPLETED', 'COMPLETED'],
            'Currency': ['EUR', 'EUR', 'EUR']
        })
        # Second call for the previous YNAB export
        mock_df2 = pd.DataFrame({
            'Date': ['2025-07-01'],
            'Payee': ['Coffee Shop'],
            'Memo': ['CARD_PAYMENT'],
            'Amount': [-4.5]
        })
        mock_read_input.side_effect = [mock_df1, mock_df2]
        
        # Import main here to avoid module-level patching issues
        import main
        
        # Run the conversion with previous transactions
        with patch.object(sys, 'argv', ['main.py', self.revolut_csv, self.previous_ynab_csv]):
            main.main()
        
        # Check if output file was created
        output_files = [f for f in os.listdir(self.test_dir) if f.endswith('_ynab.csv') 
                       and not f.startswith('previous')]
        self.assertTrue(any(output_files), "No output file was created")
        
        # Check the contents of the output file
        output_path = os.path.join(self.test_dir, output_files[0])
        output_df = pd.read_csv(output_path)
        
        # Should have 2 transactions (Coffee Shop was excluded)
        self.assertEqual(len(output_df), 2, "Output should have 2 rows (1 excluded)")
        
        # Verify Coffee Shop transaction is excluded
        self.assertFalse(any(output_df['Payee'] == 'Coffee Shop'), 
                        "Coffee Shop transaction should be excluded")
        
        # Verify other transactions are present
        self.assertTrue(any(output_df['Payee'] == 'From John'), 
                       "From John transaction should be included")
        self.assertTrue(any(output_df['Payee'] == 'Grocery Store'), 
                       "Grocery Store transaction should be included")


if __name__ == '__main__':
    unittest.main(verbosity=2)