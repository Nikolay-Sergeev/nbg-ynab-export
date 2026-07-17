# ui/pages/auth.py
from PyQt5.QtWidgets import (
    QWizardPage,
    QWizard,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QCheckBox,
    QPushButton,
    QFrame,
    QSizePolicy,
    QGraphicsDropShadowEffect,
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QColor, QCursor, QDesktopServices
import sys
import logging
from cryptography.fernet import Fernet  # noqa: F401 (kept for tests patching)
from services import token_manager as _token_manager
from ui.components import add_page_header

YNAB_DOCS_URL = "https://api.ynab.com/#personal-access-tokens"
logger = logging.getLogger(__name__)


class YNABAuthPage(QWizardPage):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setTitle("")  # Hide default title
        self.setObjectName("auth-page")

        # --- Outer layout for centering ---
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("card-panel")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 28, 32, 28)
        card_layout.setSpacing(12)

        add_page_header(
            card_layout,
            "Step 2",
            "Connect to YNAB",
            "Use a personal access token so the importer can load your budgets and create transactions.",
        )

        # Drop shadow (skip on macOS to avoid Qt crash)
        if not sys.platform.startswith('darwin'):
            shadow = QGraphicsDropShadowEffect(card)
            shadow.setBlurRadius(18)
            shadow.setColor(QColor(0, 0, 0, 30))
            shadow.setOffset(0, 2)
            card.setGraphicsEffect(shadow)

        # --- Subheading + helper link ---
        subheading_row = QHBoxLayout()
        subheading = QLabel("Personal access token")
        subheading.setProperty("role", "field-label")
        subheading_row.addWidget(subheading)
        subheading_row.addSpacing(8)
        self.helper_link = QLabel(
            '<a href="#" style="color:#0066cc;text-decoration:none;">'
            'Where do I find this?</a>'
        )
        self.helper_link.setCursor(QCursor(Qt.PointingHandCursor))
        self.helper_link.setObjectName("helper-link")
        self.helper_link.linkActivated.connect(self.open_docs)
        subheading_row.addWidget(self.helper_link, alignment=Qt.AlignVCenter)
        subheading_row.addStretch(1)
        card_layout.addLayout(subheading_row)
        card_layout.addSpacing(16)

        # --- Token input with show/hide ---
        input_container = QHBoxLayout()
        input_container.setContentsMargins(0, 0, 0, 0)

        input_area = QHBoxLayout()
        input_area.setSpacing(8)
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Paste your 32–64 character token")
        self.token_input.setEchoMode(QLineEdit.Password)
        input_area.addWidget(self.token_input)

        self.show_icon = QPushButton("Show")
        self.show_icon.setObjectName("show-token-btn")
        self.show_icon.setCheckable(True)
        self.show_icon.setFixedWidth(72)
        self.show_icon.setToolTip("Show or hide token")
        self.show_icon.toggled.connect(self.toggle_token_visibility)
        input_area.addWidget(self.show_icon)

        input_container.addLayout(input_area)

        card_layout.addLayout(input_container)
        card_layout.addSpacing(8)

        # --- Helper & error text ---
        self.helper_label = QLabel("Your token stays on this device and is sent only to YNAB.")
        self.helper_label.setObjectName("helper-label")
        card_layout.addWidget(self.helper_label, alignment=Qt.AlignLeft)
        self.error_label = QLabel("")
        self.error_label.setObjectName("error-label")
        card_layout.addWidget(self.error_label, alignment=Qt.AlignLeft)

        # --- Save token checkbox ---
        self.save_checkbox = QCheckBox("Save token securely on this device")
        card_layout.addWidget(self.save_checkbox, alignment=Qt.AlignLeft)
        card_layout.addStretch(1)

        # Navigation buttons are now in main window, no need to add them here

        # --- Final layout setup ---
        outer_layout.addWidget(card)
        outer_layout.addStretch(1)
        self.setLayout(outer_layout)

        # --- Logic ---
        self.token_input.textChanged.connect(self._validate_and_update)
        self._auto_validated = False
        self.load_saved_token()

    def open_docs(self):
        QDesktopServices.openUrl(QUrl(YNAB_DOCS_URL))

    def validate_and_proceed(self):
        """Validate token and proceed if valid"""
        logger.info("[YNABAuthPage] validate_and_proceed called")

        if not self.validate_token_input():
            return False

        token = self.token_input.text().strip()
        save = self.save_checkbox.isChecked()

        # Verify the token before saving it or moving to the budget step.
        success = self.controller.authorize(token, save)

        if not success:
            self.error_label.setText(
                getattr(self.controller, "last_error_message", None)
                or "YNAB could not verify this token."
            )
            return False

        if save:
            try:
                _token_manager.save_token(token)
            except Exception as e:
                self.error_label.setText(f"The token is valid, but could not be saved: {str(e)}")
                return False

        # Navigate to next page if successful
        parent = self.window()
        if hasattr(parent, "go_to_page") and hasattr(parent, "pages_stack"):
            current_index = parent.pages_stack.indexOf(self)
            if current_index >= 0:
                parent.go_to_page(current_index + 1)
                return True

        return False

    def toggle_token_visibility(self, checked):
        if checked:
            self.token_input.setEchoMode(QLineEdit.Normal)
            self.show_icon.setText("Hide")
        else:
            self.token_input.setEchoMode(QLineEdit.Password)
            self.show_icon.setText("Show")

    def _validate_and_update(self):
        """Internal method to validate token and update UI without recursion"""
        self.validate_token_input(show_errors=bool(self.token_input.text().strip()))
        self.completeChanged.emit()

    def validate_token_input(self, show_errors=True):
        token = self.token_input.text().strip()
        import re
        ynab_pattern = r"^[a-zA-Z0-9_-]{32,64}$"
        if not token:
            if show_errors:
                self.error_label.setText("Enter your personal access token to continue.")
            else:
                self.error_label.setText("")
            return False
        if not re.match(ynab_pattern, token):
            if show_errors:
                self.error_label.setText("This token should contain 32–64 letters, numbers, dashes, or underscores.")
            return False
        self.error_label.setText("")
        return True

    def isComplete(self):
        return self.validate_token_input(show_errors=False)

    def on_continue(self):
        if not self.validate_token_input():
            return
        token = self.token_input.text().strip()
        save = self.save_checkbox.isChecked()
        if not self.controller.authorize(token, save):
            self.error_label.setText(
                getattr(self.controller, "last_error_message", None)
                or "YNAB could not verify this token."
            )
            return
        if save:
            _token_manager.save_token(token)
        self.go_forward()

    def load_saved_token(self):
        try:
            token = _token_manager.load_token()
            if token:
                self.token_input.setText(token)
                self.save_checkbox.setChecked(True)
                self._auto_validated = True
        except FileNotFoundError:
            pass
        except Exception:
            # Ignore corrupt/legacy files to avoid breaking the UI
            pass

    def encrypt_token(self, token):
        # Delegate to shared token manager for key generation and encryption.
        return _token_manager.encrypt_token(token).decode()

    def decrypt_token(self, token_enc):
        return _token_manager.decrypt_token(token_enc.encode())

    def load_key(self):
        try:
            return _token_manager.load_key()
        except FileNotFoundError:
            key = _token_manager.generate_key()
            _token_manager.save_key(key)
            return key

    def go_back(self):
        """Navigate to the previous page."""
        # Try different navigation methods
        # First check if we're in a stacked widget with a parent window
        parent = self.window()
        if hasattr(parent, "go_to_page") and hasattr(parent, "pages_stack"):
            # Use our custom navigation system
            current_index = parent.pages_stack.indexOf(self)
            if current_index > 0:
                parent.go_to_page(current_index - 1)
                return

        # If not in stacked widget, try using wizard navigation
        wizard = self.wizard()
        if wizard is not None:
            wizard.back()

    def go_forward(self):
        """Navigate to the next page."""
        # Try different navigation methods
        # First check if we're in a stacked widget with a parent window
        parent = self.window()
        if hasattr(parent, "go_to_page") and hasattr(parent, "pages_stack"):
            # Use our custom navigation system
            current_index = parent.pages_stack.indexOf(self)
            if current_index >= 0:
                parent.go_to_page(current_index + 1)
                return

        # If not in stacked widget, try using wizard navigation
        wizard = self.wizard()
        if wizard is not None:
            wizard.next()

    def wizard(self):
        """Return the wizard containing this page, or None if not in a wizard."""
        # Try to get the wizard, otherwise return None
        parent = self.parent()
        if isinstance(parent, QWizard):
            return parent
        return None
