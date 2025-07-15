from PyQt5.QtWidgets import (
    QWizardPage, QVBoxLayout, QLabel, QComboBox, QPushButton, 
    QHBoxLayout, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import pyqtSignal, Qt

class AccountSelectionPage(QWizardPage):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setTitle("")  # Hide default title
        
        # State variables
        self.budgets = []
        self.accounts = []
        self.selected_budget_id = None
        self.selected_account_id = None
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Select YNAB Budget and Account")
        title.setProperty('role', 'title')
        layout.addWidget(title)
        layout.addSpacing(10)
        
        # Budget section
        budget_label = QLabel("Budget:")
        budget_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(budget_label)
        
        self.budget_combo = QComboBox(self)
        self.budget_combo.setMinimumHeight(40)
        self.budget_combo.setFixedWidth(400)
        self.budget_combo.addItem("Select a budget", None)
        self.budget_combo.setStyleSheet("""
            font-size: 14px;
            padding: 5px;
            color: black;
            background-color: white;
        """)
        layout.addWidget(self.budget_combo)
        layout.addSpacing(15)
        
        # Account section
        account_label = QLabel("Account:")
        account_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(account_label)
        
        self.account_combo = QComboBox(self)
        self.account_combo.setMinimumHeight(40)
        self.account_combo.setFixedWidth(400)
        self.account_combo.addItem("Select an account", None)
        self.account_combo.setStyleSheet("""
            font-size: 14px;
            padding: 5px;
            color: black;
            background-color: white;
        """)
        layout.addWidget(self.account_combo)
        layout.addSpacing(15)
        
        # Helper/status message
        self.helper_label = QLabel("Please choose both a budget and an account to continue.")
        self.helper_label.setStyleSheet("font-size: 14px; color: #666;")
        layout.addWidget(self.helper_label)
        
        # Debug functionality kept but button removed from UI
        
        # Add stretch to push everything up
        layout.addStretch(1)
        
        # Connect signals
        self.budget_combo.currentIndexChanged.connect(self.on_budget_changed)
        self.account_combo.currentIndexChanged.connect(self.on_account_changed)
        self.controller.budgetsFetched.connect(self.on_budgets_fetched)
        self.controller.accountsFetched.connect(self.on_accounts_fetched)
    
    def add_test_data(self):
        """Add test data to the combo boxes for testing"""
        print("[Debug] Adding test data")
        
        # Add test budgets
        self.budget_combo.clear()
        self.budget_combo.addItem("Select a budget", None)
        self.budget_combo.addItem("Personal Budget", "budget1")
        self.budget_combo.addItem("Business Budget", "budget2")
        self.budget_combo.addItem("Vacation Budget", "budget3")
        
        # Add test accounts
        self.account_combo.clear()
        self.account_combo.addItem("Select an account", None)
        self.account_combo.addItem("Checking Account", "account1")
        self.account_combo.addItem("Savings Account", "account2")
        self.account_combo.addItem("Credit Card", "account3")
        
        print("[Debug] Test data added")
    
    def initializePage(self):
        print("[AccountSelectionPage] initializePage called")
        
        # Auto-add test data if no YNAB client is available
        if not self.controller.ynab:
            print("[AccountSelectionPage] No YNAB client, adding sample data")
            self.add_test_data()
            return
        
        try:
            print("[AccountSelectionPage] Fetching budgets from YNAB API")
            self.controller.fetch_budgets()
        except Exception as e:
            print(f"[AccountSelectionPage] Error fetching budgets: {e}")
            # Add test data as fallback if API fails
            self.add_test_data()
    
    def on_budgets_fetched(self, budgets):
        print(f"[AccountSelectionPage] Budgets fetched: {len(budgets) if budgets else 0}")
        self.budgets = budgets or []
        
        # Update the combo box
        self.budget_combo.blockSignals(True)
        self.budget_combo.clear()
        self.budget_combo.addItem("Select a budget", None)
        
        if self.budgets:
            for b in self.budgets:
                print(f"[AccountSelectionPage] Adding budget: {b['name']} ({b['id']})")
                self.budget_combo.addItem(b['name'], b['id'])
        
        self.budget_combo.setCurrentIndex(0)
        self.budget_combo.blockSignals(False)
        
        # Reset account selection
        self.account_combo.clear()
        self.account_combo.addItem("Select an account", None)
        self.selected_budget_id = None
        self.selected_account_id = None
        self.update_helper()
    
    def on_accounts_fetched(self, accounts):
        print(f"[AccountSelectionPage] Accounts fetched: {len(accounts) if accounts else 0}")
        self.accounts = accounts or []
        
        # Update the combo box
        self.account_combo.blockSignals(True)
        self.account_combo.clear()
        self.account_combo.addItem("Select an account", None)
        
        if self.accounts:
            for a in self.accounts:
                print(f"[AccountSelectionPage] Adding account: {a['name']} ({a['id']})")
                self.account_combo.addItem(a['name'], a['id'])
        
        self.account_combo.setCurrentIndex(0)
        self.account_combo.blockSignals(False)
        
        self.selected_account_id = None
        self.update_helper()
    
    def on_budget_changed(self, idx):
        print(f"[AccountSelectionPage] Budget changed to index {idx}")
        if idx > 0:
            self.selected_budget_id = self.budget_combo.itemData(idx)
            print(f"[AccountSelectionPage] Selected budget: {self.selected_budget_id}")
            
            try:
                self.controller.fetch_accounts(self.selected_budget_id)
            except Exception as e:
                print(f"[AccountSelectionPage] Error fetching accounts: {e}")
        else:
            self.selected_budget_id = None
            
        self.update_helper()
        self.completeChanged.emit()
    
    def on_account_changed(self, idx):
        print(f"[AccountSelectionPage] Account changed to index {idx}")
        if idx > 0:
            self.selected_account_id = self.account_combo.itemData(idx)
            print(f"[AccountSelectionPage] Selected account: {self.selected_account_id}")
        else:
            self.selected_account_id = None
            
        self.update_helper()
        self.completeChanged.emit()
    
    def update_helper(self):
        if not self.selected_budget_id:
            self.helper_label.setText("Please select a budget")
        elif not self.selected_account_id:
            self.helper_label.setText("Please select an account")
        else:
            self.helper_label.setText("Ready to continue!")
            self.helper_label.setStyleSheet("font-size: 14px; color: #2c9f2c; font-weight: bold;")
    
    def isComplete(self):
        return bool(self.selected_budget_id and self.selected_account_id)
    
    def get_selected_ids(self):
        """Returns the selected budget and account IDs."""
        return self.selected_budget_id, self.selected_account_id