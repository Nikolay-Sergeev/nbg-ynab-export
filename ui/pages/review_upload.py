from PyQt5.QtWidgets import QWizardPage, QVBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHBoxLayout, QCheckBox, QFrame, QSizePolicy
from PyQt5.QtCore import Qt
from .account_select import StepperWidget
import os

class ReviewAndUploadPage(QWizardPage):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setTitle("Step 5: Review & Upload New Transactions")

        card = QFrame()
        card.setObjectName("card-panel")
        card.setFrameShape(QFrame.StyledPanel)
        card.setFrameShadow(QFrame.Raised)
        card.setMinimumWidth(500)
        card.setMaximumWidth(500)
        card.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(16)

        # Stepper (5/6)
        self.stepper = StepperWidget(step_idx=4, total_steps=6)
        card_layout.insertWidget(0, self.stepper)
        indicator = QLabel("5/6")
        indicator.setAlignment(Qt.AlignRight)
        indicator.setStyleSheet("font-size:14px;color:#888;margin-bottom:8px;")
        card_layout.insertWidget(1, indicator)

        self.label = QLabel("Review new transactions and upload to YNAB:")
        self.label.setProperty('role', 'title')
        self.label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.label)

        # Setup success and error icon placeholders
        self.success_icon = QLabel()
        self.success_icon.hide()
        self.error_icon = QLabel()
        self.error_icon.hide()
        self.info_label = QLabel("")
        self.info_label.setObjectName("info-label")
        self.info_label.setWordWrap(True)
        icon_label_layout = QHBoxLayout()
        icon_label_layout.addWidget(self.success_icon)
        icon_label_layout.addWidget(self.error_icon)
        icon_label_layout.addWidget(self.info_label)
        icon_label_layout.addStretch()
        card_layout.addLayout(icon_label_layout)

        # Setup spinner placeholder
        self.spinner = QLabel()
        self.spinner.hide()
        card_layout.addWidget(self.spinner, alignment=Qt.AlignCenter)

        self.table = QTableWidget()
        # Ensure readable font color for table
        self.table.setStyleSheet("color: #222; background: #fff;")
        self.table.setMinimumWidth(700)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        card_layout.addWidget(self.table)

        # Navigation Buttons (Back/Continue, same size, Continue on right)
        nav_layout = QHBoxLayout()
        self.back_btn = QPushButton("Back")
        self.back_btn.setObjectName("back-btn")
        self.back_btn.setFixedWidth(160)
        self.back_btn.setFixedHeight(48)
        self.back_btn.clicked.connect(lambda: self.wizard().back())
        nav_layout.addWidget(self.back_btn)
        nav_layout.addStretch(1)
        self.continue_btn = QPushButton("Continue")
        self.continue_btn.setObjectName("continue-btn")
        self.continue_btn.setFixedWidth(160)
        self.continue_btn.setFixedHeight(48)
        self.continue_btn.clicked.connect(self.on_continue)
        nav_layout.addWidget(self.continue_btn)
        card_layout.addLayout(nav_layout)

        main_layout = QVBoxLayout(self)
        main_layout.addStretch(1)
        main_layout.addWidget(card, alignment=Qt.AlignCenter)
        main_layout.addStretch(1)
        self.setLayout(main_layout)
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)

        self.controller.duplicatesFound.connect(self.on_duplicates_found)
        self.controller.uploadFinished.connect(self.on_upload_finished)
        self.controller.errorOccurred.connect(self.on_error)
        self.records = []
        self.dup_idx = set()
        self.skipped_rows = set()
        self.worker = None

    def initializePage(self):
        if not self.controller.ynab:
            QMessageBox.critical(self, "Error", "YNAB client not initialized. Please re-enter your token.")
            return
        file_path = self.wizard().page(0).file_path
        budget_id, account_id = self.wizard().page(2).get_selected_ids()
        self.skipped_rows = set()
        if file_path and budget_id and account_id:
            try:
                self.controller.check_duplicates(file_path, budget_id, account_id)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error checking duplicates: {str(e)}")

    def on_duplicates_found(self, records, dup_idx):
        try:
            self.records = records
            self.dup_idx = dup_idx
            self.skipped_rows = set(dup_idx)
            self.table.setRowCount(len(records))
            self.table.setColumnCount(len(records[0]) + 2 if records else 0)
            headers = list(records[0].keys()) if records else []
            headers.append("Status")
            headers.append("Skip")
            self.table.setHorizontalHeaderLabels(headers)
            for row, rec in enumerate(records):
                for col, key in enumerate(rec):
                    item = QTableWidgetItem(str(rec[key]))
                    if row in dup_idx:
                        item.setBackground(Qt.yellow)
                    self.table.setItem(row, col, item)
                status = "Duplicate" if row in dup_idx else "Ready"
                self.table.setItem(row, len(rec), QTableWidgetItem(status))
                cb = QCheckBox()
                cb.setChecked(row in dup_idx)
                if row in dup_idx:
                    cb.setEnabled(False)  # Disable checkbox for duplicates
                cb.stateChanged.connect(lambda s, r=row: self.on_skip_checkbox_changed(r, s))
                self.table.setCellWidget(row, len(rec)+1, cb)
            # Always enable Continue button after populating table
            self.continue_btn.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error displaying duplicates: {str(e)}")

    def on_skip_checkbox_changed(self, row, state):
        if state == Qt.Checked:
            self.skipped_rows.add(row)
        else:
            self.skipped_rows.discard(row)

    def upload_transactions(self):
        print("[DEBUG] upload_transactions called")
        budget_id, account_id = self.wizard().page(2).get_selected_ids()
        to_upload = [r for i, r in enumerate(self.records) if i not in self.dup_idx and i not in self.skipped_rows]
        print(f"[DEBUG] to_upload: {len(to_upload)} transactions")
        if not self.controller.ynab:
            print("[DEBUG] YNAB client not initialized")
            QMessageBox.critical(self, "Error", "YNAB client not initialized. Please re-enter your token.")
            return
        if budget_id and account_id and to_upload:
            try:
                formatted = []
                for tx in to_upload:
                    try:
                        amount_milliunits = int(round(float(tx.get("Amount", 0)) * 1000))
                    except (ValueError, TypeError):
                        continue
                    formatted.append({
                        "account_id": account_id,
                        "date": str(tx.get("Date", "")),
                        "amount": amount_milliunits,
                        "payee_name": str(tx.get("Payee", "") or ""),
                        "memo": str(tx.get("Memo", "") or "")
                    })
                print(f"[DEBUG] formatted: {len(formatted)} transactions")
                if formatted:
                    print("[DEBUG] Calling controller.upload_transactions")
                    self.controller.upload_transactions(budget_id, account_id, formatted)
                else:
                    print("[DEBUG] No valid transactions after formatting. Advancing to finish page.")
                    QMessageBox.information(self, "No Valid Transactions", "No valid transactions to upload after formatting.")
                    # Set stats for FinishPage and advance wizard
                    wizard = self.wizard()
                    if not hasattr(wizard, 'upload_stats'):
                        wizard.upload_stats = {}
                    wizard.upload_stats['uploaded'] = 0
                    # Save account name
                    from ui.pages.account_select import AccountSelectionPage
                    acct_page = wizard.page(2)
                    if hasattr(acct_page, 'account_combo'):
                        idx = acct_page.account_combo.currentIndex()
                        acct_name = acct_page.account_combo.itemText(idx)
                        wizard.uploaded_account_name = acct_name
                    else:
                        wizard.uploaded_account_name = None
                    self.continue_btn.setEnabled(True)
                    self.wizard().next()
            except Exception as e:
                print(f"[DEBUG] Exception in upload_transactions: {e}")
                QMessageBox.critical(self, "Error", f"Error uploading transactions: {str(e)}")
        else:
            print("[DEBUG] No budget/account selected or nothing to upload. Advancing to finish page.")
            # Set stats for FinishPage and advance wizard
            wizard = self.wizard()
            if not hasattr(wizard, 'upload_stats'):
                wizard.upload_stats = {}
            wizard.upload_stats['uploaded'] = 0
            from ui.pages.account_select import AccountSelectionPage
            acct_page = wizard.page(2)
            if hasattr(acct_page, 'account_combo'):
                idx = acct_page.account_combo.currentIndex()
                acct_name = acct_page.account_combo.itemText(idx)
                wizard.uploaded_account_name = acct_name
            else:
                wizard.uploaded_account_name = None
            self.continue_btn.setEnabled(True)
            self.wizard().next()

    def on_continue(self):
        print("[DEBUG] Continue button clicked on Step 5")
        # Disable continue button to avoid double submission
        self.continue_btn.setEnabled(False)
        print(f"[DEBUG] Records: {len(getattr(self, 'records', []))}, Duplicates: {len(getattr(self, 'dup_idx', []))}, Skipped: {len(getattr(self, 'skipped_rows', []))}")
        self.upload_transactions()

    def on_upload_finished(self, count):
        self.success_icon.show()
        self.error_icon.hide()
        self.table.setRowCount(0)
        self.info_label.setText(f"Upload complete. {count} transactions uploaded.")
        # Save upload stats and account name to wizard for FinishPage
        wizard = self.wizard()
        if not hasattr(wizard, 'upload_stats'):
            wizard.upload_stats = {}
        wizard.upload_stats['uploaded'] = count
        # Save account name
        from ui.pages.account_select import AccountSelectionPage
        acct_page = wizard.page(2)
        if hasattr(acct_page, 'account_combo'):
            idx = acct_page.account_combo.currentIndex()
            acct_name = acct_page.account_combo.itemText(idx)
            wizard.uploaded_account_name = acct_name
        else:
            wizard.uploaded_account_name = None
        self.continue_btn.setEnabled(True)
        self.wizard().next()

    def on_error(self, msg):
        self.success_icon.hide()
        self.error_icon.show()
        self.info_label.setText(f"Error: {msg}")

    def isComplete(self):
        print("[DEBUG] isComplete called for ReviewAndUploadPage, always returns True")
        return True
