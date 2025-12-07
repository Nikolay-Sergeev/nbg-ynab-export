from PyQt5.QtWidgets import (
    QWizardPage, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QCheckBox,
    QPushButton, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
import os
from config import SETTINGS_FILE, KEY_FILE
from cryptography.fernet import Fernet


class ActualAuthPage(QWizardPage):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setTitle("")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("card-panel")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Connect to Actual Budget Server")
        title.setProperty('role', 'title')
        layout.addWidget(title)

        # Server URL
        url_row = QHBoxLayout()
        url_label = QLabel("Server URL:")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://actual.example.com")
        url_row.addWidget(url_label)
        url_row.addWidget(self.url_input)
        layout.addLayout(url_row)

        # Password
        pwd_row = QHBoxLayout()
        pwd_label = QLabel("Password:")
        self.pwd_input = QLineEdit()
        self.pwd_input.setEchoMode(QLineEdit.Password)
        self.pwd_input.setPlaceholderText("Server password")
        pwd_row.addWidget(pwd_label)
        pwd_row.addWidget(self.pwd_input)
        layout.addLayout(pwd_row)

        # Save checkbox
        self.save_checkbox = QCheckBox("Save credentials securely on this device")
        layout.addWidget(self.save_checkbox, alignment=Qt.AlignLeft)

        # Helper and error
        self.helper_label = QLabel("Your credentials are stored locally.")
        self.helper_label.setObjectName("helper-label")
        self.error_label = QLabel("")
        self.error_label.setObjectName("error-label")
        layout.addWidget(self.helper_label)
        layout.addWidget(self.error_label)
        layout.addStretch(1)

        outer.addWidget(card)
        outer.addStretch(1)
        self.setLayout(outer)

        self.url_input.textChanged.connect(self._on_change)
        self.pwd_input.textChanged.connect(self._on_change)
        self.load_saved()

    def _on_change(self):
        self.completeChanged.emit()

    def isComplete(self):
        return bool(self.url_input.text().strip()) and bool(self.pwd_input.text().strip())

    def validate_and_proceed(self):
        url = self.url_input.text().strip()
        pwd = self.pwd_input.text().strip()
        if not url or not pwd:
            self.error_label.setText("Please enter both server URL and password.")
            return False

        if self.save_checkbox.isChecked():
            try:
                url_lines = []
                if os.path.exists(SETTINGS_FILE):
                    with open(SETTINGS_FILE, 'r') as f:
                        for line in f:
                            if line.startswith("FOLDER:") or line.startswith("TOKEN:"):
                                url_lines.append(line)
                enc_pwd = self.encrypt(pwd)
                url_lines.append(f"ACTUAL_URL:{url}\n")
                url_lines.append(f"ACTUAL_PWD:{enc_pwd}\n")
                with open(SETTINGS_FILE, 'w') as f:
                    f.writelines(url_lines)
            except Exception as e:
                self.error_label.setText(f"Error saving credentials: {e}")
                return False

        ok = self.controller.authorize_actual(url, pwd)
        if not ok:
            self.error_label.setText("Failed to connect to Actual server with given credentials.")
            return False

        parent = self.window()
        if hasattr(parent, 'go_to_page') and hasattr(parent, 'pages_stack'):
            idx = parent.pages_stack.indexOf(self)
            if idx >= 0:
                parent.go_to_page(2)  # logical step for account selection
                return True
        return False

    def load_saved(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    for line in f:
                        if line.startswith('ACTUAL_URL:'):
                            self.url_input.setText(line.split('ACTUAL_URL:', 1)[1].strip())
                        elif line.startswith('ACTUAL_PWD:'):
                            enc = line.split('ACTUAL_PWD:', 1)[1].strip()
                            try:
                                self.pwd_input.setText(self.decrypt(enc))
                            except Exception:
                                pass
            except Exception:
                pass

    def encrypt(self, text: str) -> str:
        key = self._load_key()
        f = Fernet(key)
        return f.encrypt(text.encode()).decode()

    def decrypt(self, token: str) -> str:
        key = self._load_key()
        f = Fernet(key)
        return f.decrypt(token.encode()).decode()

    def _load_key(self) -> bytes:
        if not os.path.exists(KEY_FILE):
            key = Fernet.generate_key()
            with open(KEY_FILE, 'wb') as f:
                f.write(key)
            return key
        with open(KEY_FILE, 'rb') as f:
            return f.read()

