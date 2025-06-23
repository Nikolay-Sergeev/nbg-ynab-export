# ui/pages/auth.py
from PyQt5.QtWidgets import (
    QWizardPage,
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
        outer_layout.setContentsMargins(24, 24, 24, 24)

        card = QFrame()
        card.setObjectName("card-panel")
        card.setMinimumWidth(500)
        card.setMaximumWidth(500)
        card.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 36, 36, 36)
        card_layout.setSpacing(0)

        title = QLabel("Authorize with YNAB")
        title.setProperty('role', 'title')
        card_layout.addWidget(title)

        # Drop shadow (skip on macOS to avoid Qt crash)
        if not sys.platform.startswith('darwin'):
            shadow = QGraphicsDropShadowEffect(card)
            shadow.setBlurRadius(18)
            shadow.setColor(QColor(0,0,0,30))
            shadow.setOffset(0, 2)
            card.setGraphicsEffect(shadow)



        # --- Subheading + helper link ---
        subheading_row = QHBoxLayout()
        subheading = QLabel("Enter your YNAB Personal Access Token")
        subheading.setStyleSheet("font-size:15px;font-weight:500;color:#333;")
        subheading_row.addWidget(subheading)
        subheading_row.addSpacing(8)
        self.helper_link = QLabel('<a href="#" style="color:#1976d2;text-decoration:none;font-size:14px;">How to get a token?</a>')
        self.helper_link.setCursor(QCursor(Qt.PointingHandCursor))
        self.helper_link.setStyleSheet("color:#1976d2;font-size:14px;")
        self.helper_link.linkActivated.connect(self.open_docs)
        subheading_row.addWidget(self.helper_link, alignment=Qt.AlignVCenter)
        subheading_row.addStretch(1)
        card_layout.addLayout(subheading_row)
        card_layout.addSpacing(16)

        # --- Token input with show/hide ---
        input_row = QHBoxLayout()
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("e.g. abc123def456…")
        self.token_input.setEchoMode(QLineEdit.Password)
        self.token_input.setMinimumWidth(280)
        self.token_input.setMaximumWidth(360)
        self.token_input.setStyleSheet("font-size:16px;")
        input_row.addStretch(1)
        input_row.addWidget(self.token_input)
        # Show/hide icon
        self.show_icon = QPushButton()
        self.show_icon.setCheckable(True)
        self.show_icon.setFixedSize(28, 28)
        self.show_icon.setIcon(QIcon.fromTheme("view-password"))
        self.show_icon.setStyleSheet("border:none;background:transparent;margin-left:-34px;")
        self.show_icon.setToolTip("Show/Hide token")
        self.show_icon.toggled.connect(self.toggle_token_visibility)
        input_row.addWidget(self.show_icon)
        input_row.addStretch(1)
        card_layout.addLayout(input_row)
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

        # --- Navigation Buttons ---
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        self.back_button = QPushButton("Back")
        self.back_button.setObjectName("back-btn")
        self.back_button.setFixedWidth(100)
        self.back_button.setFixedHeight(40)
        self.back_button.clicked.connect(lambda: self.wizard().back())
        button_layout.addWidget(self.back_button)
        self.continue_button = QPushButton("Continue")
        self.continue_button.setObjectName("continue-btn")
        self.continue_button.setFixedWidth(100)
        self.continue_button.setFixedHeight(40)
        self.continue_button.clicked.connect(self.on_continue)
        button_layout.addStretch(1)
        button_layout.addWidget(self.continue_button)
        card_layout.addLayout(button_layout)

        # --- Final layout setup ---
        outer_layout.addWidget(card)
        outer_layout.addStretch(1)
        self.setLayout(outer_layout)

        # --- Logic ---
        self.token_input.textChanged.connect(self.validate_token_input)
        self.token_input.textChanged.connect(self.completeChanged)
        self._auto_validated = False
        self.load_saved_token()
        self.validate_token_input()

    def open_docs(self):
        QDesktopServices.openUrl(QUrl(YNAB_DOCS_URL))

    def toggle_token_visibility(self, checked):
        if checked:
            self.token_input.setEchoMode(QLineEdit.Normal)
            self.show_icon.setIcon(QIcon.fromTheme("view-hidden"))
        else:
            self.token_input.setEchoMode(QLineEdit.Password)
            self.show_icon.setIcon(QIcon.fromTheme("view-password"))

    def validate_token_input(self):
        token = self.token_input.text().strip()
        ynab_pattern = r"^[a-zA-Z0-9_-]{32,64}$"
        import re
        if not token:
            self.error_label.setText("Token cannot be empty.")
            self.continue_button.setEnabled(False)
            return False
        if not re.match(ynab_pattern, token):
            self.error_label.setText("Invalid token format.")
            self.continue_button.setEnabled(False)
            return False
        self.error_label.setText("")
        self.continue_button.setEnabled(True)
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
        self.wizard().next()

    def load_saved_token(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    lines = f.readlines()
                for line in lines:
                    if line.startswith("TOKEN:"):
                        enc_token = line.split("TOKEN:",1)[1].strip()
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
