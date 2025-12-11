from PyQt5.QtWidgets import (
    QVBoxLayout, QLabel, QComboBox, QFrame, QSizePolicy, QWidget, QWizard
)
from PyQt5.QtCore import Qt, pyqtSignal
from config import get_logger


class AccountSelectionPage(QWidget):
    # Class-level signal definition
    completeChanged = pyqtSignal()

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.logger = get_logger(__name__)

        self.budgets = []
        self.accounts = []
        self.selected_budget_id = None
        self.selected_account_id = None
        self.fetched = False
        self.transactions = []

        # --- Outer layout ---
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("card-panel")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(16)

        self.title_label = QLabel("Select Budget and Account")
        self.title_label.setProperty('role', 'title')
        card_layout.addWidget(self.title_label)

        # Budget label
        self.budget_label = QLabel("Budget:")
        self.budget_label.setStyleSheet("font-size:14px;font-weight:500;color:#333;margin-top:24px;")
        card_layout.addWidget(self.budget_label, alignment=Qt.AlignLeft)
        card_layout.addSpacing(8)

        # Budget dropdown - add directly to layout
        self.budget_combo = QComboBox()
        self.budget_combo.setObjectName("budget-combo")
        self.budget_combo.setMinimumHeight(40)
        self.budget_combo.setMaximumWidth(400)  # Limit width
        self.budget_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.budget_combo.setEditable(False)
        self.budget_combo.setInsertPolicy(QComboBox.NoInsert)
        self.budget_combo.setPlaceholderText("Select a budget")
        self.budget_combo.setCursor(Qt.PointingHandCursor)  # Show hand cursor to indicate it's clickable

        # Add directly to layout
        card_layout.addWidget(self.budget_combo)
        card_layout.addSpacing(16)

        # Account label
        self.account_label = QLabel("Account:")
        self.account_label.setStyleSheet("font-size:14px;font-weight:500;color:#333;margin-top:16px;")
        card_layout.addWidget(self.account_label, alignment=Qt.AlignLeft)
        card_layout.addSpacing(8)

        # Account dropdown - add directly to layout
        self.account_combo = QComboBox()
        self.account_combo.setObjectName("account-combo")
        self.account_combo.setMinimumHeight(40)
        self.account_combo.setMaximumWidth(400)  # Limit width
        self.account_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.account_combo.setEditable(False)
        self.account_combo.setInsertPolicy(QComboBox.NoInsert)
        self.account_combo.setPlaceholderText("Choose account")
        self.account_combo.setCursor(Qt.PointingHandCursor)  # Show hand cursor to indicate it's clickable

        # Add directly to layout
        card_layout.addWidget(self.account_combo)
        card_layout.addSpacing(16)

        # Helper/error label
        self.helper_label = QLabel("Please choose both a budget and an account to continue.")
        self.helper_label.setObjectName("helper-label")
        self.helper_label.setStyleSheet("font-size:12px;color:#666;margin-bottom:0;")
        card_layout.addWidget(self.helper_label, alignment=Qt.AlignLeft)
        card_layout.addStretch(1)

        # Navigation buttons now in main window

        # Final layout
        outer_layout.addWidget(card)
        outer_layout.addStretch(1)
        self.setLayout(outer_layout)
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)

        # Signals
        # Disconnect any existing signals first to avoid duplicate connections
        try:
            self.budget_combo.currentIndexChanged.disconnect()
            self.account_combo.currentIndexChanged.disconnect()
            self.controller.budgetsFetched.disconnect(self.on_budgets_fetched)
            self.controller.accountsFetched.disconnect(self.on_accounts_fetched)
        except Exception:
            pass  # Ignore if not connected

        # Connect signals
        self.budget_combo.currentIndexChanged.connect(self.on_budget_changed)
        self.budget_combo.activated.connect(lambda idx: print(f"Budget combo activated: {idx}"))
        self.account_combo.currentIndexChanged.connect(self.on_account_changed)
        self.account_combo.activated.connect(lambda idx: print(f"Account combo activated: {idx}"))
        self.controller.budgetsFetched.connect(self.on_budgets_fetched)
        self.controller.accountsFetched.connect(self.on_accounts_fetched)
        self.controller.errorOccurred.connect(self.on_error)

        # Set initial state
        self.update_helper()
        self.validate_fields()

    def get_selected_ids(self):
        """Returns the selected budget and account IDs."""
        return self.selected_budget_id, self.selected_account_id

    def showEvent(self, event):
        """Called when the page is shown."""
        self.logger.info("[AccountSelectionPage] showEvent called")
        super().showEvent(event)

        # Reset and re-initialize comboboxes to ensure they're interactive
        self.budget_combo.setEnabled(False)
        self.budget_combo.setEnabled(True)
        self.account_combo.setEnabled(False)
        self.account_combo.setEnabled(True)

        # Give the combo boxes focus to make them more noticeable
        self.budget_combo.setFocus()

    def initializePage(self):
        self.logger.info("[AccountSelectionPage] initializePage called; target=%s client=%s",
                         getattr(self.controller, 'export_target', None),
                         type(getattr(self.controller, 'ynab', None)).__name__)
        if not self.controller.ynab:
            self.logger.info("[AccountSelectionPage] No API client, skipping fetch")
            return
        try:
            self.logger.info("[AccountSelectionPage] Fetching budgets from client=%s",
                             type(self.controller.ynab).__name__)
            self.controller.fetch_budgets()
        except Exception as e:
            self.logger.error("[AccountSelectionPage] Error fetching budgets: %s", e)

    def on_budgets_fetched(self, budgets):
        self.logger.info("[AccountSelectionPage] Budgets fetched: %s",
                         len(budgets) if budgets else 0)
        self.budgets = budgets or []

        # Update the combo box
        self.budget_combo.blockSignals(True)  # Prevent signals during update
        self.budget_combo.clear()

        # Add default selection prompt
        self.budget_combo.addItem("Select a budget", None)

        # Add all budgets from the YNAB API
        if self.budgets:
            for b in self.budgets:
                self.logger.info("[AccountSelectionPage] Adding budget: %s (%s)", b.get('name'), b.get('id'))
                self.budget_combo.addItem(b['name'], b['id'])
        else:
            self.logger.info("[AccountSelectionPage] No budgets received from API")
            # Add a message if no budgets were found
            self.budget_combo.addItem("No budgets found", None)
            # Fallback: allow manual entry for Actual API mode
            try:
                if getattr(self.controller, 'export_target', 'YNAB') == 'ACTUAL_API':
                    self.budget_combo.setEditable(True)
                    self.budget_combo.setPlaceholderText("Enter budget ID")
                    # When user types, update selected id and try fetching accounts
                    self.budget_combo.editTextChanged.connect(self.on_budget_manual_text)
            except Exception as e:
                print(f"[AccountSelectionPage] Error enabling manual budget entry: {e}")

        # Force update the combo box
        self.budget_combo.setCurrentIndex(0)
        self.budget_combo.blockSignals(False)  # Re-enable signals

        # Reset selection and dependent fields
        self.selected_budget_id = None
        self.accounts = []

        # Reset accounts combo box
        self.account_combo.blockSignals(True)  # Prevent signals during update
        self.account_combo.clear()
        self.account_combo.addItem("Select an account", None)
        self.account_combo.setCurrentIndex(0)
        self.account_combo.blockSignals(False)  # Re-enable signals

        self.selected_account_id = None
        self.update_helper()
        self.validate_fields()

    def on_budget_manual_text(self, text: str):
        text = (text or '').strip()
        self.selected_budget_id = text or None
        if self.selected_budget_id and self.controller and getattr(self.controller, 'ynab', None):
            try:
                print(f"[AccountSelectionPage] Manual budget id entered, fetching accounts: {self.selected_budget_id}")
                self.controller.fetch_accounts(self.selected_budget_id)
            except Exception as e:
                print(f"[AccountSelectionPage] Error fetching accounts for manual budget: {e}")
        self.update_helper()
        self.validate_fields()

    def on_accounts_fetched(self, accounts):
        self.logger.info("[AccountSelectionPage] Accounts fetched: %s",
                         len(accounts) if accounts else 0)
        self.accounts = accounts or []

        # Update the account combo box
        self.account_combo.blockSignals(True)  # Prevent signals during update
        self.account_combo.clear()

        # Add default selection prompt
        self.account_combo.addItem("Choose account", None)

        # Add all accounts from the YNAB API
        if self.accounts:
            for a in self.accounts:
                self.logger.info("[AccountSelectionPage] Adding account: %s (%s)", a.get('name'), a.get('id'))
                self.account_combo.addItem(a['name'], a['id'])
        else:
            self.logger.info("[AccountSelectionPage] No accounts received from API")
            # Add a message if no accounts were found
            self.account_combo.addItem("No accounts found", None)
            # Fallback: allow manual entry for Actual API mode
            try:
                if getattr(self.controller, 'export_target', 'YNAB') == 'ACTUAL_API':
                    self.account_combo.setEditable(True)
                    self.account_combo.setPlaceholderText("Enter account ID")
                    self.account_combo.editTextChanged.connect(self.on_account_manual_text)
            except Exception as e:
                print(f"[AccountSelectionPage] Error enabling manual account entry: {e}")

        # Force update the combo box
        self.account_combo.setCurrentIndex(0)
        self.account_combo.blockSignals(False)  # Re-enable signals

        self.selected_account_id = None
        self.update_helper()
        self.validate_fields()

    def mousePressEvent(self, event):
        # Log mouse click events for debugging
        print(f"[AccountSelectionPage] Mouse click at {event.x()}, {event.y()}")
        super().mousePressEvent(event)

    def on_budget_changed(self, idx):
        self.logger.info("[AccountSelectionPage] Budget index changed: %s", idx)
        data = self.budget_combo.itemData(idx)
        self.selected_budget_id = data if data else None
        self.logger.info("[AccountSelectionPage] Selected budget ID: %s", self.selected_budget_id)

        if self.selected_budget_id:
            try:
                self.logger.info("[AccountSelectionPage] Fetching accounts for budget: %s", self.selected_budget_id)
                self.controller.fetch_accounts(self.selected_budget_id)
            except Exception as e:
                self.logger.error("[AccountSelectionPage] Error fetching accounts: %s", e)
        self.selected_account_id = None
        self.account_combo.setCurrentIndex(0)
        self.update_helper()
        self.validate_fields()

        # Force UI update
        self.budget_combo.repaint()

    def on_account_changed(self, idx):
        self.logger.info("[AccountSelectionPage] Account index changed: %s", idx)
        data = self.account_combo.itemData(idx)
        self.selected_account_id = data if data else None
        self.logger.info("[AccountSelectionPage] Selected account ID: %s", self.selected_account_id)
        self.update_helper()
        self.validate_fields()

    def on_account_manual_text(self, text: str):
        text = (text or '').strip()
        self.selected_account_id = text or None
        self.update_helper()
        self.validate_fields()

    def on_error(self, msg: str):
        """Display API errors (e.g., unauthorized) on the page."""
        short_msg = (msg or "").strip().splitlines()[0]
        if len(short_msg) > 300:
            short_msg = short_msg[:300] + "…"
        if "invalid JSON" in short_msg.lower() or "html" in msg.lower():
            short_msg += " — check that your Actual server URL points to the API (e.g., https://host/api)."
        self.helper_label.setText(short_msg)
        self.helper_label.setStyleSheet("font-size:12px;color:#c62828;margin-bottom:0;")
        self.budget_combo.blockSignals(True)
        self.account_combo.blockSignals(True)
        self.budget_combo.clear()
        self.account_combo.clear()
        self.budget_combo.addItem("Unable to load budgets", None)
        self.account_combo.addItem("Unable to load accounts", None)
        self.budget_combo.blockSignals(False)
        self.account_combo.blockSignals(False)
        self.selected_budget_id = None
        self.selected_account_id = None
        self.validate_fields()

    def update_helper(self):
        if not self.selected_budget_id or not self.selected_account_id:
            self.helper_label.setText("Please choose both a budget and an account to continue.")
            self.helper_label.setStyleSheet("font-size:12px;color:#666;margin-bottom:0;")
        else:
            self.helper_label.setText("")

    def validate_fields(self):
        # Check if both budget and account are selected
        self.completeChanged.emit()  # Signal main window to update button states

    def isComplete(self):
        return bool(self.selected_budget_id and self.selected_account_id)

    def on_continue(self):
        if not self.isComplete():
            return
        # Try different navigation methods
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

    def validate_and_proceed(self):
        print("[AccountSelectionPage] validate_and_proceed called")
        if not self.isComplete():
            print("[AccountSelectionPage] Not complete, can't proceed")
            return False

        # Get the selected budget and account IDs
        budget_id, account_id = self.get_selected_ids()
        print(f"[AccountSelectionPage] Selected budget: {budget_id}, account: {account_id}")

        # If we're in stacked widget with parent window
        parent = self.window()
        if hasattr(parent, "go_to_page") and hasattr(parent, "pages_stack"):
            print("[AccountSelectionPage] Using stacked widget navigation")
            current_index = parent.pages_stack.indexOf(self)
            if current_index >= 0:
                parent.go_to_page(current_index + 1)
                return True

        # If not, try wizard navigation
        wizard = self.wizard()
        if wizard:
            print("[AccountSelectionPage] Using wizard navigation")
            wizard.next()
            return True

        print("[AccountSelectionPage] No navigation method found")
        return False

    def go_back(self):
        # Try different navigation methods
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

    def wizard(self):
        """Return the wizard containing this page, or None if not in a wizard."""
        # Try to get the wizard, otherwise return None
        parent = self.parent()
        if isinstance(parent, QWizard):
            return parent
        return None
