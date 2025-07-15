import unittest
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch
from PyQt5.QtWidgets import QApplication, QWizard
from PyQt5.QtCore import Qt, QMimeData, QUrl, QPoint
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
from PyQt5.QtTest import QTest

from ui.pages.import_file import ImportFilePage, DropZone
from ui.pages.auth import YNABAuthPage
from ui.pages.account_select import AccountSelectionPage

# Create QApplication instance for UI tests
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)


class TestDropZone(unittest.TestCase):
    """Test the DropZone widget in import_file.py."""

    def setUp(self):
        """Set up test fixtures."""
        self.drop_zone = DropZone()
        
        # Track signal emissions
        self.file_clicked_emitted = False
        self.file_dropped_path = None
        
        # Connect to signals
        self.drop_zone.fileClicked.connect(self.handle_file_clicked)
        self.drop_zone.fileDropped.connect(self.handle_file_dropped)

    def handle_file_clicked(self):
        """Handler for fileClicked signal."""
        self.file_clicked_emitted = True

    def handle_file_dropped(self, path):
        """Handler for fileDropped signal."""
        self.file_dropped_path = path

    def test_initialization(self):
        """Test that the DropZone initializes correctly."""
        self.assertTrue(self.drop_zone.acceptDrops())
        self.assertEqual(self.drop_zone.cursor().shape(), Qt.PointingHandCursor)
        
        # Check that the labels have correct text
        self.assertIn("Drag & drop", self.drop_zone.text_label.text())
        self.assertIn("Supported formats", self.drop_zone.supported_label.text())

    def test_set_text(self):
        """Test setting custom text."""
        test_text = "Test message"
        test_color = "#FF0000"
        
        self.drop_zone.setText(test_text, test_color)
        self.assertEqual(self.drop_zone.text_label.text(), test_text)
        self.assertIn(test_color, self.drop_zone.text_label.styleSheet())

    def test_mouse_press(self):
        """Test mouse press event."""
        QTest.mouseClick(self.drop_zone, Qt.LeftButton)
        self.assertTrue(self.file_clicked_emitted)

    def test_is_valid_file(self):
        """Test the _is_valid_file method."""
        # Valid file extensions
        self.assertTrue(self.drop_zone._is_valid_file("file.csv"))
        self.assertTrue(self.drop_zone._is_valid_file("file.xlsx"))
        self.assertTrue(self.drop_zone._is_valid_file("file.xls"))
        self.assertTrue(self.drop_zone._is_valid_file("FILE.CSV"))  # Test case insensitivity
        
        # Invalid file extensions
        self.assertFalse(self.drop_zone._is_valid_file("file.txt"))
        self.assertFalse(self.drop_zone._is_valid_file("file.pdf"))
        self.assertFalse(self.drop_zone._is_valid_file("file"))

    def test_drag_enter_valid_file(self):
        """Test drag enter event with valid file."""
        # Create mock QDragEnterEvent with valid file
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile("file.xlsx")])
        
        event = MagicMock(spec=QDragEnterEvent)
        event.mimeData.return_value = mime_data
        
        # Process the event
        self.drop_zone.dragEnterEvent(event)
        
        # Check that the event was accepted
        event.acceptProposedAction.assert_called_once()
        self.assertTrue(self.drop_zone.property("drag"))
        self.assertIn("dashed #3897f0", self.drop_zone.styleSheet())  # Blue border for valid file

    def test_drag_enter_invalid_file(self):
        """Test drag enter event with invalid file."""
        # Create mock QDragEnterEvent with invalid file
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile("file.txt")])
        
        event = MagicMock(spec=QDragEnterEvent)
        event.mimeData.return_value = mime_data
        
        # Process the event
        self.drop_zone.dragEnterEvent(event)
        
        # Check that the event was ignored
        event.ignore.assert_called_once()
        self.assertIn("dashed #d32f2f", self.drop_zone.styleSheet())  # Red border for invalid file

    def test_drag_leave(self):
        """Test drag leave event."""
        # First set the drag property
        self.drop_zone.setProperty("drag", True)
        self.drop_zone.setStyleSheet("border:2px dashed #3897f0;")
        
        # Create mock event
        event = MagicMock()
        
        # Process the event
        self.drop_zone.dragLeaveEvent(event)
        
        # Check that the drag property was reset
        self.assertFalse(self.drop_zone.property("drag"))
        self.assertEqual(self.drop_zone.styleSheet(), "")
        event.accept.assert_called_once()

    def test_drop_valid_file(self):
        """Test drop event with valid file."""
        # Create mock QDropEvent with valid file
        file_path = "file.xlsx"
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(file_path)])
        
        event = MagicMock(spec=QDropEvent)
        event.mimeData.return_value = mime_data
        
        # Process the event
        self.drop_zone.dropEvent(event)
        
        # Check that the signal was emitted with correct path
        self.assertEqual(self.file_dropped_path, file_path)
        event.accept.assert_called_once()

    def test_drop_invalid_file(self):
        """Test drop event with invalid file."""
        # Create mock QDropEvent with invalid file
        file_path = "file.txt"
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(file_path)])
        
        event = MagicMock(spec=QDropEvent)
        event.mimeData.return_value = mime_data
        
        # Process the event
        self.drop_zone.dropEvent(event)
        
        # Check that the signal was emitted with empty path
        self.assertEqual(self.file_dropped_path, "")
        event.accept.assert_called_once()


class TestImportFilePage(unittest.TestCase):
    """Test the ImportFilePage wizard page."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock controller
        self.mock_controller = MagicMock()
        
        # Create wizard for hosting the page
        self.wizard = QWizard()
        
        # Create the page
        self.page = ImportFilePage(self.mock_controller)
        self.wizard.addPage(self.page)
        
        # Create a temporary test file for file selection
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        self.temp_file_path = self.temp_file.name
        self.temp_file.close()

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            os.unlink(self.temp_file_path)
        except:
            pass  # Ignore if file is already deleted
        self.wizard.close()

    def test_initialization(self):
        """Test that the page initializes correctly."""
        self.assertFalse(self.page.isFinalPage())
        self.assertTrue(self.page.isCommitPage())
        self.assertIsNotNone(self.page.findChild(DropZone))

    @patch('ui.pages.import_file.QFileDialog.getOpenFileName')
    def test_browse_for_file(self, mock_file_dialog):
        """Test browsing for a file."""
        # Setup mock to return our temporary file
        mock_file_dialog.return_value = (self.temp_file_path, "Excel Files (*.xlsx *.xls)")
        
        # Call the browse_file method directly
        self.page.browse_file()
        
        # Check that the controller was called to set the file path
        self.mock_controller.set_import_file.assert_called_once_with(self.temp_file_path)

    @patch('ui.pages.import_file.QFileDialog.getOpenFileName')
    def test_browse_for_file_canceled(self, mock_file_dialog):
        """Test canceling the file browser dialog."""
        # Setup mock to return empty selection (user canceled)
        mock_file_dialog.return_value = ("", "")
        
        # Call the browse_file method directly
        self.page.browse_file()
        
        # Check that the controller was not called
        self.mock_controller.set_import_file.assert_not_called()

    def test_validate_page(self):
        """Test page validation logic."""
        # Initially the page should not be valid
        self.assertFalse(self.page.isComplete())
        
        # Set a valid file path
        self.mock_controller.get_import_file.return_value = self.temp_file_path
        
        # Now the page should be valid
        self.assertTrue(self.page.isComplete())


class TestYNABAuthPage(unittest.TestCase):
    """Test the YNABAuthPage wizard page."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock controller
        self.mock_controller = MagicMock()
        
        # Create wizard for hosting the page
        self.wizard = QWizard()
        
        # Create the page
        self.page = YNABAuthPage(self.mock_controller)
        self.wizard.addPage(self.page)

    def tearDown(self):
        """Clean up test fixtures."""
        self.wizard.close()

    def test_initialization(self):
        """Test that the page initializes correctly."""
        self.assertFalse(self.page.isFinalPage())
        self.assertTrue(self.page.isCommitPage())

    @patch('ui.pages.auth.webbrowser.open')
    def test_open_help_link(self, mock_webbrowser):
        """Test opening the help link."""
        # Find the help link button and click it
        help_button = self.page.findChild(QPushButton, "help_button")
        self.assertIsNotNone(help_button)
        
        QTest.mouseClick(help_button, Qt.LeftButton)
        
        # Check that the browser was opened with the correct URL
        mock_webbrowser.assert_called_once()
        self.assertIn("ynab", mock_webbrowser.call_args[0][0].lower())

    def test_validate_page_empty_token(self):
        """Test page validation with empty token."""
        # Get the token field
        token_field = self.page.token_field
        self.assertIsNotNone(token_field)
        
        # Initially the field is empty
        token_field.setText("")
        
        # The page should not be valid
        self.assertFalse(self.page.isComplete())

    def test_validate_page_with_token(self):
        """Test page validation with token."""
        # Get the token field
        token_field = self.page.token_field
        self.assertIsNotNone(token_field)
        
        # Set a token value
        token_field.setText("test_token_value")
        
        # The page should be valid
        self.assertTrue(self.page.isComplete())

    def test_save_token_on_next_page(self):
        """Test that token is saved when going to next page."""
        # Get the token field
        token_field = self.page.token_field
        self.assertIsNotNone(token_field)
        
        # Set a token value
        test_token = "test_token_value"
        token_field.setText(test_token)
        
        # Manually trigger the validatePage method
        self.page.validatePage()
        
        # Check that controller was called to save token
        self.mock_controller.set_token.assert_called_once_with(test_token)


class TestAccountSelectionPage(unittest.TestCase):
    """Test the AccountSelectionPage wizard page."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock controller
        self.mock_controller = MagicMock()
        
        # Mock budget data
        self.mock_budgets = [
            {"id": "budget1", "name": "Budget One"},
            {"id": "budget2", "name": "Budget Two"}
        ]
        
        # Mock account data
        self.mock_accounts = [
            {"id": "account1", "name": "Checking", "balance": 10000},
            {"id": "account2", "name": "Savings", "balance": 50000}
        ]
        
        # Configure controller mock
        self.mock_controller.get_budgets.return_value = self.mock_budgets
        
        # Create wizard for hosting the page
        self.wizard = QWizard()
        
        # Create the page
        self.page = AccountSelectionPage(self.mock_controller)
        self.wizard.addPage(self.page)

    def tearDown(self):
        """Clean up test fixtures."""
        self.wizard.close()

    def test_initialization(self):
        """Test that the page initializes correctly."""
        self.assertFalse(self.page.isFinalPage())
        self.assertTrue(self.page.isCommitPage())

    def test_populate_budgets(self):
        """Test populating the budget dropdown."""
        # Directly call the populate_budgets method
        self.page.populate_budgets(self.mock_budgets)
        
        # Check that budgets were added to the dropdown
        self.assertEqual(self.page.budget_combo.count(), 2)
        self.assertEqual(self.page.budget_combo.itemText(0), "Budget One")
        self.assertEqual(self.page.budget_combo.itemText(1), "Budget Two")

    def test_populate_accounts(self):
        """Test populating the account list."""
        # Directly call the populate_accounts method
        self.page.populate_accounts(self.mock_accounts)
        
        # Check that accounts were added to the list
        self.assertEqual(self.page.account_list.count(), 2)
        
        # Check first account item
        first_item = self.page.account_list.item(0)
        self.assertIsNotNone(first_item)
        self.assertEqual(first_item.text(), "Checking")
        self.assertEqual(first_item.data(Qt.UserRole), "account1")

    def test_validate_page_no_selection(self):
        """Test page validation with no account selected."""
        # Initially no account is selected
        self.assertFalse(self.page.isComplete())

    def test_validate_page_with_selection(self):
        """Test page validation with account selected."""
        # Populate accounts
        self.page.populate_accounts(self.mock_accounts)
        
        # Select the first account
        self.page.account_list.setCurrentRow(0)
        
        # The page should now be valid
        self.assertTrue(self.page.isComplete())

    def test_budget_selection_triggers_account_fetch(self):
        """Test that selecting a budget triggers account fetch."""
        # Populate budgets
        self.page.populate_budgets(self.mock_budgets)
        
        # Select the first budget
        self.page.budget_combo.setCurrentIndex(0)
        
        # Check that the controller was called to fetch accounts
        self.mock_controller.fetch_accounts.assert_called_with("budget1")


if __name__ == '__main__':
    unittest.main()