from PyQt5.QtWidgets import (
    QWizardPage,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHBoxLayout,
    QFrame,
    QAbstractItemView,
    QHeaderView,
    QSizePolicy,
    QMessageBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtSvg import QSvgWidget

import os
import logging

logger = logging.getLogger(__name__)


class TransactionsPage(QWizardPage):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setTitle("Latest Transactions")
        self.setFinalPage(False)

        card = QFrame()
        card.setObjectName("card-panel")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(8, 8, 8, 8)
        card_layout.setSpacing(16)

        self.label = QLabel("Latest 5 transactions in this account:")
        self.label.setProperty('role', 'title')
        self.label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.label)

        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../resources/icons/error.svg'))
        # Setup error icon without crashing on SVG
        try:
            self.error_icon = QSvgWidget(icon_path)
            self.error_icon.setFixedSize(24, 24)
            self.error_icon.hide()
        except Exception:
            self.error_icon = QLabel()
            self.error_icon.hide()
        self.error_label = QLabel("")
        self.error_label.setObjectName("error-label")
        self.error_label.setWordWrap(True)
        icon_label_layout = QHBoxLayout()
        icon_label_layout.addWidget(self.error_icon)
        icon_label_layout.addWidget(self.error_label, 1)
        icon_label_layout.addStretch()
        card_layout.addLayout(icon_label_layout)

        spinner_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../resources/icons/spinner.svg'))
        # Setup spinner without crashing on SVG
        try:
            self.spinner = QSvgWidget(spinner_path)
            self.spinner.setFixedSize(36, 36)
            self.spinner.hide()
        except Exception:
            self.spinner = QLabel()
            self.spinner.hide()
        card_layout.addWidget(self.spinner, alignment=Qt.AlignCenter)

        self.cache_label = QLabel("")
        card_layout.addWidget(self.cache_label)

        self.table = QTableWidget()
        self.table.setObjectName("transactions-table")  # Add object name for styling
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Make read-only
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)  # Select whole rows
        self.table.setAlternatingRowColors(True)  # Enable alternating colors for QSS
        self.table.verticalHeader().setVisible(False)  # Hide row numbers
        self.table.setShowGrid(False)  # Hide grid lines, use borders in QSS if needed
        card_layout.addWidget(self.table)

        self.refresh_btn = QPushButton("Refresh")
        card_layout.addWidget(self.refresh_btn)
        self.refresh_btn.clicked.connect(self.on_refresh_clicked)
        card_layout.addStretch(1)

        # Navigation buttons now handled by main window

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(card)
        self.setLayout(main_layout)

        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)

        self.controller.transactionsFetched.connect(self.on_transactions_fetched)
        self.controller.errorOccurred.connect(self.on_error)
        self._cache = None
        self._cache_ids = (None, None)

    def initializePage(self):
        self.error_label.setText("")
        self.error_icon.hide()
        self.spinner.hide()
        self.cache_label.setText("")
        self.fetch_transactions()

    def fetch_transactions(self):
        if not self.controller.ynab:
            QMessageBox.critical(self, "Error", "YNAB client not initialized. Please re-enter your token.")
            return
        # Get selected IDs from the account selection page
        parent = self.window()
        if hasattr(parent, "pages_stack") and parent.pages_stack.count() > 2:
            account_page = parent.pages_stack.widget(2)
            if hasattr(account_page, "get_selected_ids"):
                budget_id, account_id = account_page.get_selected_ids()
            else:
                logger.error("[TransactionsPage] Cannot get selected IDs; account page missing method")
                return
        else:
            logger.error("[TransactionsPage] Cannot get selected IDs; pages_stack not found")
            return
        if budget_id and account_id:
            # Use cache if possible
            if self._cache and self._cache_ids == (budget_id, account_id):
                self.cache_label.setText("Using cached transactions")
                self.spinner.hide()
                self.on_transactions_fetched(self._cache)
                return
            self.cache_label.setText("")
            self.spinner.show()
            try:
                # Limit to the latest 5 transactions for quick preview
                self.controller.fetch_transactions(budget_id, account_id, count=5)
            except Exception as e:
                self.spinner.hide()
                self.error_icon.show()
                self.error_label.setText(f"Failed to fetch transactions: {str(e)}")

    def on_transactions_fetched(self, txns):
        try:
            self.spinner.hide()
            # Cache for session
            # Get selected IDs from the account selection page
            parent = self.window()
            if hasattr(parent, "pages_stack") and parent.pages_stack.count() > 2:
                account_page = parent.pages_stack.widget(2)
                if hasattr(account_page, "get_selected_ids"):
                    budget_id, account_id = account_page.get_selected_ids()
                else:
                    logger.error("[TransactionsPage] Cannot get selected IDs; account page missing method")
                    return
            else:
                logger.error("[TransactionsPage] Cannot get selected IDs; pages_stack not found")
                return
            self._cache = txns
            self._cache_ids = (budget_id, account_id)
            # Only show last 5, sorted by date desc if possible
            if txns and 'date' in txns[0]:
                txns = sorted(txns, key=lambda x: x['date'], reverse=True)[:5]

            # Define columns to display and their headers
            columns_to_show = {
                'date': 'Date',
                'payee_name': 'Payee',
                'amount': 'Amount',
                'memo': 'Memo'
            }

            self.table.setRowCount(len(txns))
            self.table.setColumnCount(len(columns_to_show))
            self.table.setHorizontalHeaderLabels(columns_to_show.values())

            for row, txn in enumerate(txns):
                for col, key in enumerate(columns_to_show.keys()):
                    raw_value = txn.get(key, '')  # Use .get() for safety

                    # Format specific columns
                    if key == 'amount':
                        # Amount is in milliunits (e.g., 12340 = $12.34)
                        try:
                            milliunits = int(raw_value)
                            amount_str = f"{milliunits / 1000.0:.2f}"
                            item = QTableWidgetItem(amount_str)
                            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        except (ValueError, TypeError):
                            item = QTableWidgetItem(str(raw_value))  # Fallback
                    elif key == 'date':
                        item = QTableWidgetItem(str(raw_value))
                        # Optionally parse and reformat date if needed
                    else:
                        # Handle potential None values for payee/memo
                        item = QTableWidgetItem(str(raw_value) if raw_value is not None else "")

                    self.table.setItem(row, col, item)

            # Adjust column widths
            header = self.table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.ResizeToContents)
            # Stretch last column (Memo) if possible
            if self.table.columnCount() > 0:
                header.setSectionResizeMode(self.table.columnCount() - 1, QHeaderView.Stretch)

            self.error_icon.hide()
            self.error_label.setText("")
        except Exception as e:
            self.spinner.hide()
            self.error_icon.show()
            msg = str(e)
            self.error_label.setText(f"Error displaying transactions: {msg}")

    def on_refresh_clicked(self):
        self._cache = None
        self._cache_ids = (None, None)
        self.cache_label.setText("Fetching fresh data...")
        self.spinner.show()
        self.fetch_transactions()

    def validate_and_proceed(self):
        """Validate page and proceed to next step if valid"""
        logger.info("[TransactionsPage] validate_and_proceed called")
        # Navigation now handled by parent window
        parent = self.window()
        if hasattr(parent, "go_to_page") and hasattr(parent, "pages_stack"):
            current_index = parent.pages_stack.indexOf(self)
            if current_index >= 0:
                parent.go_to_page(current_index + 1)
                return True

        logger.error("[TransactionsPage] No navigation method found")
        return False

    def isComplete(self):
        # Always allow navigation
        return True

    def on_error(self, msg: str):
        """Surface API errors directly on the transactions step."""
        self.spinner.hide()
        self.error_icon.show()
        self.error_label.setText(msg)
        # Also clear cached data to force refetch on retry
        self._cache = None
        self._cache_ids = (None, None)
