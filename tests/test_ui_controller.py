import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from config import DUP_CHECK_DAYS, DUP_CHECK_COUNT
import pandas as pd
import os
import tempfile

from services.actual_client import ActualClient
from ui.controller import (
    BudgetFetchWorker,
    AccountFetchWorker,
    TransactionFetchWorker,
    DuplicateCheckWorker,
    UploadWorker
)


class TestBudgetFetchWorker(unittest.TestCase):
    """Test the BudgetFetchWorker class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_ynab_client = MagicMock()
        self.worker = BudgetFetchWorker(self.mock_ynab_client)

        # Connect to signals for testing
        self.finished_signal_data = None
        self.error_signal_message = None
        
        self.worker.finished.connect(self.handle_finished)
        self.worker.error.connect(self.handle_error)
        # Default mock to YNAB-style signature; tests can override per-case
        self.mock_ynab_client.upload_transactions.side_effect = None

    def handle_finished(self, data):
        """Handler for finished signal."""
        self.finished_signal_data = data

    def handle_error(self, message):
        """Handler for error signal."""
        self.error_signal_message = message

    def test_run_success(self):
        """Test successful budget fetch."""
        # Prepare mock data
        mock_budgets = [
            {"id": "budget1", "name": "Budget One"},
            {"id": "budget2", "name": "Budget Two"}
        ]
        self.mock_ynab_client.get_budgets.return_value = mock_budgets
        
        # Run the worker
        self.worker.run()
        
        # Check if the client method was called
        self.mock_ynab_client.get_budgets.assert_called_once()
        
        # Check if signal emitted correct data
        self.assertEqual(self.finished_signal_data, mock_budgets)
        self.assertIsNone(self.error_signal_message)

    def test_run_failure(self):
        """Test budget fetch failure."""
        # Simulate an exception
        self.mock_ynab_client.get_budgets.side_effect = Exception("API error")
        
        # Run the worker
        self.worker.run()
        
        # Check if the client method was called
        self.mock_ynab_client.get_budgets.assert_called_once()
        
        # Check if error signal was emitted
        self.assertIsNone(self.finished_signal_data)
        self.assertIn("Failed to fetch budgets", self.error_signal_message)
        self.assertIn("API error", self.error_signal_message)


class TestAccountFetchWorker(unittest.TestCase):
    """Test the AccountFetchWorker class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_ynab_client = MagicMock()
        self.budget_id = "test_budget_id"
        self.worker = AccountFetchWorker(self.mock_ynab_client, self.budget_id)

        # Connect to signals for testing
        self.finished_signal_data = None
        self.error_signal_message = None
        
        self.worker.finished.connect(self.handle_finished)
        self.worker.error.connect(self.handle_error)

    def handle_finished(self, data):
        """Handler for finished signal."""
        self.finished_signal_data = data

    def handle_error(self, message):
        """Handler for error signal."""
        self.error_signal_message = message

    def test_run_success(self):
        """Test successful account fetch."""
        # Prepare mock data
        mock_accounts = [
            {"id": "account1", "name": "Checking"},
            {"id": "account2", "name": "Savings"}
        ]
        self.mock_ynab_client.get_accounts.return_value = mock_accounts
        
        # Run the worker
        self.worker.run()
        
        # Check if the client method was called with correct budget ID
        self.mock_ynab_client.get_accounts.assert_called_once_with(self.budget_id)
        
        # Check if signal emitted correct data
        self.assertEqual(self.finished_signal_data, mock_accounts)
        self.assertIsNone(self.error_signal_message)

    def test_run_failure(self):
        """Test account fetch failure."""
        # Simulate an exception
        self.mock_ynab_client.get_accounts.side_effect = Exception("API error")
        
        # Run the worker
        self.worker.run()
        
        # Check if the client method was called
        self.mock_ynab_client.get_accounts.assert_called_once_with(self.budget_id)
        
        # Check if error signal was emitted
        self.assertIsNone(self.finished_signal_data)
        self.assertIn("Failed to fetch accounts", self.error_signal_message)
        self.assertIn("API error", self.error_signal_message)


class TestTransactionFetchWorker(unittest.TestCase):
    """Test the TransactionFetchWorker class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_ynab_client = MagicMock()
        self.budget_id = "test_budget_id"
        self.account_id = "test_account_id"
        self.worker = TransactionFetchWorker(
            self.mock_ynab_client, 
            self.budget_id,
            self.account_id,
            count=None,
            since_date=None,
        )

        # Connect to signals for testing
        self.finished_signal_data = None
        self.error_signal_message = None
        
        self.worker.finished.connect(self.handle_finished)
        self.worker.error.connect(self.handle_error)

    def handle_finished(self, data):
        """Handler for finished signal."""
        self.finished_signal_data = data

    def handle_error(self, message):
        """Handler for error signal."""
        self.error_signal_message = message

    def test_run_success(self):
        """Test successful transaction fetch."""
        # Prepare mock data
        mock_transactions = [
            {"id": "txn1", "amount": -4500, "date": "2025-07-01"},
            {"id": "txn2", "amount": 10000, "date": "2025-07-02"}
        ]
        self.mock_ynab_client.get_transactions.return_value = mock_transactions
        
        # Run the worker
        self.worker.run()
        
        # Check if the client method was called with correct IDs
        self.mock_ynab_client.get_transactions.assert_called_once_with(
            self.budget_id, self.account_id, count=None, since_date=None
        )
        
        # Check if signal emitted correct data
        self.assertEqual(self.finished_signal_data, mock_transactions)
        self.assertIsNone(self.error_signal_message)

    def test_run_failure(self):
        """Test transaction fetch failure."""
        # Simulate an exception
        self.mock_ynab_client.get_transactions.side_effect = Exception("API error")
        
        # Run the worker
        self.worker.run()
        
        # Check if the client method was called
        self.mock_ynab_client.get_transactions.assert_called_once_with(
            self.budget_id, self.account_id, count=None, since_date=None
        )
        
        # Check if error signal was emitted
        self.assertIsNone(self.finished_signal_data)
        self.assertIn("Failed to fetch transactions", self.error_signal_message)
        self.assertIn("API error", self.error_signal_message)


class TestDuplicateCheckWorker(unittest.TestCase):
    """Test the DuplicateCheckWorker class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_converter = MagicMock()
        self.mock_ynab_client = MagicMock()
        self.budget_id = "test_budget_id"
        self.account_id = "test_account_id"
        
        # Create a temporary test file
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.file_path = self.temp_file.name
        
        self.worker = DuplicateCheckWorker(
            self.mock_converter,
            self.file_path,
            self.budget_id,
            self.account_id,
            self.mock_ynab_client
        )

        # Connect to signals for testing
        self.finished_signal_records = None
        self.finished_signal_duplicates = None
        self.error_signal_message = None
        
        self.worker.finished.connect(self.handle_finished)
        self.worker.error.connect(self.handle_error)

    def tearDown(self):
        """Clean up test fixtures."""
        os.unlink(self.file_path)

    def handle_finished(self, records, duplicates):
        """Handler for finished signal."""
        self.finished_signal_records = records
        self.finished_signal_duplicates = duplicates

    def handle_error(self, message):
        """Handler for error signal."""
        self.error_signal_message = message

    def test_run_success_no_duplicates(self):
        """Test successful duplicate check with no duplicates."""
        # Prepare mock data
        mock_df = pd.DataFrame({
            'Date': ['2025-07-01', '2025-07-02'],
            'Payee': ['Coffee Shop', 'Grocery Store'],
            'Memo': ['Coffee', 'Food'],
            'Amount': [-4.50, -65.30]
        })
        self.mock_converter.convert_to_ynab.return_value = mock_df
        
        mock_ynab_transactions = [
            {
                "date": "2025-06-15",
                "payee_name": "Restaurant",
                "memo": "Dinner",
                "amount": -45000  # YNAB uses milliunits (45.00)
            }
        ]
        self.mock_ynab_client.get_transactions.return_value = mock_ynab_transactions
        
        # Run the worker
        expected_since_date = (
            datetime.now() - timedelta(days=DUP_CHECK_DAYS)
        ).strftime("%Y-%m-%d")
        self.worker.run()

        # Check if the methods were called with correct parameters
        self.mock_converter.convert_to_ynab.assert_called_once_with(
            self.file_path,
            write_output=False,
        )
        self.mock_ynab_client.get_transactions.assert_called_once_with(
            self.budget_id,
            self.account_id,
            count=DUP_CHECK_COUNT,
            since_date=expected_since_date,
        )
        
        # Check if signal emitted correct data
        self.assertEqual(len(self.finished_signal_records), 2)
        self.assertEqual(len(self.finished_signal_duplicates), 0)  # No duplicates
        self.assertIsNone(self.error_signal_message)

    def test_run_success_with_duplicates(self):
        """Test successful duplicate check with duplicates."""
        # Prepare mock data
        mock_df = pd.DataFrame({
            'Date': ['2025-07-01', '2025-07-02'],
            'Payee': ['Coffee Shop', 'Grocery Store'],
            'Memo': ['Coffee', 'Food'],
            'Amount': [-4.50, -65.30]
        })
        self.mock_converter.convert_to_ynab.return_value = mock_df
        
        mock_ynab_transactions = [
            {
                "date": "2025-07-01",
                "payee_name": "Coffee Shop",
                "memo": "Coffee",
                "amount": -4500  # YNAB uses milliunits (4.50)
            }
        ]
        self.mock_ynab_client.get_transactions.return_value = mock_ynab_transactions
        
        # Run the worker
        self.worker.run()
        
        # Check if signal emitted correct data
        self.assertEqual(len(self.finished_signal_records), 2)
        self.assertEqual(len(self.finished_signal_duplicates), 1)  # One duplicate
        self.assertTrue(0 in self.finished_signal_duplicates)  # First record is duplicate
        self.assertIsNone(self.error_signal_message)

    def test_run_success_with_actual_import_id_duplicates(self):
        """Test duplicate check using import_id for Actual Budget."""
        class DummyActualClient(ActualClient):
            def __init__(self, transactions):
                self.get_transactions = MagicMock(return_value=transactions)

        mock_df = pd.DataFrame({
            'Date': ['2025-07-03', '2025-07-02'],
            'Payee': ['Coffee Shop', 'Grocery Store'],
            'Memo': ['Coffee', 'Food'],
            'Amount': [-4.50, -65.30],
            'ImportId': ['ABC123', None]
        })
        self.mock_converter.convert_to_ynab.return_value = mock_df

        mock_actual_transactions = [
            {
                "date": "2025-07-15",
                "payee_name": "Other Payee",
                "memo": "Other Memo",
                "amount": -9999,
                "import_id": "ABC123",
            },
            {
                "date": "2025-07-02",
                "payee_name": "Grocery Store",
                "memo": "Food",
                "amount": -65300,
                "import_id": None,
            },
        ]
        actual_client = DummyActualClient(mock_actual_transactions)
        worker = DuplicateCheckWorker(
            self.mock_converter,
            self.file_path,
            self.budget_id,
            self.account_id,
            actual_client,
        )

        self.finished_signal_records = None
        self.finished_signal_duplicates = None
        self.error_signal_message = None
        worker.finished.connect(self.handle_finished)
        worker.error.connect(self.handle_error)

        expected_since_date = (
            datetime.now() - timedelta(days=DUP_CHECK_DAYS)
        ).strftime("%Y-%m-%d")
        worker.run()

        actual_client.get_transactions.assert_called_once_with(
            self.budget_id,
            self.account_id,
            count=DUP_CHECK_COUNT,
            since_date=expected_since_date,
        )
        self.assertEqual(len(self.finished_signal_records), 2)
        self.assertEqual(self.finished_signal_duplicates, {0, 1})
        self.assertIsNone(self.error_signal_message)

    def test_run_success_with_actual_import_id_mismatch_fallback(self):
        """Test fallback matching when Actual import_id does not match."""
        class DummyActualClient(ActualClient):
            def __init__(self, transactions):
                self.get_transactions = MagicMock(return_value=transactions)

        mock_df = pd.DataFrame({
            'Date': ['2025-12-17'],
            'Payee': ['MIX MAPKT'],
            'Memo': ['MIX MAPKT'],
            'Amount': [-18.26],
            'ImportId': ['P34902D6D31J']
        })
        self.mock_converter.convert_to_ynab.return_value = mock_df

        mock_actual_transactions = [
            {
                "date": "2025-12-17",
                "payee_name": "MIX MAPKT",
                "memo": "MIX MAPKT",
                "amount": -18260,
                "import_id": "OTHERID",
            }
        ]
        actual_client = DummyActualClient(mock_actual_transactions)
        worker = DuplicateCheckWorker(
            self.mock_converter,
            self.file_path,
            self.budget_id,
            self.account_id,
            actual_client,
        )

        self.finished_signal_records = None
        self.finished_signal_duplicates = None
        self.error_signal_message = None
        worker.finished.connect(self.handle_finished)
        worker.error.connect(self.handle_error)

        worker.run()

        self.assertEqual(len(self.finished_signal_records), 1)
        self.assertEqual(self.finished_signal_duplicates, {0})
        self.assertIsNone(self.error_signal_message)

    def test_run_failure(self):
        """Test duplicate check failure."""
        # Simulate an exception
        self.mock_converter.convert_to_ynab.side_effect = Exception("Conversion error")
        
        # Run the worker
        self.worker.run()
        
        # Check if error signal was emitted
        self.assertIsNone(self.finished_signal_records)
        self.assertIsNone(self.finished_signal_duplicates)
        self.assertIn("Failed to check duplicates", self.error_signal_message)
        self.assertIn("Conversion error", self.error_signal_message)


class TestUploadWorker(unittest.TestCase):
    """Test the UploadWorker class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_ynab_client = MagicMock()
        self.budget_id = "test_budget_id"
        self.account_id = "test_account_id"
        self.transactions = [
            {
                "account_id": "test_account_id",
                "date": "2025-07-01",
                "payee_name": "Coffee Shop",
                "memo": "Coffee",
                "amount": -4500  # YNAB uses milliunits
            },
            {
                "account_id": "test_account_id",
                "date": "2025-07-02",
                "payee_name": "Grocery Store",
                "memo": "Food",
                "amount": -65300  # YNAB uses milliunits
            }
        ]
        
        self.worker = UploadWorker(
            self.mock_ynab_client,
            self.budget_id,
            self.account_id,
            self.transactions
        )

        # Connect to signals for testing
        self.finished_signal_count = None
        self.error_signal_message = None
        
        self.worker.finished.connect(self.handle_finished)
        self.worker.error.connect(self.handle_error)

    def handle_finished(self, count):
        """Handler for finished signal."""
        self.finished_signal_count = count

    def handle_error(self, message):
        """Handler for error signal."""
        self.error_signal_message = message

    def test_run_success(self):
        """Test successful transaction upload."""
        # Prepare mock response
        mock_response = {
            "data": {
                "transaction_ids": ["txn1", "txn2"],
                "transactions": [
                    {"id": "txn1"},
                    {"id": "txn2"}
                ]
            }
        }
        self.mock_ynab_client.upload_transactions.return_value = mock_response
        
        # Run the worker
        self.worker.run()
        
        # Check if the client method was called with correct parameters
        self.mock_ynab_client.upload_transactions.assert_called_once_with(
            self.budget_id, self.account_id, self.transactions
        )
        
        # Check if signal emitted correct data (2 transactions uploaded)
        self.assertEqual(self.finished_signal_count, 2)
        self.assertIsNone(self.error_signal_message)

    def test_run_failure(self):
        """Test transaction upload failure."""
        # Simulate an exception
        self.mock_ynab_client.upload_transactions.side_effect = Exception("API error")
        
        # Run the worker
        self.worker.run()
        
        # Check if error signal was emitted
        self.assertIsNone(self.finished_signal_count)
        self.assertIn("Failed to upload", self.error_signal_message)
        self.assertIn("API error", self.error_signal_message)


if __name__ == '__main__':
    unittest.main()
