import unittest
import os
import sys
import tempfile
import pandas as pd
import csv
from unittest.mock import patch, mock_open, MagicMock
import logging

# Add the parent directory to sys.path to import main module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import (
    convert_nbg_to_ynab,
    validate_input_file,
    load_previous_transactions,
    validate_revolut_currency,
    SUPPORTED_EXTENSIONS,
    ACCOUNT_REQUIRED_COLUMNS,
    CARD_REQUIRED_COLUMNS,
    REVOLUT_REQUIRED_COLUMNS
)


class TestMainConversion(unittest.TestCase):
    """Test the main conversion function and its error handling paths."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        
        # Create valid test files
        self.valid_xlsx = os.path.join(self.test_dir, "valid.xlsx")
        self.valid_csv = os.path.join(self.test_dir, "valid.csv")
        self.previous_csv = os.path.join(self.test_dir, "previous.csv")
        
        # Create invalid test files
        self.invalid_ext = os.path.join(self.test_dir, "invalid.txt")
        self.nonexistent_file = os.path.join(self.test_dir, "nonexistent.xlsx")

        # Create empty test files
        open(self.valid_xlsx, 'w').close()
        open(self.valid_csv, 'w').close()
        open(self.previous_csv, 'w').close()
        open(self.invalid_ext, 'w').close()

        # Set up mock dataframes
        self.mock_account_df = pd.DataFrame({
            'Valeur': ['15/07/2025', '14/07/2025'],
            'Ονοματεπώνυμο αντισυμβαλλόμενου': ['SUPERMARKET XYZ', 'JOHN DOE'],
            'Περιγραφή': ['MARKET PURCHASE', 'SALARY TRANSFER'],
            'Ποσό συναλλαγής': ['45,67', '1500,00'],
            'Χρέωση / Πίστωση': ['Χρέωση', 'Πίστωση']
        })
        
        self.mock_card_df = pd.DataFrame({
            'Ημερομηνία/Ώρα Συναλλαγής': ['21/2/2025 10:00 μμ', '14/2/2025 4:51 μμ'],
            'Περιγραφή Κίνησης': ['E-COMMERCE ΑΓΟΡΑ - SHOP.EXAMPLE.COM', 'ΦΟΡΤΙΣΗ'],
            'Χ/Π': ['Χ', 'Π'],
            'Ποσό': ['12,34', '100,00']
        })
        
        self.mock_revolut_df = pd.DataFrame({
            'Type': ['CARD_PAYMENT', 'TRANSFER'],
            'Started Date': ['2025-07-01', '2025-07-02'],
            'Description': ['Coffee Shop', 'From John'],
            'Amount': ['-4.50', '50.00'],
            'Fee': ['0.00', '0.00'],
            'State': ['COMPLETED', 'COMPLETED'],
            'Currency': ['EUR', 'EUR']
        })
        
        self.mock_prev_df = pd.DataFrame({
            'Date': ['2025-07-01'],
            'Payee': ['Coffee Shop'],
            'Memo': ['CARD_PAYMENT'],
            'Amount': [-4.50]
        })
        
        # Output of conversion
        self.expected_ynab_df = pd.DataFrame({
            'Date': ['2025-07-01', '2025-07-02'],
            'Payee': ['Coffee Shop', 'From John'],
            'Memo': ['CARD_PAYMENT', 'TRANSFER'],
            'Amount': [-4.50, 50.00]
        })
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove test directory and files
        import shutil
        shutil.rmtree(self.test_dir)
    
    @patch('main.validate_input_file')
    @patch('main.pd.read_excel')
    @patch('main.process_account_operations')
    @patch('main.generate_output_filename')
    @patch('main.pd.DataFrame.to_csv')
    def test_convert_nbg_to_ynab_excel_account(
        self, mock_to_csv, mock_gen_output, mock_process, mock_read_excel, mock_validate
    ):
        """Test converting NBG Excel account statement to YNAB."""
        # Setup mocks
        mock_read_excel.return_value = self.mock_account_df
        mock_process.return_value = self.expected_ynab_df
        mock_gen_output.return_value = os.path.join(self.test_dir, "output.csv")
        
        # Run the function
        result = convert_nbg_to_ynab(self.valid_xlsx)
        
        # Verify the function calls
        mock_validate.assert_called_once_with(self.valid_xlsx)
        mock_read_excel.assert_called_once_with(self.valid_xlsx)
        mock_process.assert_called_once()
        mock_gen_output.assert_called_once()
        mock_to_csv.assert_called_once()
        
        # Verify the result
        pd.testing.assert_frame_equal(result, self.expected_ynab_df)
    
    @patch('main.validate_input_file')
    @patch('main.pd.read_csv')
    @patch('main.process_revolut_operations')
    @patch('main.generate_output_filename')
    @patch('main.pd.DataFrame.to_csv')
    def test_convert_nbg_to_ynab_csv_revolut(
        self, mock_to_csv, mock_gen_output, mock_process, mock_read_csv, mock_validate
    ):
        """Test converting Revolut CSV statement to YNAB."""
        # Setup mocks
        mock_read_csv.return_value = self.mock_revolut_df
        mock_process.return_value = self.expected_ynab_df
        mock_gen_output.return_value = os.path.join(self.test_dir, "output.csv")
        
        # Run the function
        result = convert_nbg_to_ynab(self.valid_csv)
        
        # Verify the function calls
        mock_validate.assert_called_once_with(self.valid_csv)
        mock_read_csv.assert_called_once_with(self.valid_csv)
        mock_process.assert_called_once()
        mock_gen_output.assert_called_once()
        mock_to_csv.assert_called_once()
        
        # Verify the result
        pd.testing.assert_frame_equal(result, self.expected_ynab_df)
    
    @patch('main.validate_input_file')
    @patch('main.pd.read_excel')
    @patch('main.process_card_operations')
    @patch('main.generate_output_filename')
    @patch('main.pd.DataFrame.to_csv')
    def test_convert_nbg_to_ynab_excel_card(
        self, mock_to_csv, mock_gen_output, mock_process, mock_read_excel, mock_validate
    ):
        """Test converting NBG Excel card statement to YNAB."""
        # Setup mocks
        mock_read_excel.return_value = self.mock_card_df
        mock_process.return_value = self.expected_ynab_df
        mock_gen_output.return_value = os.path.join(self.test_dir, "output.csv")
        
        # Run the function
        result = convert_nbg_to_ynab(self.valid_xlsx)
        
        # Verify the function calls
        mock_validate.assert_called_once_with(self.valid_xlsx)
        mock_read_excel.assert_called_once_with(self.valid_xlsx)
        mock_process.assert_called_once()
        mock_gen_output.assert_called_once()
        mock_to_csv.assert_called_once()
        
        # Verify the result
        pd.testing.assert_frame_equal(result, self.expected_ynab_df)
    
    @patch('main.validate_input_file')
    @patch('main.pd.read_excel')
    @patch('main.load_previous_transactions')
    @patch('main.exclude_existing_transactions')
    @patch('main.process_account_operations')
    @patch('main.generate_output_filename')
    @patch('main.pd.DataFrame.to_csv')
    def test_convert_nbg_to_ynab_with_previous(
        self, mock_to_csv, mock_gen_output, mock_process, mock_exclude, 
        mock_load_prev, mock_read_excel, mock_validate
    ):
        """Test converting NBG statement with previous transactions exclusion."""
        # Setup mocks
        mock_read_excel.return_value = self.mock_account_df
        mock_process.return_value = self.expected_ynab_df
        mock_load_prev.return_value = self.mock_prev_df
        mock_exclude.return_value = pd.DataFrame({
            'Date': ['2025-07-02'],
            'Payee': ['From John'],
            'Memo': ['TRANSFER'],
            'Amount': [50.00]
        })
        mock_gen_output.return_value = os.path.join(self.test_dir, "output.csv")
        
        # Run the function
        result = convert_nbg_to_ynab(self.valid_xlsx, self.previous_csv)
        
        # Verify the function calls
        mock_validate.assert_called_once_with(self.valid_xlsx)
        mock_read_excel.assert_called_once_with(self.valid_xlsx)
        mock_process.assert_called_once()
        mock_load_prev.assert_called_once_with(self.previous_csv)
        mock_exclude.assert_called_once()
        mock_gen_output.assert_called_once()
        mock_to_csv.assert_called_once()
        
        # Verify the result (should be the filtered DataFrame)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['Payee'], 'From John')
    
    @patch('main.validate_input_file', side_effect=FileNotFoundError("File not found"))
    @patch('main.logging.error')
    def test_convert_nbg_to_ynab_file_not_found(self, mock_log_error, mock_validate):
        """Test error handling for non-existent file."""
        # Run the function and expect FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            convert_nbg_to_ynab(self.nonexistent_file)

        # Check function calls
        mock_validate.assert_called_once_with(self.nonexistent_file)
        mock_log_error.assert_called_once()
    
    @patch('main.validate_input_file')
    @patch('main.pd.read_excel', side_effect=ValueError("Empty file"))
    @patch('main.logging.error')
    def test_convert_nbg_to_ynab_empty_file(self, mock_log_error, mock_read_excel, mock_validate):
        """Test error handling for empty file."""
        # Run the function and expect ValueError
        with self.assertRaises(ValueError):
            convert_nbg_to_ynab(self.valid_xlsx)

        # Check function calls
        mock_validate.assert_called_once_with(self.valid_xlsx)
        mock_read_excel.assert_called_once_with(self.valid_xlsx)

        # It's called twice - once with 'Failed to read Excel file' and once with 'Validation error'
        self.assertEqual(mock_log_error.call_count, 2)
    
    @patch('main.validate_input_file')
    @patch('main.pd.read_excel')
    @patch('main.logging.error')
    def test_convert_nbg_to_ynab_unrecognized_format(self, mock_log_error, mock_read_excel, mock_validate):
        """Test error handling for unrecognized format."""
        # Setup mock to return DataFrame with unknown columns
        mock_read_excel.return_value = pd.DataFrame({
            'Column1': [1, 2],
            'Column2': ['a', 'b']
        })
        
        # Run the function and expect ValueError
        with self.assertRaises(ValueError):
            convert_nbg_to_ynab(self.valid_xlsx)

        # Check function calls
        mock_validate.assert_called_once_with(self.valid_xlsx)
        mock_read_excel.assert_called_once_with(self.valid_xlsx)
        mock_log_error.assert_called_once()
    
    def test_validate_input_file_nonexistent(self):
        """Test validating a non-existent file."""
        with self.assertRaises(FileNotFoundError):
            validate_input_file(self.nonexistent_file)
    
    def test_validate_input_file_unsupported_extension(self):
        """Test validating a file with unsupported extension."""
        with self.assertRaises(ValueError) as context:
            validate_input_file(self.invalid_ext)
        self.assertIn("Unsupported file type", str(context.exception))
    
    def test_validate_input_file_supported_extensions(self):
        """Test validating files with supported extensions."""
        # These should not raise exceptions
        validate_input_file(self.valid_xlsx)
        validate_input_file(self.valid_csv)
    
    @patch('main.pd.read_csv')
    def test_load_previous_transactions(self, mock_read_csv):
        """Test loading previous transactions."""
        # Setup mock
        mock_read_csv.return_value = self.mock_prev_df
        
        # Run the function
        result = load_previous_transactions(self.previous_csv)
        
        # Check function calls
        mock_read_csv.assert_called_once_with(self.previous_csv)
        
        # Check the result
        pd.testing.assert_frame_equal(result, self.mock_prev_df)
    
    @patch('main.pd.read_csv', side_effect=Exception("CSV error"))
    @patch('main.logging.warning')
    def test_load_previous_transactions_error(self, mock_log_warning, mock_read_csv):
        """Test error handling when loading previous transactions fails."""
        # The function should not raise an error but return an empty DataFrame
        result = load_previous_transactions(self.previous_csv)
        
        # Check that a warning was logged
        mock_log_warning.assert_called_once()
        self.assertIn("Could not load previous transactions", mock_log_warning.call_args[0][0])
        
        # Verify that an empty DataFrame with the expected columns was returned
        self.assertTrue(result.empty)
        self.assertEqual(list(result.columns), ['Date', 'Payee', 'Memo', 'Amount'])
    
    def test_validate_revolut_currency_valid(self):
        """Test validating Revolut currency with all EUR transactions."""
        # This should not raise an exception
        validate_revolut_currency(self.mock_revolut_df)
    
    def test_validate_revolut_currency_invalid(self):
        """Test validating Revolut currency with non-EUR transactions."""
        # Create DataFrame with non-EUR transactions
        invalid_df = self.mock_revolut_df.copy()
        invalid_df.loc[1, 'Currency'] = 'USD'
        
        with self.assertRaises(ValueError) as context:
            validate_revolut_currency(invalid_df)
        self.assertIn("only contain EUR", str(context.exception))


class TestEdgeCases(unittest.TestCase):
    """Test file format edge cases."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        
        # Create test files
        self.minimal_csv = os.path.join(self.test_dir, "minimal.csv")
        self.invalid_date_csv = os.path.join(self.test_dir, "invalid_date.csv")
        self.empty_csv = os.path.join(self.test_dir, "empty.csv")
        self.mixed_currency_csv = os.path.join(self.test_dir, "mixed_currency.csv")

        # Create placeholder files to satisfy validation
        open(self.invalid_date_csv, "w").close()
        open(self.empty_csv, "w").close()
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove test directory and files
        import shutil
        shutil.rmtree(self.test_dir)
    
    @patch('main.process_revolut_operations')
    def test_minimal_valid_revolut_csv(self, mock_process):
        """Test processing a minimal valid Revolut CSV."""
        # Create minimal Revolut CSV with just the required columns
        minimal_df = pd.DataFrame({
            'Type': ['CARD_PAYMENT'],
            'Started Date': ['2025-07-01'],
            'Description': ['Coffee Shop'],
            'Amount': ['-4.50'],
            'Fee': ['0.00'],
            'State': ['COMPLETED'],
            'Currency': ['EUR']
        })
        minimal_df.to_csv(self.minimal_csv, index=False)
        
        # Setup mock
        mock_process.return_value = pd.DataFrame({
            'Date': ['2025-07-01'],
            'Payee': ['Coffee Shop'],
            'Memo': ['CARD_PAYMENT'],
            'Amount': [-4.50]
        })
        
        # Run the conversion
        with patch('main.pd.read_csv', return_value=minimal_df):
            result = convert_nbg_to_ynab(self.minimal_csv)
        
        # Check that the process function was called with correct data
        mock_process.assert_called_once()
        self.assertIsNotNone(result)
    
    @patch('main.process_account_operations')
    @patch('main.pd.read_csv')
    @patch('main.logging.error')
    def test_invalid_date_format(self, mock_log_error, mock_read_csv, mock_process):
        """Test handling of invalid date format."""
        # Create account data with invalid date
        invalid_date_df = pd.DataFrame({
            'Valeur': ['invalid-date', '14/07/2025'],
            'Ονοματεπώνυμο αντισυμβαλλόμενου': ['SUPERMARKET XYZ', 'JOHN DOE'],
            'Περιγραφή': ['MARKET PURCHASE', 'SALARY TRANSFER'],
            'Ποσό συναλλαγής': ['45,67', '1500,00'],
            'Χρέωση / Πίστωση': ['Χρέωση', 'Πίστωση']
        })
        mock_read_csv.return_value = invalid_date_df
        
        # Make process_account_operations raise ValueError for invalid date
        mock_process.side_effect = ValueError("Invalid date format")
        
        # Run the conversion expecting ValueError
        with self.assertRaises(ValueError):
            convert_nbg_to_ynab(self.invalid_date_csv)

        # Check that error was logged
        mock_log_error.assert_called_once()
    
    @patch('main.pd.read_csv')
    @patch('main.logging.error')
    def test_empty_dataframe(self, mock_log_error, mock_read_csv):
        """Test handling of empty DataFrame."""
        # Create empty DataFrame
        empty_df = pd.DataFrame()
        mock_read_csv.return_value = empty_df
        
        # Run the conversion expecting ValueError
        with self.assertRaises(ValueError):
            convert_nbg_to_ynab(self.empty_csv)

        # Check that error was logged
        mock_log_error.assert_called_once()


if __name__ == '__main__':
    unittest.main()