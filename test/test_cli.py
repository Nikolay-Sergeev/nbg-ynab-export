import unittest
import os
import tempfile
import sys
import shutil
from unittest.mock import patch, MagicMock
from pathlib import Path
import pandas as pd

from cli import parse_args, main
from config import SUPPORTED_EXT


class TestCLIArgumentParsing(unittest.TestCase):
    """Test argument parsing in the CLI module."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        
        # Create test files
        self.valid_csv = os.path.join(self.test_dir, "statement.csv")
        open(self.valid_csv, 'w').close()
        
        self.valid_xlsx = os.path.join(self.test_dir, "statement.xlsx")
        open(self.valid_xlsx, 'w').close()
        
        self.previous_csv = os.path.join(self.test_dir, "previous.csv")
        open(self.previous_csv, 'w').close()
        
        self.invalid_ext = os.path.join(self.test_dir, "invalid.txt")
        open(self.invalid_ext, 'w').close()

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)

    def test_parse_args_with_input_only(self):
        """Test parsing arguments with only input file."""
        with patch('sys.argv', ['cli.py', self.valid_csv]):
            args = parse_args()
            self.assertEqual(args.input_file, Path(self.valid_csv))
            self.assertIsNone(args.previous)

    def test_parse_args_with_input_and_previous(self):
        """Test parsing arguments with input and previous file."""
        with patch('sys.argv', ['cli.py', self.valid_csv, '--previous', self.previous_csv]):
            args = parse_args()
            self.assertEqual(args.input_file, Path(self.valid_csv))
            self.assertEqual(args.previous, Path(self.previous_csv))

    def test_parse_args_with_short_flag(self):
        """Test parsing arguments with short flag for previous."""
        with patch('sys.argv', ['cli.py', self.valid_csv, '-p', self.previous_csv]):
            args = parse_args()
            self.assertEqual(args.input_file, Path(self.valid_csv))
            self.assertEqual(args.previous, Path(self.previous_csv))


class TestCLIMain(unittest.TestCase):
    """Test the main function in the CLI module."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        
        # Create test files
        self.valid_csv = os.path.join(self.test_dir, "statement.csv")
        open(self.valid_csv, 'w').close()
        
        self.valid_xlsx = os.path.join(self.test_dir, "statement.xlsx")
        open(self.valid_xlsx, 'w').close()
        
        self.previous_csv = os.path.join(self.test_dir, "previous.csv")
        open(self.previous_csv, 'w').close()
        
        self.invalid_ext = os.path.join(self.test_dir, "invalid.txt")
        open(self.invalid_ext, 'w').close()
        
        self.nonexistent_file = os.path.join(self.test_dir, "nonexistent.csv")

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)

    @patch('cli.parse_args')
    def test_main_invalid_file_path(self, mock_parse_args):
        """Test main function with nonexistent file."""
        args = MagicMock()
        args.input_file = Path(self.nonexistent_file)
        args.previous = None
        mock_parse_args.return_value = args
        
        result = main()
        self.assertEqual(result, 1, "Should return error code 1 for nonexistent file")

    @patch('cli.parse_args')
    def test_main_invalid_extension(self, mock_parse_args):
        """Test main function with invalid file extension."""
        args = MagicMock()
        args.input_file = Path(self.invalid_ext)
        args.previous = None
        mock_parse_args.return_value = args
        
        result = main()
        self.assertEqual(result, 1, "Should return error code 1 for invalid extension")

    @patch('cli.parse_args')
    @patch('cli.read_input')
    @patch('cli.process_revolut')
    @patch('cli.write_output')
    def test_main_revolut_detection(self, mock_write, mock_process, mock_read, mock_parse_args):
        """Test main function with Revolut input format detection."""
        args = MagicMock()
        args.input_file = Path(self.valid_csv)
        args.previous = None
        mock_parse_args.return_value = args
        
        # Mock Revolut DataFrame
        revolut_df = pd.DataFrame({
            'Type': ['CARD_PAYMENT'],
            'Started Date': ['2025-07-01'],
            'Description': ['Coffee Shop'],
            'Amount': ['-4.50'],
            'Fee': ['0.00'],
            'State': ['COMPLETED'],
            'Currency': ['EUR']
        })
        mock_read.return_value = revolut_df
        
        # Mock processed DataFrame
        result_df = pd.DataFrame({
            'Date': ['2025-07-01'],
            'Payee': ['Coffee Shop'],
            'Memo': ['CARD_PAYMENT'],
            'Amount': [-4.50]
        })
        mock_process.return_value = result_df
        
        # Mock output file path
        mock_write.return_value = os.path.join(self.test_dir, "output.csv")
        
        result = main()
        self.assertEqual(result, 0, "Should return success code 0")
        mock_process.assert_called_once_with(revolut_df)
        mock_write.assert_called_once()

    @patch('cli.parse_args')
    @patch('cli.read_input')
    @patch('cli.process_account')
    @patch('cli.write_output')
    def test_main_account_detection(self, mock_write, mock_process, mock_read, mock_parse_args):
        """Test main function with NBG Account input format detection."""
        args = MagicMock()
        args.input_file = Path(self.valid_csv)
        args.previous = None
        mock_parse_args.return_value = args
        
        # Mock Account DataFrame
        account_df = pd.DataFrame({
            'Valeur': ['15/07/2025'],
            'Ονοματεπώνυμο αντισυμβαλλόμενου': ['SUPERMARKET XYZ'],
            'Περιγραφή': ['MARKET PURCHASE'],
            'Ποσό συναλλαγής': ['-45,67'],
            'Χρέωση / Πίστωση': ['Χρέωση']
        })
        mock_read.return_value = account_df
        
        # Mock processed DataFrame
        result_df = pd.DataFrame({
            'Date': ['2025-07-15'],
            'Payee': ['SUPERMARKET XYZ'],
            'Memo': ['MARKET PURCHASE'],
            'Amount': [-45.67]
        })
        mock_process.return_value = result_df
        
        # Mock output file path
        mock_write.return_value = os.path.join(self.test_dir, "output.csv")
        
        result = main()
        self.assertEqual(result, 0, "Should return success code 0")
        mock_process.assert_called_once_with(account_df)
        mock_write.assert_called_once()

    @patch('cli.parse_args')
    @patch('cli.read_input')
    @patch('cli.process_card')
    @patch('cli.write_output')
    def test_main_card_detection(self, mock_write, mock_process, mock_read, mock_parse_args):
        """Test main function with NBG Card input format detection."""
        args = MagicMock()
        args.input_file = Path(self.valid_csv)
        args.previous = None
        mock_parse_args.return_value = args
        
        # Mock Card DataFrame
        card_df = pd.DataFrame({
            'Ημερομηνία/Ώρα Συναλλαγής': ['21/2/2025 10:00 μμ'],
            'Περιγραφή Κίνησης': ['E-COMMERCE ΑΓΟΡΑ - SHOP.EXAMPLE.COM'],
            'Ποσό': ['12,34'],
            'Χ/Π': ['Χ']
        })
        mock_read.return_value = card_df
        
        # Mock processed DataFrame
        result_df = pd.DataFrame({
            'Date': ['2025-02-21'],
            'Payee': ['SHOP.EXAMPLE.COM'],
            'Memo': ['E-COMMERCE ΑΓΟΡΑ'],
            'Amount': [-12.34]
        })
        mock_process.return_value = result_df
        
        # Mock output file path
        mock_write.return_value = os.path.join(self.test_dir, "output.csv")
        
        result = main()
        self.assertEqual(result, 0, "Should return success code 0")
        mock_process.assert_called_once_with(card_df)
        mock_write.assert_called_once()

    @patch('cli.parse_args')
    @patch('cli.read_input')
    def test_main_unrecognized_format(self, mock_read, mock_parse_args):
        """Test main function with unrecognized input format."""
        args = MagicMock()
        args.input_file = Path(self.valid_csv)
        args.previous = None
        mock_parse_args.return_value = args
        
        # Mock DataFrame with unrecognized columns
        unrecognized_df = pd.DataFrame({
            'Column1': ['Value1'],
            'Column2': ['Value2'],
            'Column3': ['Value3']
        })
        mock_read.return_value = unrecognized_df
        
        result = main()
        self.assertEqual(result, 1, "Should return error code 1 for unrecognized format")

    @patch('cli.parse_args')
    @patch('cli.read_input')
    @patch('cli.process_revolut')
    @patch('cli.exclude_existing')
    @patch('cli.write_output')
    def test_main_with_previous_file(self, mock_write, mock_exclude, mock_process, mock_read, mock_parse_args):
        """Test main function with previous YNAB file for exclusion."""
        args = MagicMock()
        args.input_file = Path(self.valid_csv)
        args.previous = Path(self.previous_csv)
        mock_parse_args.return_value = args
        
        # Mock Revolut DataFrame
        revolut_df = pd.DataFrame({
            'Type': ['CARD_PAYMENT', 'TRANSFER'],
            'Started Date': ['2025-07-01', '2025-07-02'],
            'Description': ['Coffee Shop', 'From John'],
            'Amount': ['-4.50', '50.00'],
            'Fee': ['0.00', '0.00'],
            'State': ['COMPLETED', 'COMPLETED'],
            'Currency': ['EUR', 'EUR']
        })
        mock_read.side_effect = [revolut_df, pd.DataFrame()]
        
        # Mock processed DataFrame
        processed_df = pd.DataFrame({
            'Date': ['2025-07-01', '2025-07-02'],
            'Payee': ['Coffee Shop', 'From John'],
            'Memo': ['CARD_PAYMENT', 'TRANSFER'],
            'Amount': [-4.50, 50.00]
        })
        mock_process.return_value = processed_df
        
        # Mock excluded DataFrame
        excluded_df = pd.DataFrame({
            'Date': ['2025-07-02'],
            'Payee': ['From John'],
            'Memo': ['TRANSFER'],
            'Amount': [50.00]
        })
        mock_exclude.return_value = excluded_df
        
        # Mock output file path
        mock_write.return_value = os.path.join(self.test_dir, "output.csv")
        
        result = main()
        self.assertEqual(result, 0, "Should return success code 0")
        mock_process.assert_called_once_with(revolut_df)
        mock_exclude.assert_called_once()
        mock_write.assert_called_once()

    @patch('cli.parse_args')
    @patch('cli.read_input')
    def test_main_exception_handling(self, mock_read, mock_parse_args):
        """Test main function exception handling."""
        args = MagicMock()
        args.input_file = Path(self.valid_csv)
        args.previous = None
        mock_parse_args.return_value = args
        
        # Mock read_input to raise an exception
        mock_read.side_effect = Exception("Test exception")
        
        result = main()
        self.assertEqual(result, 1, "Should return error code 1 for exceptions")


if __name__ == '__main__':
    unittest.main()