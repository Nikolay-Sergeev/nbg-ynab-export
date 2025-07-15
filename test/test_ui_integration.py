import unittest
import os
import sys
from pathlib import Path
import tempfile
from unittest.mock import patch, MagicMock
import pandas as pd

# Set up PyQt5 offscreen mode for tests
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt5.QtWidgets import QApplication, QFileDialog
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal

from ui.wizard import RobustWizard
from ui.pages.import_file import ImportFilePage
from ui.pages.auth import YNABAuthPage
from ui.pages.account_select import AccountSelectionPage
from ui.pages.transactions import TransactionsPage
from ui.pages.review_upload import ReviewAndUploadPage
from ui.controller import WizardController


class SignalEmitter(QObject):
    """Helper class for emitting signals in tests."""
    signal = pyqtSignal()
    
    def emit(self):
        self.signal.emit()


class TestUIComponents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up QApplication once for all tests."""
        cls.app = QApplication.instance() or QApplication([])
        
    def setUp(self):
        """Set up test environment before each test."""
        # Create a temporary file to use as test input
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.csv', delete=False)
        self.temp_file.write(b"Type,Started Date,Description,Amount,Fee,State,Currency\n")
        self.temp_file.write(b"CARD_PAYMENT,2024-07-15,Test,10.00,0.00,COMPLETED,EUR\n")
        self.temp_file.close()
        
    def tearDown(self):
        """Clean up after each test."""
        if hasattr(self, 'temp_file') and os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    @patch('PyQt5.QtWidgets.QFileDialog.getOpenFileName')
    def test_import_file_page(self, mock_dialog):
        """Test the import file page behavior."""
        # Set up mock dialog response
        mock_dialog.return_value = (self.temp_file.name, "CSV Files (*.csv)")
        
        # Create wizard and import page
        wizard = RobustWizard()
        import_page = ImportFilePage(wizard)
        
        # Check initial state
        self.assertFalse(import_page.isComplete())
        
        # Simulate browse button click
        import_page.browse_button.click()
        
        # Check that the file path was updated
        self.assertEqual(import_page.file_path, self.temp_file.name)
        self.assertTrue(import_page.isComplete())
        
        # Verify file format detected correctly
        self.assertEqual(import_page.detected_format.text(), "Detected format: Revolut CSV")
        
        # Clean up
        wizard.deleteLater()
    
    @patch('services.token_manager.save_token')
    def test_ynab_auth_page(self, mock_save_token):
        """Test the YNAB auth page behavior."""
        # Create wizard and auth page
        wizard = RobustWizard()
        auth_page = YNABAuthPage(wizard)
        
        # Check initial state
        self.assertFalse(auth_page.isComplete())
        
        # Enter a token
        QTest.keyClicks(auth_page.token_input, "test_token_123")
        self.assertTrue(auth_page.isComplete())
        
        # Simulate next button press and verify token saved
        wizard.next()
        mock_save_token.assert_called_once_with("test_token_123")
        
        # Clean up
        wizard.deleteLater()
    
    @patch('services.ynab_client.YnabClient')
    def test_account_selection_page(self, MockClient):
        """Test the account selection page."""
        # Set up mock client with dummy budgets and accounts
        mock_client = MockClient.return_value
        mock_client.get_budgets.return_value = [
            {"id": "budget1", "name": "Budget 1"},
            {"id": "budget2", "name": "Budget 2"}
        ]
        mock_client.get_accounts.return_value = [
            {"id": "account1", "name": "Checking", "closed": False, "deleted": False},
            {"id": "account2", "name": "Savings", "closed": False, "deleted": False}
        ]
        
        # Create wizard with mocked client
        wizard = RobustWizard()
        wizard.controller = WizardController("test_token")
        wizard.controller.client = mock_client
        wizard.registerField("file_path*", MagicMock())
        
        # Create account selection page
        account_page = AccountSelectionPage(wizard)
        
        # Simulate worker completion signal
        account_page.budget_fetch_complete([
            {"id": "budget1", "name": "Budget 1"},
            {"id": "budget2", "name": "Budget 2"}
        ])
        
        # Check budgets loaded
        self.assertEqual(account_page.budget_combo.count(), 2)
        
        # Select first budget and simulate selection changed
        account_page.budget_combo.setCurrentIndex(0)
        account_page.on_budget_selected(0)
        
        # Simulate worker completion for accounts
        account_page.account_fetch_complete([
            {"id": "account1", "name": "Checking", "closed": False, "deleted": False},
            {"id": "account2", "name": "Savings", "closed": False, "deleted": False}
        ])
        
        # Check accounts loaded
        self.assertEqual(account_page.account_combo.count(), 2)
        
        # Select first account
        account_page.account_combo.setCurrentIndex(0)
        self.assertTrue(account_page.isComplete())
        
        # Clean up
        wizard.deleteLater()


if __name__ == '__main__':
    unittest.main(verbosity=2)