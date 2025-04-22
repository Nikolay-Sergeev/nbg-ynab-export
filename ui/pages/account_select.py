from PyQt5.QtWidgets import (
    QWizardPage, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap, QColor
import traceback
import sys  # for platform checks

class StepperWidget(QFrame):
    def __init__(self, step_idx=2, total_steps=4, parent=None):
        super().__init__(parent)
        self.setObjectName("stepper")
        layout = QHBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 24)
        for i in range(total_steps):
            dot = QLabel()
            dot.setFixedSize(18, 18)
            if i <= step_idx:
                dot.setStyleSheet("background:#1976d2;border-radius:9px;border:2px solid #1976d2;")
            else:
                dot.setStyleSheet("background:#fff;border-radius:9px;border:2px solid #b0bec5;")
            layout.addWidget(dot)
            if i < total_steps - 1:
                arrow = QLabel()
                arrow.setPixmap(QPixmap(16, 2))
                arrow.setStyleSheet("background:#b0bec5;")
                arrow.setFixedHeight(2)
                arrow.setFixedWidth(24)
                layout.addWidget(arrow)

class AccountSelectionPage(QWizardPage):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setTitle("")

        self.budgets = []
        self.accounts = []
        self.selected_budget_id = None
        self.selected_account_id = None
        self.fetched = False
        self.transactions = []

        # --- Outer layout ---
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(40, 40, 40, 40)
        outer_layout.addStretch(1)

        # Stepper (3/6)
        stepper = StepperWidget(step_idx=2, total_steps=6)
        outer_layout.addWidget(stepper, alignment=Qt.AlignHCenter)
        indicator = QLabel("3/6")
        indicator.setAlignment(Qt.AlignRight)
        indicator.setStyleSheet("font-size:14px;color:#888;margin-bottom:8px;")
        outer_layout.addWidget(indicator)

        # Card
        card = QFrame()
        card.setObjectName("card-panel")
        card.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        card.setMinimumWidth(420)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(0)
        # Drop shadow (skip on macOS to avoid Qt crash)
        if not sys.platform.startswith('darwin'):
            from PyQt5.QtWidgets import QGraphicsDropShadowEffect
            shadow = QGraphicsDropShadowEffect(card)
            shadow.setBlurRadius(18)
            shadow.setColor(QColor(0,0,0,30))
            shadow.setOffset(0, 2)
            card.setGraphicsEffect(shadow)

        # Title
        title = QLabel("Select your YNAB Account")
        title.setStyleSheet("font-size:20px;font-weight:bold;color:#222;margin-bottom:24px;")
        title.setWordWrap(True)
        card_layout.addWidget(title, alignment=Qt.AlignHCenter)
        card_layout.addSpacing(8)

        # Budget label
        budget_label = QLabel("Budget:")
        budget_label.setStyleSheet("font-size:14px;font-weight:500;color:#333;margin-top:24px;")
        card_layout.addWidget(budget_label, alignment=Qt.AlignLeft)
        card_layout.addSpacing(8)

        # Budget dropdown
        self.budget_combo = QComboBox()
        self.budget_combo.setObjectName("budget-combo")
        self.budget_combo.setMinimumHeight(40)
        self.budget_combo.setMinimumWidth(240)
        self.budget_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.budget_combo.setEditable(False)
        self.budget_combo.setStyleSheet("font-size:15px;border:1px solid #ccc;border-radius:6px;color:#222;background:#fff;padding:6px 32px 6px 12px;")
        self.budget_combo.setInsertPolicy(QComboBox.NoInsert)
        self.budget_combo.setPlaceholderText("Select a budget")
        card_layout.addWidget(self.budget_combo, alignment=Qt.AlignLeft)
        card_layout.addSpacing(16)

        # Account label
        account_label = QLabel("Account:")
        account_label.setStyleSheet("font-size:14px;font-weight:500;color:#333;margin-top:16px;")
        card_layout.addWidget(account_label, alignment=Qt.AlignLeft)
        card_layout.addSpacing(8)

        # Account dropdown
        self.account_combo = QComboBox()
        self.account_combo.setObjectName("account-combo")
        self.account_combo.setMinimumHeight(40)
        self.account_combo.setMinimumWidth(240)
        self.account_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.account_combo.setEditable(False)
        self.account_combo.setStyleSheet("font-size:15px;border:1px solid #ccc;border-radius:6px;color:#222;background:#fff;padding:6px 32px 6px 12px;")
        self.account_combo.setInsertPolicy(QComboBox.NoInsert)
        self.account_combo.setPlaceholderText("Choose account")
        card_layout.addWidget(self.account_combo, alignment=Qt.AlignLeft)
        card_layout.addSpacing(16)

        # Helper/error label
        self.helper_label = QLabel("Please choose both a budget and an account to continue.")
        self.helper_label.setObjectName("helper-label")
        self.helper_label.setStyleSheet("font-size:12px;color:#666;margin-bottom:0;")
        card_layout.addWidget(self.helper_label, alignment=Qt.AlignLeft)
        card_layout.addSpacing(32)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.back_btn = QPushButton("Back")
        self.back_btn.setObjectName("back-btn")
        self.back_btn.setFixedHeight(40)
        self.back_btn.setFixedWidth(100)
        self.back_btn.setStyleSheet("background:#fff;color:#555;border:1px solid #aaa;font-weight:500;")
        self.back_btn.clicked.connect(self.go_back)
        btn_row.addWidget(self.back_btn)
        btn_row.addSpacing(24)
        self.continue_btn = QPushButton("Continue")
        self.continue_btn.setObjectName("continue-btn")
        self.continue_btn.setFixedHeight(40)
        self.continue_btn.setFixedWidth(100)
        self.continue_btn.setStyleSheet("background:#1976d2;color:#fff;font-weight:600;opacity:0.5;")
        self.continue_btn.clicked.connect(self.on_continue)
        btn_row.addWidget(self.continue_btn)
        card_layout.addLayout(btn_row)

        # Final layout
        outer_layout.addWidget(card, alignment=Qt.AlignCenter)
        outer_layout.addStretch(1)
        self.setLayout(outer_layout)

        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)

        # Signals
        self.budget_combo.currentIndexChanged.connect(self.on_budget_changed)
        self.account_combo.currentIndexChanged.connect(self.on_account_changed)
        self.controller.budgetsFetched.connect(self.on_budgets_fetched)
        self.controller.accountsFetched.connect(self.on_accounts_fetched)
        self.update_helper()
        self.validate_fields()

    def get_selected_ids(self):
        """Returns the selected budget and account IDs."""
        return self.selected_budget_id, self.selected_account_id

    def initializePage(self):
        if not self.controller.ynab:
            return
        try:
            self.controller.fetch_budgets()
        except Exception as e:
            pass

    def on_budgets_fetched(self, budgets):
        self.budgets = budgets or []
        self.budget_combo.clear()
        self.budget_combo.addItem("Select a budget", None)
        for b in self.budgets:
            self.budget_combo.addItem(b['name'], b['id'])
        self.selected_budget_id = None
        self.accounts = []
        self.account_combo.clear()
        self.account_combo.addItem("Select an account", None)
        self.selected_account_id = None
        self.update_helper()
        self.validate_fields()

    def on_accounts_fetched(self, accounts):
        self.accounts = accounts or []
        self.account_combo.clear()
        self.account_combo.addItem("Choose account", None)
        for a in self.accounts:
            self.account_combo.addItem(a['name'], a['id'])
        self.selected_account_id = None
        self.update_helper()
        self.validate_fields()

    def on_budget_changed(self, idx):
        data = self.budget_combo.itemData(idx)
        self.selected_budget_id = data if data else None
        if self.selected_budget_id:
            try:
                self.controller.fetch_accounts(self.selected_budget_id)
            except Exception as e:
                pass
        self.selected_account_id = None
        self.account_combo.setCurrentIndex(0)
        self.update_helper()
        self.validate_fields()

    def on_account_changed(self, idx):
        data = self.account_combo.itemData(idx)
        self.selected_account_id = data if data else None
        self.update_helper()
        self.validate_fields()

    def update_helper(self):
        if not self.selected_budget_id or not self.selected_account_id:
            self.helper_label.setText("Please choose both a budget and an account to continue.")
            self.helper_label.setStyleSheet("font-size:12px;color:#666;margin-bottom:0;")
        else:
            self.helper_label.setText("")

    def validate_fields(self):
        valid = bool(self.selected_budget_id and self.selected_account_id)
        self.continue_btn.setEnabled(valid)
        if valid:
            self.continue_btn.setStyleSheet("background:#1976d2;color:#fff;font-weight:600;opacity:1;")
        else:
            self.continue_btn.setStyleSheet("background:#1976d2;color:#fff;font-weight:600;opacity:0.5;")

    def isComplete(self):
        return bool(self.selected_budget_id and self.selected_account_id)

    def on_continue(self):
        if not self.isComplete():
            return
        self.wizard().next()

    def go_back(self):
        self.wizard().back()
