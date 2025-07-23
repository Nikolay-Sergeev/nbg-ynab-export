import unittest
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch
from PyQt5.QtWidgets import QApplication, QWizard, QFrame, QVBoxLayout
from PyQt5.QtCore import Qt, QMimeData, QUrl, QPoint
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
from PyQt5.QtTest import QTest

from ui.pages.import_file import ImportFilePage, DropZone
from ui.pages.auth import YNABAuthPage
from ui.pages.account_select import AccountSelectionPage
from ui.pages.review_upload import ReviewAndUploadPage

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
        except Exception:
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
        
        # Mock the handle_file_selected method to avoid file validation issues in tests
        self.page.handle_file_selected = MagicMock()
        
        # Call the browse_file method directly
        self.page.browse_file()
        
        # Check that handle_file_selected was called with the right path
        self.page.handle_file_selected.assert_called_once_with(self.temp_file_path)

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
        
        # Directly set the file path on the page
        self.page.file_path = self.temp_file_path
        
        # Now the page should be valid
        self.assertTrue(self.page.isComplete())

    def test_handle_file_selected_saves_folder(self):
        """Ensure selected folder path is persisted."""
        tmp_dir = tempfile.mkdtemp()
        settings_path = os.path.join(tmp_dir, "settings.txt")

        with patch("ui.pages.import_file.SETTINGS_FILE", settings_path):
            page = ImportFilePage(self.mock_controller)
            page.handle_file_selected(self.temp_file_path)

        with open(settings_path, "r") as f:
            contents = f.read()

        expected = f"FOLDER:{os.path.dirname(self.temp_file_path)}\n"
        self.assertIn(expected, contents)


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
        # Check for essential UI elements
        self.assertIsNotNone(self.page.token_input)
        self.assertIsNotNone(self.page.save_checkbox)

    def test_open_help_link(self):
        """Test that the help link exists."""
        # Verify that the helper_link exists
        self.assertIsNotNone(self.page.helper_link)
        # The actual opening would require QDesktopServices.openUrl to be mocked,
        # which is more complex and unnecessary for basic tests

    def test_validate_page_empty_token(self):
        """Test page validation with empty token."""
        # Get the token input field
        token_input = self.page.token_input
        self.assertIsNotNone(token_input)
        
        # Initially the field is empty
        token_input.setText("")
        
        # The page should not be valid
        self.assertFalse(self.page.isComplete())

    def test_validate_page_with_token(self):
        """Test page validation with token."""
        # Get the token input field
        token_input = self.page.token_input
        self.assertIsNotNone(token_input)
        
        # Set a valid token format (32-64 characters of a-zA-Z0-9_-)
        token_input.setText("abcdef1234567890abcdef1234567890abcdef12")
        
        # Force validation
        self.page._validate_and_update()
        
        # The page should be valid
        self.assertTrue(self.page.isComplete())

    @patch('ui.pages.auth.Fernet')
    def test_save_token_on_validation(self, mock_fernet):
        """Test that token validation works properly."""
        # Get the token input field
        token_input = self.page.token_input
        self.assertIsNotNone(token_input)
        
        # Set a valid token format (32-64 characters of a-zA-Z0-9_-)
        test_token = "abcdef1234567890abcdef1234567890abcdef12"
        token_input.setText(test_token)
        
        # Check the checkbox to save the token
        self.page.save_checkbox.setChecked(True)
        
        # Mock the controller's authorize method
        self.mock_controller.authorize.return_value = True
        
        # Mock encryption for token saving
        mock_fernet_instance = MagicMock()
        mock_fernet_instance.encrypt.return_value = b"encrypted_token"
        mock_fernet.return_value = mock_fernet_instance
        mock_fernet.generate_key.return_value = b"test_key"
        
        # Mock file operations
        with patch('builtins.open', MagicMock()):
            with patch('os.path.exists', return_value=False):
                # Check validation logic without navigation
                self.assertTrue(self.page.validate_token_input())
        
        # The check box should still be checked
        self.assertTrue(self.page.save_checkbox.isChecked())


class TestAccountSelectionPage(unittest.TestCase):
    """Test the AccountSelectionPage widget."""

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
        
        # Create container frame (we're not using a wizard anymore)
        self.container = QFrame()
        layout = QVBoxLayout(self.container)
        
        # Create the page
        self.page = AccountSelectionPage(self.mock_controller)
        layout.addWidget(self.page)

    def tearDown(self):
        """Clean up test fixtures."""
        self.container.close()

    def test_initialization(self):
        """Test that the page initializes correctly."""
        # In the new architecture, check for essential widgets
        self.assertIsNotNone(self.page.budget_combo)
        self.assertIsNotNone(self.page.account_combo)

    def test_on_budgets_fetched(self):
        """Test handling budgets data."""
        # Call the on_budgets_fetched method which replaced populate_budgets
        self.page.on_budgets_fetched(self.mock_budgets)
        
        # Budget combo should now have 3 items (default + 2 budgets)
        self.assertEqual(self.page.budget_combo.count(), 3)
        self.assertEqual(self.page.budget_combo.itemText(1), "Budget One")
        self.assertEqual(self.page.budget_combo.itemText(2), "Budget Two")

    def test_on_accounts_fetched(self):
        """Test handling accounts data."""
        # Call the on_accounts_fetched method which replaced populate_accounts
        self.page.on_accounts_fetched(self.mock_accounts)
        
        # Account combo should now have 3 items (default + 2 accounts)
        self.assertEqual(self.page.account_combo.count(), 3)
        self.assertEqual(self.page.account_combo.itemText(1), "Checking")
        self.assertEqual(self.page.account_combo.itemText(2), "Savings")

    def test_validate_page_no_selection(self):
        """Test page validation with no account selected."""
        # Initially no account is selected
        self.assertFalse(self.page.isComplete())

    def test_validate_page_with_selection(self):
        """Test page validation with account selected."""
        # Directly set the selection IDs
        self.page.selected_budget_id = "budget1"
        self.page.selected_account_id = "account1"
        
        # The page should now be valid
        self.assertTrue(self.page.isComplete())

    def test_budget_selection_triggers_account_fetch(self):
        """Test that selecting a budget triggers account fetch."""
        # Reset the mock to clear any calls during setup
        self.mock_controller.fetch_accounts.reset_mock()
        
        # Add items to the combo box
        self.page.budget_combo.addItem("Budget One", "budget1")
        self.page.budget_combo.addItem("Budget Two", "budget2")
        
        # Select the first budget by index
        self.page.budget_combo.setCurrentIndex(0)
        
        # Manually call the change handler since the signal won't be emitted in tests
        self.page.on_budget_changed(0)
        
        # Check that the controller was called to fetch accounts
        self.mock_controller.fetch_accounts.assert_called_with("budget1")


class TestReviewAndUploadPage(unittest.TestCase):
    """Test the ReviewAndUploadPage widget."""

    def setUp(self):
        self.mock_controller = MagicMock()
        self.container = QFrame()
        layout = QVBoxLayout(self.container)
        self.page = ReviewAndUploadPage(self.mock_controller)
        layout.addWidget(self.page)

    def tearDown(self):
        self.container.close()

    def test_hide_duplicates_checkbox(self):
        records = [
            {"Date": "2025-07-01", "Payee": "Coffee", "Memo": "", "Amount": "1"},
            {"Date": "2025-07-02", "Payee": "Shop", "Memo": "", "Amount": "2"},
        ]
        dup_idx = {1}

        self.page.on_duplicates_found(records, dup_idx)

        # Checkbox should be visible when duplicates exist
        self.assertFalse(self.page.hide_dup_checkbox.isHidden())

        # Toggling should hide/show duplicate rows
        self.page.hide_dup_checkbox.setChecked(True)
        self.assertTrue(self.page.table.isRowHidden(1))
        self.page.hide_dup_checkbox.setChecked(False)
        self.assertFalse(self.page.table.isRowHidden(1))


if __name__ == '__main__':
    unittest.main()