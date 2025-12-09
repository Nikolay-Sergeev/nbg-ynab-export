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
from PyQt5.QtGui import QIcon, QColor, QCursor, QDesktopServices
import os
import sys
from config import SETTINGS_FILE, KEY_FILE
from cryptography.fernet import Fernet

YNAB_DOCS_URL = "https://api.ynab.com/#personal-access-tokens"


class YNABAuthPage(QWizardPage):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setTitle("")  # Hide default title

        # --- Outer layout for centering ---
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("card-panel")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(0)

        title = QLabel("Verify YNAB Token")
        title.setProperty('role', 'title')
        card_layout.addWidget(title)

        # Drop shadow (skip on macOS to avoid Qt crash)
        if not sys.platform.startswith('darwin'):
            shadow = QGraphicsDropShadowEffect(card)
            shadow.setBlurRadius(18)
            shadow.setColor(QColor(0, 0, 0, 30))
            shadow.setOffset(0, 2)
            card.setGraphicsEffect(shadow)

        # --- Subheading + helper link ---
        subheading_row = QHBoxLayout()
        subheading = QLabel("Enter your YNAB Personal Access Token")
        subheading.setStyleSheet("font-size:15px;font-weight:500;color:#333;")
        subheading_row.addWidget(subheading)
        subheading_row.addSpacing(8)
        self.helper_link = QLabel(
            '<a href="#" style="color:#1976d2;text-decoration:none;font-size:14px;">How to get a token?</a>')
        self.helper_link.setCursor(QCursor(Qt.PointingHandCursor))
        self.helper_link.setStyleSheet("color:#1976d2;font-size:14px;")
        self.helper_link.linkActivated.connect(self.open_docs)
        subheading_row.addWidget(self.helper_link, alignment=Qt.AlignVCenter)
        subheading_row.addStretch(1)
        card_layout.addLayout(subheading_row)
        card_layout.addSpacing(16)

        # --- Token input with show/hide ---
        input_container = QHBoxLayout()
        input_container.setContentsMargins(0, 0, 0, 0)

        # Add stretches and widget to center it with flexible width
        input_container.addStretch(1)

        input_area = QHBoxLayout()
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("e.g. abc123def456…")
        self.token_input.setEchoMode(QLineEdit.Password)
        self.token_input.setMinimumWidth(280)
        self.token_input.setStyleSheet("font-size:16px;")
        input_area.addWidget(self.token_input)

        # Show/hide icon
        self.show_icon = QPushButton()
        self.show_icon.setCheckable(True)
        self.show_icon.setFixedSize(28, 28)
        self.show_icon.setIcon(QIcon.fromTheme("view-password"))
        self.show_icon.setStyleSheet("border:none;background:transparent;margin-left:-34px;")
        self.show_icon.setToolTip("Show/Hide token")
        self.show_icon.toggled.connect(self.toggle_token_visibility)
        input_area.addWidget(self.show_icon)

        # Add the input area to container
        input_container.addLayout(input_area)
        input_container.addStretch(1)

        card_layout.addLayout(input_container)
        card_layout.addSpacing(8)

        # --- Helper & error text ---
        self.helper_label = QLabel("Your token is stored locally and never sent to our servers.")
        self.helper_label.setObjectName("helper-label")
        self.helper_label.setStyleSheet("font-size:12px;color:#666;margin-bottom:0;")
        card_layout.addWidget(self.helper_label, alignment=Qt.AlignLeft)
        card_layout.addSpacing(8)
        self.error_label = QLabel("")
        self.error_label.setObjectName("error-label")
        self.error_label.setStyleSheet("font-size:12px;color:#d32f2f;margin-bottom:0;")
        card_layout.addWidget(self.error_label, alignment=Qt.AlignLeft)
        card_layout.addSpacing(8)

        # --- Save token checkbox ---
        self.save_checkbox = QCheckBox("Save token securely on this device")
        self.save_checkbox.setStyleSheet("font-size:14px;color:#333;margin-top:0;margin-bottom:0;")
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
        print("[YNABAuthPage] validate_and_proceed called")

        if not self.validate_token_input():
            return False

        token = self.token_input.text().strip()
        save = self.save_checkbox.isChecked()

        if save:
            try:
                enc_token = self.encrypt_token(token)
                # Save token, preserving only FOLDER entries
                lines = []
                if os.path.exists(SETTINGS_FILE):
                    with open(SETTINGS_FILE, "r") as f:
                        for line in f:
                            if line.startswith("FOLDER:"):
                                lines.append(line)
                lines.append(f"TOKEN:{enc_token}\n")
                with open(SETTINGS_FILE, "w") as f:
                    f.writelines(lines)
            except Exception as e:
                self.error_label.setText(f"Error saving token: {str(e)}")
                return False

        # Use controller to authorize and check result
        success = self.controller.authorize(token, save)

        if not success:
            self.error_label.setText("Failed to initialize YNAB client with this token")
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
            self.show_icon.setIcon(QIcon.fromTheme("view-hidden"))
        else:
            self.token_input.setEchoMode(QLineEdit.Password)
            self.show_icon.setIcon(QIcon.fromTheme("view-password"))

    def _validate_and_update(self):
        """Internal method to validate token and update UI without recursion"""
        self.validate_token_input()
        self.completeChanged.emit()

    def validate_token_input(self):
        token = self.token_input.text().strip()
        import re
        ynab_pattern = r"^[a-zA-Z0-9_-]{32,64}$"
        if not token:
            self.error_label.setText("Token cannot be empty.")
            return False
        if not re.match(ynab_pattern, token):
            self.error_label.setText("Invalid token format.")
            return False
        self.error_label.setText("")
        return True

    def isComplete(self):
        return self.validate_token_input()

    def on_continue(self):
        if not self.validate_token_input():
            return
        token = self.token_input.text().strip()
        save = self.save_checkbox.isChecked()
        if save:
            enc_token = self.encrypt_token(token)
            # Save token, preserving only FOLDER entries
            lines = []
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r") as f:
                    for line in f:
                        if line.startswith("FOLDER:"):
                            lines.append(line)
            lines.append(f"TOKEN:{enc_token}\n")
            with open(SETTINGS_FILE, "w") as f:
                f.writelines(lines)
        self.controller.authorize(token, save)
        self.go_forward()

    def load_saved_token(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    lines = f.readlines()
                for line in lines:
                    if line.startswith("TOKEN:"):
                        enc_token = line.split("TOKEN:", 1)[1].strip()
                        token = self.decrypt_token(enc_token)
                        self.token_input.setText(token)
                        self.save_checkbox.setChecked(True)
                        self._auto_validated = True
                        break
            except Exception:
                pass

    def encrypt_token(self, token):
        key = self.load_key()
        f = Fernet(key)
        return f.encrypt(token.encode()).decode()

    def decrypt_token(self, token_enc):
        key = self.load_key()
        f = Fernet(key)
        return f.decrypt(token_enc.encode()).decode()

    def load_key(self):
        if not os.path.exists(KEY_FILE):
            key = Fernet.generate_key()
            with open(KEY_FILE, "wb") as f:
                f.write(key)
        else:
            with open(KEY_FILE, "rb") as f:
                key = f.read()
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
