from PyQt5.QtWidgets import (
    QWizardPage, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QCheckBox,
    QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt
from urllib.parse import urlparse
import os
from config import SETTINGS_FILE, ACTUAL_SETTINGS_FILE, get_logger, ensure_app_dir
from services import token_manager as _token_manager


class ActualAuthPage(QWizardPage):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setTitle("")
        self.logger = get_logger(__name__)

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
        self.save_checkbox.setChecked(True)
        layout.addWidget(self.save_checkbox, alignment=Qt.AlignLeft)

        # Helper and error
        self.helper_label = QLabel("Your credentials are stored locally.")
        self.helper_label.setObjectName("helper-label")
        self.error_label = QLabel("")
        self.error_label.setObjectName("error-label")
        layout.addWidget(self.helper_label)
        layout.addWidget(self.error_label)
        layout.addStretch(1)
        # Allow copying any server message for easier debugging
        self.error_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.helper_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

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
        self.logger.info("[ActualAuthPage] validate_and_proceed called")
        try:
            url = self.url_input.text().strip()
            pwd = self.pwd_input.text().strip()
            if not url or not pwd:
                self.error_label.setText("Please enter both server URL and password.")
                self.logger.info("[ActualAuthPage] Missing URL or password")
                return False
            parsed = urlparse(url)
            if not parsed.scheme:
                self.error_label.setText("Server URL must include http:// or https://")
                self.logger.info("[ActualAuthPage] Missing URL scheme")
                return False
            scheme = parsed.scheme.lower()
            host = (parsed.hostname or "").lower()
            if scheme not in ("http", "https"):
                self.error_label.setText("Server URL must start with http:// or https://")
                self.logger.info("[ActualAuthPage] Unsupported URL scheme: %s", scheme)
                return False
            if scheme == "http" and host not in ("localhost", "127.0.0.1", "::1"):
                self.error_label.setText("Insecure URL. Use https:// for remote servers.")
                self.logger.info("[ActualAuthPage] Rejected insecure URL: %s", url)
                return False

            if self.save_checkbox.isChecked():
                try:
                    ensure_app_dir()
                    enc_pwd = _token_manager.encrypt_token(pwd).decode()
                    with open(ACTUAL_SETTINGS_FILE, 'w') as f:
                        f.write(f"ACTUAL_URL:{url}\n")
                        f.write(f"ACTUAL_PWD:{enc_pwd}\n")
                    try:
                        os.chmod(ACTUAL_SETTINGS_FILE, 0o600)
                    except OSError:
                        pass
                    # Remove legacy Actual credentials from shared settings file if present.
                    if os.path.exists(SETTINGS_FILE):
                        try:
                            with open(SETTINGS_FILE, 'r') as f:
                                lines = [
                                    ln for ln in f
                                    if not (ln.startswith("ACTUAL_URL:") or ln.startswith("ACTUAL_PWD:"))
                                ]
                            with open(SETTINGS_FILE, 'w') as f:
                                f.writelines(lines)
                            try:
                                os.chmod(SETTINGS_FILE, 0o600)
                            except OSError:
                                pass
                        except Exception:
                            pass
                except Exception as e:
                    self.error_label.setText(f"Error saving credentials: {e}")
                    self.logger.error("[ActualAuthPage] Error saving credentials: %s", e)
                    return False

            ok = self.controller.authorize_actual(url, pwd)
            if not ok:
                msg = getattr(self.controller, "last_error_message", None)
                short_msg = (msg or "Failed to connect to Actual server with given credentials.").strip()
                if "invalid json" in short_msg.lower() or "html" in short_msg.lower():
                    short_msg += "\nHint: ensure the URL points to the Actual API base (e.g., https://host/api)."
                if len(short_msg) > 400:
                    short_msg = short_msg[:400] + "…"
                self.error_label.setText(short_msg)
                self.logger.error("[ActualAuthPage] authorize_actual failed for url=%s; msg=%s", url, msg)
                return False
        except Exception as e:  # Defensive: avoid crashing Qt if anything unexpected happens
            self.error_label.setText(f"Unexpected error: {e}")
            self.logger.exception("[ActualAuthPage] Unexpected error during validation")
            return False

        parent = self.window()
        if hasattr(parent, 'go_to_page') and hasattr(parent, 'pages_stack'):
            idx = parent.pages_stack.indexOf(self)
            if idx >= 0:
                self.logger.info("[ActualAuthPage] Auth succeeded; navigating to AccountSelection")
                parent.go_to_page(2)  # logical step for account selection
                return True
        return False

    def load_saved(self):
        ensure_app_dir()
        # Prefer dedicated Actual settings file.
        if os.path.exists(ACTUAL_SETTINGS_FILE):
            try:
                with open(ACTUAL_SETTINGS_FILE, 'r') as f:
                    for line in f:
                        if line.startswith('ACTUAL_URL:'):
                            self.url_input.setText(line.split('ACTUAL_URL:', 1)[1].strip())
                        elif line.startswith('ACTUAL_PWD:'):
                            enc = line.split('ACTUAL_PWD:', 1)[1].strip()
                            try:
                                self.pwd_input.setText(_token_manager.decrypt_token(enc.encode()))
                            except Exception:
                                pass
                return
            except Exception:
                pass

        # Legacy fallback: read from shared settings.txt and migrate if found.
        if os.path.exists(SETTINGS_FILE):
            legacy_url = None
            legacy_pwd = None
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    for line in f:
                        if line.startswith('ACTUAL_URL:'):
                            legacy_url = line.split('ACTUAL_URL:', 1)[1].strip()
                        elif line.startswith('ACTUAL_PWD:'):
                            legacy_pwd = line.split('ACTUAL_PWD:', 1)[1].strip()
                if legacy_url:
                    self.url_input.setText(legacy_url)
                if legacy_pwd:
                    try:
                        self.pwd_input.setText(_token_manager.decrypt_token(legacy_pwd.encode()))
                    except Exception:
                        pass
                if legacy_url and legacy_pwd:
                    try:
                        with open(ACTUAL_SETTINGS_FILE, 'w') as f:
                            f.write(f"ACTUAL_URL:{legacy_url}\n")
                            f.write(f"ACTUAL_PWD:{legacy_pwd}\n")
                        try:
                            os.chmod(ACTUAL_SETTINGS_FILE, 0o600)
                        except OSError:
                            pass
                    except Exception:
                        pass
            except Exception:
                pass
