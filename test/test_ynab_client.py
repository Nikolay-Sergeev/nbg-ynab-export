import unittest
from unittest.mock import patch, MagicMock
import requests
import json
from services.ynab_client import YnabClient


class TestYnabClient(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        self.client = YnabClient("test_token")
        self.mock_response = MagicMock()
        self.mock_response.status_code = 200

    @patch('requests.get')
    def test_get_budgets(self, mock_get):
        """Test fetching budgets."""
        # Setup mock
        self.mock_response.json.return_value = {"data": {"budgets": [
            {"id": "budget1", "name": "Test Budget"}
        ]}}
        mock_get.return_value = self.mock_response

        # Call the method
        budgets = self.client.get_budgets()

        # Assertions
        self.assertEqual(len(budgets), 1)
        self.assertEqual(budgets[0]["id"], "budget1")
        self.assertEqual(budgets[0]["name"], "Test Budget")
        mock_get.assert_called_once_with(
            "https://api.ynab.com/v1/budgets",
            headers={"Authorization": "Bearer test_token"},
            timeout=10
        )

    @patch('requests.get')
    def test_get_accounts(self, mock_get):
        """Test fetching accounts for a budget."""
        # Setup mock
        self.mock_response.json.return_value = {"data": {"accounts": [
            {"id": "account1", "name": "Checking", "type": "checking"}
        ]}}
        mock_get.return_value = self.mock_response

        # Call the method
        accounts = self.client.get_accounts("budget1")

        # Assertions
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0]["id"], "account1")
        self.assertEqual(accounts[0]["name"], "Checking")
        mock_get.assert_called_once_with(
            "https://api.ynab.com/v1/budgets/budget1/accounts",
            headers={"Authorization": "Bearer test_token"},
            timeout=10
        )

    @patch('requests.get')
    def test_get_transactions(self, mock_get):
        """Test fetching transactions for an account."""
        # Setup mock
        self.mock_response.json.return_value = {"data": {"transactions": [
            {"id": "t1", "date": "2025-07-01", "amount": -10000}
        ]}}
        mock_get.return_value = self.mock_response

        # Call the method
        transactions = self.client.get_transactions("budget1", "account1")

        # Assertions
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0]["id"], "t1")
        mock_get.assert_called_once_with(
            "https://api.ynab.com/v1/budgets/budget1/accounts/account1/transactions",
            headers={"Authorization": "Bearer test_token"},
            params={},
            timeout=15
        )

    @patch('requests.get')
    def test_get_transactions_with_params(self, mock_get):
        """Test fetching transactions with pagination and filtering."""
        # Setup mock
        self.mock_response.json.return_value = {"data": {"transactions": []}}
        mock_get.return_value = self.mock_response

        # Call the method with parameters
        self.client.get_transactions(
            "budget1", "account1", count=10, page=2, since_date="2025-01-01"
        )

        # Assertions
        mock_get.assert_called_once_with(
            "https://api.ynab.com/v1/budgets/budget1/accounts/account1/transactions",
            headers={"Authorization": "Bearer test_token"},
            params={"count": 10, "page": 2, "since_date": "2025-01-01"},
            timeout=15
        )

    @patch('requests.post')
    def test_upload_transactions(self, mock_post):
        """Test uploading transactions."""
        # Setup mock
        self.mock_response.json.return_value = {
            "data": {
                "transaction_ids": ["t1"],
                "duplicate_import_ids": [],
                "transaction_ids_count": 1
            }
        }
        mock_post.return_value = self.mock_response

        # Create test transactions
        transactions = [{
            "account_id": "account1",
            "date": "2025-07-01",
            "amount": -10000,
            "payee_name": "Test Store"
        }]

        # Call the method
        result = self.client.upload_transactions("budget1", transactions)

        # Assertions
        self.assertIn("transaction_ids", result["data"])
        self.assertEqual(len(result["data"]["transaction_ids"]), 1)
        mock_post.assert_called_once_with(
            "https://api.ynab.com/v1/budgets/budget1/transactions",
            headers={"Authorization": "Bearer test_token", "Content-Type": "application/json"},
            json={"transactions": transactions},
            timeout=20
        )

    @patch('requests.get')
    def test_get_account_name(self, mock_get):
        """Test getting account name with cache."""
        # Setup mock for the first call to get_accounts
        self.mock_response.json.return_value = {"data": {"accounts": [
            {"id": "account1", "name": "Checking"},
            {"id": "account2", "name": "Savings"}
        ]}}
        mock_get.return_value = self.mock_response

        # First call should fetch accounts
        name = self.client.get_account_name("budget1", "account2")

        # Assert results and API call
        self.assertEqual(name, "Savings")
        mock_get.assert_called_once()

        # Reset mock for second test
        mock_get.reset_mock()

        # Second call should use cache
        name = self.client.get_account_name("budget1", "account1")
        self.assertEqual(name, "Checking")
        mock_get.assert_not_called()  # API not called again

        # Test with unknown account ID
        name = self.client.get_account_name("budget1", "non_existent")
        self.assertEqual(name, "Unknown Account")

    @patch('requests.get')
    def test_api_error_handling(self, mock_get):
        """Test handling of API errors."""
        # Setup mock to raise an exception
        mock_get.side_effect = requests.exceptions.HTTPError("401 Client Error: Unauthorized")

        # Call method and check exception
        with self.assertRaises(requests.exceptions.HTTPError):
            self.client.get_budgets()

    @patch('requests.get')
    def test_connection_error_handling(self, mock_get):
        """Test handling of connection errors."""
        # Setup mock to raise a connection error
        mock_get.side_effect = requests.exceptions.ConnectionError(
            "Failed to establish connection"
        )

        # Call method and check exception
        with self.assertRaises(requests.exceptions.ConnectionError):
            self.client.get_budgets()


if __name__ == '__main__':
    unittest.main(verbosity=2)