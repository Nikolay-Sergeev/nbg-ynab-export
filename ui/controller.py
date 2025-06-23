# ui/controller.py
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from services.ynab_client import YnabClient
from services.conversion_service import ConversionService
import re


# --- Worker Classes --- #
class BudgetFetchWorker(QObject):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, ynab_client):
        super().__init__()
        self.ynab_client = ynab_client

    def run(self):
        try:
            budgets = self.ynab_client.get_budgets()
            self.finished.emit(budgets)
        except Exception as e:
            err_msg = f"Failed to fetch budgets: {e}"
            self.error.emit(err_msg)


class AccountFetchWorker(QObject):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, ynab_client, budget_id):
        super().__init__()
        self.ynab_client = ynab_client
        self.budget_id = budget_id

    def run(self):
        try:
            accounts = self.ynab_client.get_accounts(self.budget_id)
            self.finished.emit(accounts)
        except Exception as e:
            err_msg = f"Failed to fetch accounts: {e}"
            self.error.emit(err_msg)


class TransactionFetchWorker(QObject):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, ynab_client, budget_id, account_id):
        super().__init__()
        self.ynab_client = ynab_client
        self.budget_id = budget_id
        self.account_id = account_id

    def run(self):
        try:
            txns = self.ynab_client.get_transactions(self.budget_id, self.account_id)
            self.finished.emit(txns)
        except Exception as e:
            err_msg = f"Failed to fetch transactions: {e}"
            self.error.emit(err_msg)


class DuplicateCheckWorker(QObject):
    finished = pyqtSignal(list, set)
    error = pyqtSignal(str)

    def __init__(self, converter, file_path, budget_id, account_id, ynab_client):
        super().__init__()
        self.converter = converter
        self.file_path = file_path
        self.budget_id = budget_id
        self.account_id = account_id
        self.ynab_client = ynab_client

    def run(self):
        try:
            df = self.converter.convert_to_ynab(self.file_path)
            # Fetch the 50 most recent YNAB transactions for duplicate checking
            from datetime import datetime, timedelta
            since_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
            prev = self.ynab_client.get_transactions(self.budget_id, self.account_id, count=50, since_date=since_date)
            records = df.to_dict('records')
            
            # Normalize and clean payee/memo text for matching
            def normalize(s):
                return (s or "").strip().lower()
            def clean_text(s):
                t = normalize(s)
                for prefix in ["3d secure ecommerce αγορά - ", "3d secure ", "e-commerce αγορά - "]:
                    if t.startswith(prefix):
                        t = t[len(prefix):]
                # Remove suffixes like " virtual"
                if t.endswith(" virtual"):
                    t = t[:-len(" virtual")].strip()
                return t
            # Build set of keys from API transactions
            keys_prev = set()
            for d in prev:
                date_prev = d.get("date")
                payee_prev = clean_text(d.get("import_payee_name") or d.get("payee_name"))
                memo_prev = clean_text(d.get("memo"))
                amt_prev = d.get("amount")  # milliunits
                keys_prev.add((date_prev, payee_prev, amt_prev, memo_prev))
            # Identify duplicates in imported records
            dup_idx = set()
            for i, r in enumerate(records):
                date_csv = r.get("Date")
                payee_csv = clean_text(r.get("Payee"))
                memo_csv = clean_text(r.get("Memo"))
                try:
                    amt_csv = int(round(float(r.get("Amount", 0)) * 1000))
                except:
                    amt_csv = None
                is_transfer_csv = payee_csv.startswith("transfer :")
                for (date_prev, payee_prev, amt_prev, memo_prev) in keys_prev:
                    is_transfer_prev = payee_prev.startswith("transfer :")
                    if date_csv == date_prev and amt_csv == amt_prev:
                        if is_transfer_csv or is_transfer_prev:
                            # Fuzzy memo match: ignore non-word chars, lowercase, compare first 15 chars
                            norm_memo_csv = re.sub(r"\W", "", memo_csv.lower())
                            norm_memo_prev = re.sub(r"\W", "", memo_prev.lower())
                            if norm_memo_csv[:15] == norm_memo_prev[:15]:
                                dup_idx.add(i)
                                break
                        else:
                            if payee_csv == payee_prev and memo_csv == memo_prev:
                                dup_idx.add(i)
                                break
            self.finished.emit(records, dup_idx)
        except Exception as e:
            err_msg = f"Failed to check duplicates: {e}"
            self.error.emit(err_msg)


class UploadWorker(QObject):
    finished = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, ynab_client, budget_id, account_id, transactions):
        super().__init__()
        self.ynab_client = ynab_client
        self.budget_id = budget_id
        self.account_id = account_id
        self.transactions = transactions

    def run(self):
        try:
            # Use correct YnabClient method and parse upload count
            response = self.ynab_client.upload_transactions(self.budget_id, self.transactions)
            # YNAB API returns new transaction ids in response['data']['transaction_ids'] or count in response['data']['transactions']
            uploaded = 0
            if response and 'data' in response:
                if 'transaction_ids' in response['data']:
                    uploaded = len(response['data']['transaction_ids'])
                elif 'transactions' in response['data']:
                    uploaded = len(response['data']['transactions'])
            self.finished.emit(uploaded)
        except Exception as e:
            err_msg = f"Failed to upload transactions: {e}"
            self.error.emit(err_msg)


# --- Controller Class --- #
class WizardController(QObject):
    """
    Controller for the Qt wizard: handles API and conversion operations in background, emits signals to update UI.
    """
    budgetsFetched = pyqtSignal(list)
    accountsFetched = pyqtSignal(list)
    transactionsFetched = pyqtSignal(list)
    duplicatesFound = pyqtSignal(list, set)
    uploadFinished = pyqtSignal(int)
    errorOccurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ynab = None
        self.converter = ConversionService()
        self.worker = None
        self.worker_thread = None

    def _cleanup_thread(self):
        if self.worker_thread is not None:
            if self.worker_thread.isRunning():
                self.worker_thread.quit()
                if not self.worker_thread.wait(3000): 
                     self.worker_thread.terminate()
                     self.worker_thread.wait() 
            self.worker = None
            self.worker_thread = None

    def authorize(self, token: str, save: bool):
        """Store token and optionally persist it via UI settings."""
        self.ynab = YnabClient(token)
        try:
            # Token persistence not implemented; skip save_token
            pass
        except Exception as e:
            self.errorOccurred.emit(str(e))

    def fetch_budgets(self):
        """Fetch budgets from YNAB API."""
        if not self.ynab:
             self.errorOccurred.emit("YNAB client not initialized.")
             return
        self._cleanup_thread()
        self.worker_thread = QThread()
        self.worker = BudgetFetchWorker(self.ynab)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.budgetsFetched)
        self.worker.error.connect(self.errorOccurred)
        self.worker.finished.connect(self._cleanup_thread)
        self.worker.error.connect(self._cleanup_thread)

        self.worker_thread.start()

    def fetch_accounts(self, budget_id: str):
        """Fetch accounts under a given budget."""
        if not self.ynab:
             self.errorOccurred.emit("YNAB client not initialized.")
             return
        self._cleanup_thread()
        self.worker_thread = QThread()
        self.worker = AccountFetchWorker(self.ynab, budget_id)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.accountsFetched)
        self.worker.error.connect(self.errorOccurred)
        self.worker.finished.connect(self._cleanup_thread)
        self.worker.error.connect(self._cleanup_thread)

        self.worker_thread.start()

    def fetch_transactions(self, budget_id: str, account_id: str):
        """Fetch transactions for an account."""
        if not self.ynab:
             self.errorOccurred.emit("YNAB client not initialized.")
             return
        self._cleanup_thread()
        self.worker_thread = QThread()
        self.worker = TransactionFetchWorker(self.ynab, budget_id, account_id)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.transactionsFetched)
        self.worker.error.connect(self.errorOccurred)
        self.worker.finished.connect(self._cleanup_thread)
        self.worker.error.connect(self._cleanup_thread)

        self.worker_thread.start()

    def check_duplicates(self, file_path: str, budget_id: str, account_id: str):
        """Convert file and detect duplicates against YNAB transactions."""
        self._cleanup_thread()
        self.worker_thread = QThread()
        self.worker = DuplicateCheckWorker(self.converter, file_path, budget_id, account_id, self.ynab)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.duplicatesFound)
        self.worker.error.connect(self.errorOccurred)
        self.worker.finished.connect(self._cleanup_thread)
        self.worker.error.connect(self._cleanup_thread)

        self.worker_thread.start()

    def upload_transactions(self, budget_id: str, account_id: str, transactions: list):
        """Upload new transactions to YNAB."""
        if not self.ynab:
             self.errorOccurred.emit("YNAB client not initialized.")
             return
        self._cleanup_thread()
        self.worker_thread = QThread()
        self.worker = UploadWorker(self.ynab, budget_id, account_id, transactions)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.uploadFinished)
        self.worker.error.connect(self.errorOccurred)
        self.worker.finished.connect(self._cleanup_thread)
        self.worker.error.connect(self._cleanup_thread)

        self.worker_thread.start()
