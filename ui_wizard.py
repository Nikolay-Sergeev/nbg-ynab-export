import os
import sys
from PyQt5.QtWidgets import (
    QApplication, QWizard, QWizardPage, QLabel, QVBoxLayout, QPushButton, QFileDialog, QLineEdit, QMessageBox, QComboBox, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView, QHBoxLayout
)
from PyQt5.QtSvg import QSvgWidget, QSvgRenderer
from PyQt5.QtGui import QIcon, QPixmap, QPainter
from PyQt5.QtCore import Qt, QTimer
import requests
import pandas as pd
import tempfile
from cryptography.fernet import Fernet
from main import convert_nbg_to_ynab

# Use settings.txt and settings.key in the user's home directory
HOME_DIR = os.path.expanduser("~")
SETTINGS_DIR = os.path.join(HOME_DIR, ".nbg-ynab-export")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "nbg_ynab_settings.txt")
KEY_FILE = os.path.join(SETTINGS_DIR, "nbg_ynab_settings.key")

# Ensure settings directory exists
os.makedirs(SETTINGS_DIR, exist_ok=True)

def generate_key():
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    return key

def load_key():
    if not os.path.exists(KEY_FILE):
        return generate_key()
    with open(KEY_FILE, "rb") as f:
        return f.read()

def encrypt_token(token):
    key = load_key()
    f = Fernet(key)
    return f.encrypt(token.encode()).decode()

def decrypt_token(token_enc):
    key = load_key()
    f = Fernet(key)
    return f.decrypt(token_enc.encode()).decode()

class SpinnerWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        spinner_path = os.path.join(os.path.dirname(__file__), "icons", "spinner.svg")
        self.setFixedSize(48, 48)
        self.setAlignment(Qt.AlignCenter)
        if os.path.exists(spinner_path):
            self.setStyleSheet("background: transparent;")
            self.setText(f'<img src="{spinner_path}" width="48" height="48"/>')
        else:
            self.setText("Loading...")
        self.hide()

class ImportFilePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Step 1: Import NBG or Revolut Export")
        layout = QVBoxLayout()
        self.label = QLabel("Select an NBG or Revolut export file (CSV/XLSX):")
        self.label.setProperty('role', 'title')
        # SVG upload icon
        self.upload_icon = QSvgWidget(os.path.join(os.path.dirname(__file__), "icons", "upload.svg"))
        self.upload_icon.setFixedSize(48, 48)
        self.upload_icon.setToolTip("Drag and drop file here or click Browse")
        self.file_path_input = QLineEdit()
        self.file_path_input.setReadOnly(True)
        self.file_path_input.setMinimumHeight(60)  
        self.file_path_input.setStyleSheet("font-size:16px;")
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_file)
        # Spinner for file processing
        self.spinner = SpinnerWidget()
        # Drag and drop support
        self.file_path_input.setAcceptDrops(True)
        self.file_path_input.installEventFilter(self)
        layout.addWidget(self.label)
        icon_input_layout = QHBoxLayout()
        icon_input_layout.setContentsMargins(0, 0, 0, 0)
        icon_input_layout.setSpacing(8)
        icon_input_layout.addWidget(self.upload_icon, 0)
        icon_input_layout.addWidget(self.file_path_input, 1)
        layout.addLayout(icon_input_layout)
        layout.addWidget(self.browse_btn)
        layout.addWidget(self.spinner, alignment=Qt.AlignCenter)
        self.setLayout(layout)
        self.last_folder = self.load_last_folder()

    def load_last_folder(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    lines = f.readlines()
                for line in lines:
                    if line.startswith("FOLDER:"):
                        return line.strip().split("FOLDER:",1)[1]
            except Exception:
                pass
        return ""

    def save_last_folder(self, folder):
        # Save folder path in settings.txt (append or update)
        lines = []
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                lines = f.readlines()
        # Remove any old folder line
        lines = [l for l in lines if not l.startswith("FOLDER:")]
        lines.append(f"FOLDER:{folder}\n")
        with open(SETTINGS_FILE, "w") as f:
            f.writelines(lines)

    def set_file_and_remember_folder(self, file_path):
        # Only show filename, not full path
        import os
        self.file_path_input.setText(os.path.basename(file_path))
        if os.path.isfile(file_path):
            folder = os.path.dirname(file_path)
            self.save_last_folder(folder)
            self.last_folder = folder
        self.completeChanged.emit()

    def browse_file(self):
        start_dir = self.last_folder if self.last_folder else ""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File", start_dir, "CSV/XLSX Files (*.csv *.xlsx *.xls)")
        if file_path:
            self.set_file_and_remember_folder(file_path)

    def eventFilter(self, source, event):
        if source == self.file_path_input:
            if event.type() == event.DragEnter:
                if event.mimeData().hasUrls():
                    event.accept()
                    return True
            elif event.type() == event.Drop:
                if event.mimeData().hasUrls():
                    file_path = event.mimeData().urls()[0].toLocalFile()
                    if file_path.lower().endswith(('.csv', '.xlsx', '.xls')):
                        self.set_file_and_remember_folder(file_path)
                    event.accept()
                    return True
        return super().eventFilter(source, event)

    def isComplete(self):
        return bool(self.file_path_input.text())

    def initializePage(self):
        # If file was entered by user via other means (e.g., drag/drop/fill), remember folder
        file_path = self.file_path_input.text()
        if file_path:
            self.set_file_and_remember_folder(file_path)

class YNABAuthPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Step 2: Authorize with YNAB")
        layout = QVBoxLayout()
        self.label = QLabel("Paste your YNAB Personal Access Token (https://api.ynab.com/):")
        self.label.setProperty('role', 'title')
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.Password)
        self.save_checkbox = QCheckBox("Save token securely on this device")
        layout.addWidget(self.label)
        layout.addWidget(self.token_input)
        layout.addWidget(self.save_checkbox)
        self.setLayout(layout)
        self.token_valid = False
        self._auto_validated = False
        self.load_saved_token()
        self.token_input.textChanged.connect(self.completeChanged)

    def load_saved_token(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    enc_token = f.read().strip()
                token = decrypt_token(enc_token)
                self.token_input.setText(token)
                self.save_checkbox.setChecked(True)
                self._auto_validated = True
            except Exception:
                pass

    def validate_token(self):
        pass

    def isComplete(self):
        # Allow continue if token field is not empty
        return bool(self.token_input.text().strip())

    def get_token(self):
        # Always return the current value of the token field
        return self.token_input.text().strip()

    def nextId(self):
        # Always save token to file before leaving this page
        token = self.token_input.text().strip()
        if token:
            from cryptography.fernet import Fernet
            import base64
            import os
            if not os.path.exists(KEY_FILE):
                key = Fernet.generate_key()
                with open(KEY_FILE, "wb") as f:
                    f.write(key)
            else:
                with open(KEY_FILE, "rb") as f:
                    key = f.read()
            fernet = Fernet(key)
            enc_token = fernet.encrypt(token.encode()).decode()
            with open(SETTINGS_FILE, "w") as f:
                f.write(enc_token)
        return super().nextId()

class AccountSelectionPage(QWizardPage):
    def __init__(self, get_token_func):
        super().__init__()
        self.setTitle("Step 3: Select Budget and Account")
        self.get_token_func = get_token_func
        self.budgets = []
        self.accounts = []
        self.selected_budget_id = None
        self.selected_account_id = None
        self.layout = QVBoxLayout()
        self.label = QLabel("Select a YNAB budget and account to update:")
        self.label.setProperty('role', 'title')
        self.budget_combo = QComboBox()
        self.account_combo = QComboBox()
        self.budget_combo.currentIndexChanged.connect(self.on_budget_changed)
        self.account_combo.currentIndexChanged.connect(self.on_account_changed)
        self.layout.addWidget(self.label)
        self.layout.addWidget(QLabel("Budget:"))
        self.layout.addWidget(self.budget_combo)
        self.layout.addWidget(QLabel("Account:"))
        self.layout.addWidget(self.account_combo)
        self.setLayout(self.layout)
        self.fetched = False
        self.transactions = []

    def initializePage(self):
        if not self.fetched:
            token = self.get_token_func()
            headers = {"Authorization": f"Bearer {token}"}
            try:
                resp = requests.get("https://api.ynab.com/v1/budgets", headers=headers, timeout=10)
                if resp.status_code == 200:
                    budgets = resp.json()['data']['budgets']
                    self.budgets = budgets
                    self.budget_combo.clear()
                    for b in budgets:
                        self.budget_combo.addItem(b['name'], b['id'])
                    if budgets:
                        self.selected_budget_id = budgets[0]['id']
                        self.fetch_accounts()
                else:
                    QMessageBox.critical(self, "Error", f"Failed to fetch budgets: {resp.status_code}\n{resp.text}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to connect to YNAB API:\n{str(e)}")
            self.fetched = True

    def fetch_accounts(self):
        token = self.get_token_func()
        budget_id = self.selected_budget_id
        headers = {"Authorization": f"Bearer {token}"}
        try:
            resp = requests.get(f"https://api.ynab.com/v1/budgets/{budget_id}/accounts", headers=headers, timeout=10)
            if resp.status_code == 200:
                accounts = resp.json()['data']['accounts']
                self.accounts = accounts
                self.account_combo.clear()
                for a in accounts:
                    if not a['deleted'] and not a['closed']:
                        self.account_combo.addItem(a['name'], a['id'])
                if accounts:
                    self.selected_account_id = self.account_combo.currentData()
            else:
                QMessageBox.critical(self, "Error", f"Failed to fetch accounts: {resp.status_code}\n{resp.text}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to connect to YNAB API:\n{str(e)}")

    def on_budget_changed(self, idx):
        if idx >= 0 and self.budgets:
            self.selected_budget_id = self.budget_combo.itemData(idx)
            self.fetch_accounts()
            self.completeChanged.emit()

    def on_account_changed(self, idx):
        if idx >= 0 and self.accounts:
            self.selected_account_id = self.account_combo.itemData(idx)
            self.completeChanged.emit()

    def isComplete(self):
        return self.selected_budget_id is not None and self.selected_account_id is not None

    def get_selected_budget_account(self):
        return self.selected_budget_id, self.selected_account_id

class TransactionsPage(QWizardPage):
    def __init__(self, get_token_func, get_budget_account_func):
        super().__init__()
        self.setTitle("Step 4: Last 5 Transactions")
        self.get_token_func = get_token_func
        self.get_budget_account_func = get_budget_account_func
        self.layout = QVBoxLayout()
        self.error_icon = QSvgWidget(os.path.join(os.path.dirname(__file__), "icons", "error.svg"))
        self.error_icon.setFixedSize(24, 24)
        self.error_icon.setToolTip("Error")
        self.error_icon.hide()
        self.error_label = QLabel("")
        self.error_label.setObjectName("error-label")
        self.error_label.setWordWrap(True)
        self.error_label.setMinimumWidth(400)
        # Spinner for API fetch
        self.spinner = SpinnerWidget()
        icon_label_layout = QHBoxLayout()
        icon_label_layout.setContentsMargins(0, 0, 0, 0)
        icon_label_layout.setSpacing(8)
        icon_label_layout.addWidget(self.error_icon)
        icon_label_layout.addWidget(self.error_label, 1)
        icon_label_layout.addStretch()
        self.layout.addLayout(icon_label_layout)
        self.layout.addWidget(self.spinner, alignment=Qt.AlignCenter)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Date", "Payee", "Amount", "Memo"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self.table)
        self.setLayout(self.layout)
        self.fetched = False
        self.setMinimumSize(600, 250)
        self.setMaximumSize(600, 250)
        self.error = None

    def initializePage(self):
        self.error_label.setText("")
        self.error_icon.hide()
        self.spinner.show()
        QApplication.processEvents()
        token = self.get_token_func()
        budget_id, account_id = self.get_budget_account_func()
        headers = {"Authorization": f"Bearer {token}"}
        try:
            resp = requests.get(f"https://api.ynab.com/v1/budgets/{budget_id}/accounts/{account_id}/transactions?count=5", headers=headers, timeout=10)
            self.spinner.hide()
            if resp.status_code == 200:
                transactions = resp.json()['data']['transactions']
                transactions = sorted(transactions, key=lambda x: x['date'], reverse=True)[:5]
                self.table.setRowCount(0)
                if transactions:
                    for tx in transactions:
                        row = self.table.rowCount()
                        self.table.insertRow(row)
                        self.table.setItem(row, 0, QTableWidgetItem(str(tx['date'])))
                        self.table.setItem(row, 1, QTableWidgetItem(str(tx.get('payee_name', ''))))
                        self.table.setItem(row, 2, QTableWidgetItem(str(tx['amount']/1000)))
                        self.table.setItem(row, 3, QTableWidgetItem(str(tx.get('memo', ''))))
                self.error = None
            elif resp.status_code == 429:
                self.error_icon.show()
                self.error_label.setText("API error: Too many requests (rate limit). You have exceeded 200 requests per hour. See YNAB API docs: https://api.ynab.com/#rate-limiting.")
                self.table.setRowCount(0)
                self.error = '{"error":{"id":"429","name":"too_many_requests","detail":"Too many requests"}}'
            else:
                self.error_icon.show()
                self.error_label.setText(f"Failed to fetch: {resp.status_code} {resp.text}")
                self.table.setRowCount(0)
                self.error = f"API error: {resp.status_code}"
        except Exception as e:
            self.spinner.hide()
            self.error_icon.show()
            self.error_label.setText(f"Failed to connect to YNAB API: {e}")
            self.table.setRowCount(0)
            self.error = str(e)

    def isComplete(self):
        return self.error is None

    def get_selected_budget_account(self):
        return self.selected_budget_id, self.selected_account_id

class ReviewAndUploadPage(QWizardPage):
    def __init__(self, get_token_func, get_budget_account_func, get_import_file_func):
        super().__init__()
        self.setTitle("Step 5: Review & Upload New Transactions")
        self.get_token_func = get_token_func
        self.get_budget_account_func = get_budget_account_func
        self.get_import_file_func = get_import_file_func
        self.layout = QVBoxLayout()
        # SVG success and error icons
        self.success_icon = QSvgWidget(os.path.join(os.path.dirname(__file__), "icons", "success.svg"))
        self.success_icon.setFixedSize(24, 24)
        self.success_icon.setToolTip("Success")
        self.success_icon.hide()
        self.error_icon = QSvgWidget(os.path.join(os.path.dirname(__file__), "icons", "error.svg"))
        self.error_icon.setFixedSize(24, 24)
        self.error_icon.setToolTip("Error")
        self.error_icon.hide()
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        self.info_label.setObjectName("success-label")
        # Spinner for upload
        self.spinner = SpinnerWidget()
        icon_label_layout = QHBoxLayout()
        icon_label_layout.addWidget(self.success_icon)
        icon_label_layout.addWidget(self.error_icon)
        icon_label_layout.addWidget(self.info_label)
        icon_label_layout.addStretch()
        self.layout.addLayout(icon_label_layout)
        self.layout.addWidget(self.spinner, alignment=Qt.AlignCenter)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Date", "Payee", "Amount", "Memo", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.upload_btn = QPushButton("Add New Transactions to YNAB")
        self.upload_btn.clicked.connect(self.upload_transactions)
        self.layout.addWidget(self.table)
        self.layout.addWidget(self.upload_btn)
        self.setLayout(self.layout)
        self.new_transactions = []
        self.removed_count = 0
        self.upload_btn.setEnabled(False)

    def show_success(self, msg):
        self.spinner.hide()
        self.success_icon.show()
        self.error_icon.hide()
        self.info_label.setText(msg)
        self.info_label.setObjectName("success-label")
        self.info_label.setStyleSheet("")

    def show_error(self, msg):
        self.spinner.hide()
        self.success_icon.hide()
        self.error_icon.show()
        self.info_label.setText(msg)
        self.info_label.setObjectName("error-label")
        self.info_label.setStyleSheet("")

    def initializePage(self):
        self.spinner.show()
        QApplication.processEvents()
        self.info_label.setText("Processing file and checking for duplicates...")
        self.table.setRowCount(0)
        self.upload_btn.setEnabled(False)
        # 1. Parse the imported file into DataFrame
        file_path = self.get_import_file_func()
        if not file_path:
            self.info_label.setText("No file selected!")
            return
        try:
            df = convert_nbg_to_ynab(file_path)
        except Exception as e:
            self.info_label.setText(f"Processing error: {e}")
            return
        # 3. Fetch ALL transactions from YNAB account (cache-aware)
        token = self.get_token_func()
        budget_id, account_id = self.get_budget_account_func()
        wizard = self.wizard()
        # Use cache if possible
        if (hasattr(wizard, 'cached_ynab_transactions') and
            wizard.cached_ynab_transactions is not None and
            wizard.cached_budget_id == budget_id and
            wizard.cached_account_id == account_id):
            all_ynab_tx = wizard.cached_ynab_transactions
        else:
            headers = {"Authorization": f"Bearer {token}"}
            all_ynab_tx = []
            page = 1
            while True:
                resp = requests.get(
                    f"https://api.ynab.com/v1/budgets/{budget_id}/accounts/{account_id}/transactions?page={page}",
                    headers=headers, timeout=15)
                if resp.status_code != 200:
                    self.info_label.setText(f"Failed to fetch YNAB transactions: {resp.status_code}\n{resp.text}")
                    return
                txs = resp.json()['data']['transactions']
                all_ynab_tx.extend(txs)
                if not txs or len(txs) < 30:
                    break
                page += 1
            # Cache results for this session
            wizard.cached_ynab_transactions = all_ynab_tx
            wizard.cached_budget_id = budget_id
            wizard.cached_account_id = account_id
        # ... rest of duplicate logic unchanged ...

    def upload_transactions(self):
        self.spinner.show()
        QApplication.processEvents()
        token = self.get_token_func()
        budget_id, account_id = self.get_budget_account_func()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        to_upload = []
        for tx in self.new_transactions:
            # YNAB expects milliunits for amount
            to_upload.append({
                "account_id": account_id,
                "date": tx['Date'],
                "amount": int(float(tx['Amount']) * 1000),
                "payee_name": tx['Payee'],
                "memo": tx['Memo'],
                "cleared": "cleared",
                "approved": True
            })
        import json
        data = json.dumps({"transactions": to_upload})
        try:
            resp = requests.post(f"https://api.ynab.com/v1/budgets/{budget_id}/transactions", headers=headers, data=data, timeout=20)
            self.spinner.hide()
            if resp.status_code == 201:
                self.show_success(f"Successfully added {len(to_upload)} transactions!")
                self.upload_btn.setEnabled(False)
            elif resp.status_code == 429:
                from datetime import datetime
                import time
                retry_after = resp.headers.get('Retry-After')
                msg = "API rate limit reached (Too Many Requests). You have exceeded 200 requests per hour. "
                if retry_after:
                    try:
                        wait_sec = int(retry_after)
                        mins = wait_sec // 60
                        secs = wait_sec % 60
                        msg += f"Please wait {mins} min {secs} sec and try again. "
                    except Exception:
                        pass
                msg += "See YNAB API docs: https://api.ynab.com/#rate-limiting."
                self.show_error(msg)
            elif resp.status_code == 401:
                self.show_error("API error: Unauthorized (401). Please check your YNAB token and try again.")
            elif resp.status_code >= 400 and resp.status_code < 500:
                self.show_error(f"API error: {resp.status_code}. Please check your YNAB token, account, and data.\nDetails: {resp.text}")
            elif resp.status_code >= 500:
                self.show_error(f"YNAB server error (status {resp.status_code}). Please try again later.")
            else:
                self.show_error(f"Failed to upload: {resp.status_code}\n{resp.text}")
        except requests.exceptions.RequestException as e:
            self.spinner.hide()
            self.show_error(f"Network error during upload: {e}\nPlease check your internet connection and try again.")

class FinishPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Step 6: Ready to Continue")
        layout = QVBoxLayout()
        self.label = QLabel("File imported and YNAB authorized! Click 'Finish' to proceed to the next steps.")
        self.label.setProperty('role', 'title')
        layout.addWidget(self.label)
        self.setLayout(layout)

class NBGYNABWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NBG/Revolut to YNAB Wizard")
        self.setStyleSheet("""
            QWizard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f7fbff, stop:1 #e3f2fd);
                font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            }
            QWizardPage {
                background: #ffffff;
                border-radius: 18px;
                padding: 32px 32px 24px 32px;
                margin: 16px;
                /* box-shadow removed for Qt compatibility */
            }
            QLabel {
                color: #222;
                font-size: 15px;
            }
            QLabel[role='title'] {
                font-size: 22px;
                font-weight: bold;
                color: #1976d2;
                margin-bottom: 16px;
            }
            QLineEdit {
                background: #f5faff;
                border: 2px solid #bbdefb;
                border-radius: 10px;
                padding: 10px 14px;
                font-size: 16px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2196f3, stop:1 #64b5f6);
                color: #fff;
                border: none;
                border-radius: 10px;
                padding: 10px 24px;
                font-size: 16px;
                font-weight: 500;
                margin-top: 8px;
                margin-bottom: 8px;
            }
            QPushButton:hover:enabled {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1976d2, stop:1 #42a5f5);
            }
            QPushButton:disabled {
                background: #e3eaf2;
                color: #a0aec0;
                border: none;
                opacity: 0.7;
            }
            QTableWidget {
                background: #f7fbff;
                border-radius: 10px;
                border: 1px solid #bbdefb;
                font-size: 15px;
                gridline-color: #e3f2fd;
            }
            QHeaderView::section {
                background: #e3f2fd;
                color: #1976d2;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                padding: 6px;
            }
            QTableWidget::item:selected {
                background: #bbdefb;
                color: #222;
            }
            QTableWidget QTableCornerButton::section {
                background: #e3f2fd;
                border-radius: 8px;
            }
            QSvgWidget {
                background: transparent;
            }
            .error-label {
                color: #d32f2f;
                font-weight: bold;
                font-size: 15px;
                border-radius: 8px;
                background: rgba(244, 67, 54, 0.06);
                padding: 8px 12px;
                margin-bottom: 8px;
                animation: fadeIn 0.7s;
            }
            .success-label {
                color: #388e3c;
                font-weight: bold;
                font-size: 15px;
                border-radius: 8px;
                background: rgba(76, 175, 80, 0.08);
                padding: 8px 12px;
                margin-bottom: 8px;
                animation: fadeIn 0.7s;
            }
            @keyframes fadeIn {
                0% { opacity: 0; }
                100% { opacity: 1; }
            }
        """)
        # Rename Cancel to Exit and ensure it's always shown
        self.setButtonText(QWizard.CancelButton, "Exit")
        self.setOption(QWizard.NoCancelButtonOnLastPage, False)
        self.setButtonLayout([
            QWizard.Stretch,
            QWizard.BackButton,
            QWizard.NextButton,
            QWizard.FinishButton,
            QWizard.CancelButton
        ])
        self.import_file_page = ImportFilePage()
        self.ynab_auth_page = YNABAuthPage()
        self.account_selection_page = AccountSelectionPage(self.ynab_auth_page.get_token)
        self.transactions_page = TransactionsPage(self.ynab_auth_page.get_token, self.account_selection_page.get_selected_budget_account)
        self.review_upload_page = ReviewAndUploadPage(
            self.ynab_auth_page.get_token,
            self.account_selection_page.get_selected_budget_account,
            lambda: self.import_file_page.file_path_input.text()
        )
        self.finish_page = FinishPage()
        self.addPage(self.import_file_page)
        self.addPage(self.ynab_auth_page)
        self.addPage(self.account_selection_page)
        self.addPage(self.transactions_page)
        self.addPage(self.review_upload_page)
        self.addPage(self.finish_page)
        # --- Optimization: session cache for YNAB transactions ---
        self.cached_ynab_transactions = None
        self.cached_budget_id = None
        self.cached_account_id = None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Set SVG app icon
    import os
    svg_icon_path = os.path.join(os.path.dirname(__file__), "icons", "app_icon.svg")
    if os.path.exists(svg_icon_path):
        renderer = QSvgRenderer(svg_icon_path)
        pixmap = QPixmap(128, 128)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        app.setWindowIcon(QIcon(pixmap))
    wizard = NBGYNABWizard()
    wizard.show()
    sys.exit(app.exec_())
