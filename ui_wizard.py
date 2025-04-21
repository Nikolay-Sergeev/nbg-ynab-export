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
from services.ynab_client import YnabClient
from services.conversion_service import ConversionService
import logging

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
        self.selected_file_path = None

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
        import os
        self.selected_file_path = file_path
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
        return bool(self.selected_file_path)

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
            try:
                ynab = YnabClient(token)
                budgets = ynab.get_budgets()
                self.budgets = budgets
                self.budget_combo.clear()
                for b in budgets:
                    self.budget_combo.addItem(b['name'], b['id'])
                if budgets:
                    self.selected_budget_id = budgets[0]['id']
                    self.fetch_accounts()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to fetch budgets: {str(e)}")
            self.fetched = True

    def fetch_accounts(self):
        token = self.get_token_func()
        budget_id = self.selected_budget_id
        try:
            ynab = YnabClient(token)
            accounts = ynab.get_accounts(budget_id)
            self.accounts = accounts
            self.account_combo.clear()
            for a in accounts:
                if not a['deleted'] and not a['closed']:
                    self.account_combo.addItem(a['name'], a['id'])
            if accounts:
                self.selected_account_id = self.account_combo.currentData()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to fetch accounts: {str(e)}")

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
        try:
            ynab = YnabClient(token)
            transactions = ynab.get_transactions(budget_id, account_id, count=5)
            self.spinner.hide()
            transactions = sorted(transactions, key=lambda x: x['date'], reverse=True)[:5]
            self.table.setRowCount(0)
            for i, tx in enumerate(transactions):
                self.table.insertRow(i)
                self.table.setItem(i, 0, QTableWidgetItem(tx['date']))
                self.table.setItem(i, 1, QTableWidgetItem(tx.get('payee_name', '')))
                self.table.setItem(i, 2, QTableWidgetItem(str(tx['amount']/1000)))
                self.table.setItem(i, 3, QTableWidgetItem(tx.get('memo', '')))
            self.error = None
        except Exception as e:
            self.spinner.hide()
            self.error_icon.show()
            msg = str(e)
            if hasattr(e, 'response') and getattr(e.response, 'status_code', None) == 429:
                msg = "API error: Too many requests (rate limit). You have exceeded 200 requests per hour. See YNAB API docs: https://api.ynab.com/#rate-limiting."
            self.error_label.setText(msg)
            self.table.setRowCount(0)
            self.error = msg

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
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Date", "Payee", "Amount", "Memo", "Status", "Skip"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self.table)
        self.setLayout(self.layout)
        self.new_transactions = []
        self.removed_count = 0
        self.upload_btn = None
        self.skipped_rows = set()

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
        # 1. Convert file to YNAB CSV and get DataFrame
        file_path = self.get_import_file_func()
        if not file_path:
            self.info_label.setText("No file selected!")
            return
        try:
            df = ConversionService.convert_to_ynab(file_path)
        except Exception as e:
            self.info_label.setText(f"Processing error: {e}")
            self.spinner.hide()
            return
        self.df = df
        wizard = self.wizard()
        token = self.get_token_func()
        budget_id, account_id = self.get_budget_account_func()
        # 2. Fetch all YNAB transactions since the earliest CSV date
        from datetime import datetime
        def normalize_date(date_str):
            # Try both YNAB (DD/MM/YYYY) and CSV (YYYY-MM-DD) formats
            for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
                try:
                    return datetime.strptime(date_str.strip(), fmt).date()
                except Exception:
                    continue
            return date_str.strip()
        try:
            csv_records = df.to_dict(orient="records")
            earliest_csv_date = min(normalize_date(tx["Date"]) for tx in csv_records if tx.get("Date"))
            ynab = YnabClient(token)
            # Fetch all transactions since earliest date (YNAB API uses ISO format)
            ynab_all = ynab.get_transactions(budget_id, account_id, since_date=str(earliest_csv_date))
        except Exception as e:
            import traceback
            tb_str = traceback.format_exc()
            self.info_label.setText(f"Failed to fetch YNAB transactions: {str(e)}\nTraceback:\n{tb_str}")
            print(f"[DEBUG] Exception in fetching YNAB transactions: {str(e)}\nTraceback:\n{tb_str}")
            self.info_label.setText(f"Failed to fetch YNAB transactions: {str(e)}")
            self.spinner.hide()
            return
        
        # 4. Compare and deduplicate: remove any CSV tx that matches any YNAB tx (not just one-to-one)
        def tx_equal(csv_tx, ynab_tx):
            def norm(s):
                return str(s).strip().lower() if s is not None else ""
            csv_date = normalize_date(csv_tx.get("Date", ""))
            ynab_date = normalize_date(ynab_tx.get("date", ""))
            try:
                csv_amount = float(csv_tx.get("Amount", 0))
            except Exception:
                csv_amount = 0
            try:
                ynab_amount = float(ynab_tx.get("amount", 0)) / 1000
            except Exception:
                ynab_amount = 0
            csv_memo = norm(csv_tx.get("Memo", ""))
            ynab_memo = norm(ynab_tx.get("memo", ""))
            return (
                csv_date == ynab_date and
                csv_amount == ynab_amount and
                csv_memo == ynab_memo
            )
        deduped = []
        for csv_tx in csv_records:
            if not any(tx_equal(csv_tx, ynab_tx) for ynab_tx in ynab_all):
                deduped.append(csv_tx)
        self.new_transactions = deduped
        # Update table
        self.table.setRowCount(0)
        for i, tx in enumerate(self.new_transactions):
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(str(tx.get("Date", ""))))
            self.table.setItem(i, 1, QTableWidgetItem(str(tx.get("Payee", ""))))
            self.table.setItem(i, 2, QTableWidgetItem(str(tx.get("Amount", ""))))
            self.table.setItem(i, 3, QTableWidgetItem(str(tx.get("Memo", ""))))
            self.table.setItem(i, 4, QTableWidgetItem("Ready"))
            # Add skip checkbox
            skip_cb = QCheckBox()
            skip_cb.setChecked(False)
            skip_cb.stateChanged.connect(lambda state, row=i: self.on_skip_checkbox_changed(row, state))
            self.table.setCellWidget(i, 5, skip_cb)
        self.info_label.setText("")
        self.spinner.hide()

    def on_skip_checkbox_changed(self, row, state):
        if state == Qt.Checked:
            self.skipped_rows.add(row)
        else:
            self.skipped_rows.discard(row)

    def get_transactions_to_upload(self):
        # Only include non-skipped transactions
        return [tx for i, tx in enumerate(self.new_transactions) if i not in self.skipped_rows]

    def validatePage(self):
        # Called when Continue is pressed
        self.spinner.show()
        QApplication.processEvents()
        token = self.get_token_func()
        budget_id, account_id = self.get_budget_account_func()
        try:
            transactions_to_upload_raw = self.get_transactions_to_upload()

            # --- FORMAT FOR YNAB API ---
            formatted_transactions = []
            for tx in transactions_to_upload_raw:
                # Convert amount to milliunits (integer)
                try:
                    amount_milliunits = int(round(float(tx.get("Amount", 0)) * 1000))
                except (ValueError, TypeError):
                    # Handle cases where Amount might not be a valid number
                    # Log this error or provide feedback?
                    # For now, skip this transaction or set amount to 0
                    logging.warning(f"Skipping transaction due to invalid amount: {tx}")
                    continue # Or set amount_milliunits = 0 if preferred

                formatted_tx = {
                    "account_id": account_id,
                    "date": str(tx.get("Date", "")), # Ensure date is string YYYY-MM-DD
                    "amount": amount_milliunits,
                    "payee_name": str(tx.get("Payee", "") or ""), # Ensure payee is string
                    "memo": str(tx.get("Memo", "") or "") # Ensure memo is string
                    # Add other fields like 'cleared', 'approved', 'flag_color' if needed
                }
                formatted_transactions.append(formatted_tx)
            # -------------------------

            ynab = YnabClient(token)
            # Pass the *formatted* list to the API client
            if formatted_transactions:
                ynab.upload_transactions(budget_id, formatted_transactions)
            else:
                logging.info("No valid transactions to upload after formatting.")

            # Always set stats, even if nothing uploaded (based on original intent)
            wizard = self.wizard()
            # Stats should reflect the number *attempted* to upload (before potential formatting errors)
            wizard.upload_stats = {'uploaded': len(transactions_to_upload_raw)}
            wizard.uploaded_account_name = ynab.get_account_name(budget_id, account_id)

            self.show_success(f"Successfully added {len(formatted_transactions)} transactions!")
        except requests.exceptions.HTTPError as e:
            msg = f"HTTP error: {e}"
            if hasattr(e, 'response') and getattr(e.response, 'status_code', None) == 429:
                msg = "API error: Too many requests (rate limit). Please wait an hour."
            elif hasattr(e, 'response') and getattr(e.response, 'status_code', None) == 409:
                # Handle potential duplicate import conflict (though dedupe should prevent)
                msg = f"API conflict (409): {e.response.json().get('error', {}).get('detail', str(e))}"
            elif hasattr(e, 'response') and getattr(e.response, 'status_code', None) >= 400 and getattr(e.response, 'status_code', None) < 500:
                # More detailed 4xx error
                details = str(e)
                try:
                    error_json = e.response.json()
                    details = error_json.get('error', {}).get('detail', str(e))
                except ValueError: # Not JSON
                    pass
                msg = f"API error: {getattr(e.response, 'status_code', None)}. Please check your YNAB token, account, and data.\nDetails: {details}"
            elif hasattr(e, 'response') and getattr(e.response, 'status_code', None) >= 500:
                msg = f"YNAB server error (status {getattr(e.response, 'status_code', None)}). Please try again later."
            self.show_error(msg)
        except Exception as e:
            logging.exception("An unexpected error occurred during upload validation.") # Log stack trace
            msg = f"An unexpected error occurred: {str(e)}"
            self.show_error(msg)
        self.spinner.hide()
        return True

class FinishPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Step 6: Import Complete")
        layout = QVBoxLayout()
        self.label = QLabel()
        self.label.setProperty('role', 'title')
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.stats = None
        self.account_name = None

    def initializePage(self):
        wizard = self.wizard()
        # Try to get stats from wizard
        stats = getattr(wizard, 'upload_stats', None)
        account_name = getattr(wizard, 'uploaded_account_name', None)
        if stats and account_name:
            if stats['uploaded'] == 0:
                text = f"<b>No new transactions were uploaded to <b>{account_name}</b>.</b><br><br>"
                text += "You may now close the wizard."
            else:
                text = f"<b>Import complete!</b><br><br>"
                text += f"<span style='font-size:18px;color:#1976d2;'>"
                text += f"<b>{stats['uploaded']}</b> transaction{'s' if stats['uploaded'] != 1 else ''} uploaded to <b>{account_name}</b>."
                text += "</span><br><br>"
                text += "You may now close the wizard."
        else:
            text = "<b>Import complete!</b> You may now close the wizard."
        self.label.setText(text)
        self.wizard().setButtonText(QWizard.FinishButton, "Finish & Exit")
        self.wizard().setButtonLayout([QWizard.BackButton, QWizard.FinishButton])

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
            lambda: self.import_file_page.selected_file_path
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
