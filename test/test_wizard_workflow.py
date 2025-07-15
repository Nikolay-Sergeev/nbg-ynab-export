import unittest
import sys
import os
from unittest.mock import MagicMock, patch
from PyQt5.QtWidgets import QApplication, QWizard
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtTest import QTest

# Import wizard and related classes
from ui.wizard import (
    RobustWizard, 
    StepLabel, 
    SidebarWizardWindow
)
from ui.pages.import_file import ImportFilePage
from ui.pages.auth import YNABAuthPage
from ui.pages.account_select import AccountSelectionPage
from ui.pages.transactions import TransactionsPage
from ui.pages.review_upload import ReviewAndUploadPage
from ui.pages.finish_page import FinishPage

# Create QApplication instance for UI tests
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)


class TestStepLabel(unittest.TestCase):
    """Test the StepLabel class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.label = StepLabel("Test Step")
    
    def test_initialization(self):
        """Test that the label initializes correctly."""
        self.assertEqual(self.label.text(), "Test Step")
        self.assertTrue(self.label.wordWrap())
        self.assertEqual(self.label.alignment(), Qt.AlignLeft | Qt.AlignTop)
    
    def test_set_selected(self):
        """Test setting selected state."""
        # Initially not selected
        self.label.set_selected(False)
        style = self.label.styleSheet()
        self.assertIn("color:#333", style)
        self.assertNotIn("background-color:#007AFF", style)
        
        # Set to selected
        self.label.set_selected(True)
        style = self.label.styleSheet()
        self.assertIn("background-color:#007AFF", style)
        self.assertIn("color:white", style)
        
        # Set back to not selected
        self.label.set_selected(False)
        style = self.label.styleSheet()
        self.assertIn("color:#333", style)
        self.assertNotIn("background-color:#007AFF", style)


class TestRobustWizard(unittest.TestCase):
    """Test the RobustWizard class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_controller = MagicMock()
        
        self.wizard = RobustWizard()
        
        # Add pages to the wizard
        self.import_page = ImportFilePage(self.mock_controller)
        self.auth_page = YNABAuthPage(self.mock_controller)
        self.account_page = AccountSelectionPage(self.mock_controller)
        self.transactions_page = TransactionsPage(self.mock_controller)
        self.review_page = ReviewAndUploadPage(self.mock_controller)
        self.finish_page = FinishPage(self.mock_controller)
        
        self.wizard.addPage(self.import_page)      # ID: 0
        self.wizard.addPage(self.auth_page)        # ID: 1
        self.wizard.addPage(self.account_page)     # ID: 2
        self.wizard.addPage(self.transactions_page) # ID: 3
        self.wizard.addPage(self.review_page)      # ID: 4
        self.wizard.addPage(self.finish_page)      # ID: 5
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.wizard.close()
    
    def test_page_order(self):
        """Test that pages are in the expected order."""
        self.assertEqual(self.wizard.pageIds(), [0, 1, 2, 3, 4, 5])
        
        self.assertIs(self.wizard.page(0), self.import_page)
        self.assertIs(self.wizard.page(1), self.auth_page)
        self.assertIs(self.wizard.page(2), self.account_page)
        self.assertIs(self.wizard.page(3), self.transactions_page)
        self.assertIs(self.wizard.page(4), self.review_page)
        self.assertIs(self.wizard.page(5), self.finish_page)
    
    def test_next_id_override(self):
        """Test the overridden nextId method."""
        # Set current page to review page (ID: 4)
        self.wizard.setCurrentPage(4)
        
        # nextId should return 5 (finish page) when on review page
        self.assertEqual(self.wizard.nextId(), 5)
        
        # Test other pages follow default behavior
        self.wizard.setCurrentPage(0)
        self.assertEqual(self.wizard.nextId(), 1)
        
        self.wizard.setCurrentPage(1)
        self.assertEqual(self.wizard.nextId(), 2)
    
    @patch('ui.wizard.print')
    def test_initialize_page(self, mock_print):
        """Test page initialization."""
        # Initialize page 1 (YNABAuthPage)
        self.wizard.initializePage(1)
        
        # Check that the debug print was called
        mock_print.assert_called_with(f"[Wizard] initializePage called for page id 1 (YNABAuthPage)")
    
    @patch('ui.wizard.print')
    def test_close_event_with_workers(self, mock_print):
        """Test closeEvent handling of active workers."""
        # Create mock worker with isRunning method
        mock_worker = MagicMock()
        mock_worker.isRunning.return_value = True
        
        # Add worker to a page
        self.review_page.worker = mock_worker
        
        # Simulate close event
        self.wizard.closeEvent(MagicMock())
        
        # Check that worker's quit and wait methods were called
        mock_worker.quit.assert_called_once()
        mock_worker.wait.assert_called_once()


class TestWizardWorkflowTransitions(unittest.TestCase):
    """Test the workflow transitions between wizard pages."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_controller = MagicMock()
        
        # Create the wizard window with controller
        with patch('ui.wizard.WizardController', return_value=self.mock_controller):
            self.wizard_window = SidebarWizardWindow()
            self.wizard = self.wizard_window.wizard
        
        # Configure mock controller for testing page transitions
        self.mock_controller.get_import_file.return_value = "/path/to/test.xlsx"
        
        # For auth page
        self.mock_controller.get_token.return_value = "test_token"
        self.mock_controller.is_token_valid.return_value = True
        
        # For account selection page
        self.mock_budgets = [
            {"id": "budget1", "name": "Budget One"},
            {"id": "budget2", "name": "Budget Two"}
        ]
        self.mock_accounts = [
            {"id": "account1", "name": "Checking", "balance": 10000},
            {"id": "account2", "name": "Savings", "balance": 50000}
        ]
        self.mock_controller.get_budgets.return_value = self.mock_budgets
        self.mock_controller.get_accounts.return_value = self.mock_accounts
        
        # For transactions page
        self.mock_transactions = [
            {"date": "2025-07-01", "payee": "Coffee Shop", "memo": "Coffee", "amount": -450},
            {"date": "2025-07-02", "payee": "Grocery Store", "memo": "Food", "amount": -6530}
        ]
        self.mock_controller.get_transactions.return_value = self.mock_transactions
        self.mock_controller.get_duplicate_indices.return_value = set()
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.wizard_window.close()
    
    def test_import_page_to_auth_page_transition(self):
        """Test transition from import page to auth page."""
        # Start at import page
        self.wizard.restart()
        import_page = self.wizard.page(0)
        
        # Set up valid file path
        self.mock_controller.get_import_file.return_value = "/path/to/test.xlsx"
        self.mock_controller.is_file_valid.return_value = True
        
        # Page should be complete
        self.assertTrue(import_page.isComplete())
        
        # Advance to next page
        self.wizard.next()
        
        # Check that we're on the auth page
        self.assertEqual(self.wizard.currentId(), 1)
    
    def test_auth_page_to_account_page_transition(self):
        """Test transition from auth page to account selection page."""
        # Start at auth page
        self.wizard.restart()
        self.wizard.next()  # Go to auth page
        auth_page = self.wizard.page(1)
        
        # Set valid token
        auth_page.token_field.setText("valid_token")
        
        # Page should be complete
        self.assertTrue(auth_page.isComplete())
        
        # Advance to next page
        with patch('ui.pages.account_select.AccountSelectionPage.populate_budgets') as mock_populate:
            self.wizard.next()
            
            # Check that we're on the account selection page
            self.assertEqual(self.wizard.currentId(), 2)
            
            # Check that budgets were populated
            mock_populate.assert_called_once()
    
    def test_account_page_to_transactions_page_transition(self):
        """Test transition from account page to transactions page."""
        # Start at account selection page
        self.wizard.restart()
        self.wizard.next()  # Go to auth page
        self.wizard.next()  # Go to account selection page
        account_page = self.wizard.page(2)
        
        # Select a budget and account
        account_page.budget_id = "budget1"
        account_page.account_id = "account1"
        
        # Page should be complete
        self.assertTrue(account_page.isComplete())
        
        # Advance to next page
        with patch('ui.pages.transactions.TransactionsPage.load_transactions') as mock_load:
            self.wizard.next()
            
            # Check that we're on the transactions page
            self.assertEqual(self.wizard.currentId(), 3)
            
            # Check that transactions were loaded
            mock_load.assert_called_once()
    
    def test_transactions_page_to_review_page_transition(self):
        """Test transition from transactions page to review page."""
        # Start at transactions page
        self.wizard.restart()
        self.wizard.next()  # Go to auth page
        self.wizard.next()  # Go to account selection page
        self.wizard.next()  # Go to transactions page
        transactions_page = self.wizard.page(3)
        
        # Configure page to be complete
        transactions_page.transactions_selected = True
        
        # Page should be complete
        self.assertTrue(transactions_page.isComplete())
        
        # Advance to next page
        with patch('ui.pages.review_upload.ReviewAndUploadPage.load_summary') as mock_load:
            self.wizard.next()
            
            # Check that we're on the review page
            self.assertEqual(self.wizard.currentId(), 4)
            
            # Check that summary was loaded
            mock_load.assert_called_once()
    
    def test_review_page_to_finish_page_transition(self):
        """Test transition from review page to finish page."""
        # Start at review page
        self.wizard.restart()
        self.wizard.next()  # Go to auth page
        self.wizard.next()  # Go to account selection page
        self.wizard.next()  # Go to transactions page
        self.wizard.next()  # Go to review page
        review_page = self.wizard.page(4)
        
        # Configure page to be complete
        review_page.upload_complete = True
        
        # Page should be complete
        self.assertTrue(review_page.isComplete())
        
        # Advance to next page
        self.wizard.next()
        
        # Check that we're on the finish page
        self.assertEqual(self.wizard.currentId(), 5)
        
        # The finish page should be the final page
        self.assertTrue(self.wizard.page(5).isFinalPage())
        
    def test_sidebar_step_labels(self):
        """Test that sidebar step labels update correctly during transitions."""
        # Get access to step labels
        step_labels = self.wizard_window.step_labels
        self.assertEqual(len(step_labels), 6)  # Should have 6 steps
        
        # Navigate through pages and check labels
        for i in range(6):
            # Set current page
            self.wizard.setCurrentPage(i)
            
            # Current page label should be selected, others not
            for j, label in enumerate(step_labels):
                if j == i:
                    # Check through style sheet that this label is selected
                    self.assertIn("background-color:#007AFF", label.styleSheet())
                else:
                    self.assertNotIn("background-color:#007AFF", label.styleSheet())


if __name__ == '__main__':
    unittest.main()