from PyQt5.QtWidgets import (
    QWizardPage,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHBoxLayout,
    QFrame,
    QSizePolicy,
    QHeaderView,
    QMessageBox,
    QCheckBox,
    QAbstractItemView,
)
from PyQt5.QtCore import Qt
from PyQt5.QtSvg import QSvgWidget
import os
from services.conversion_service import generate_output_filename
import logging


class ReviewAndUploadPage(QWizardPage):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setTitle("Review & Select Transactions")

        card = QFrame()
        card.setObjectName("card-panel")
        card.setFrameShape(QFrame.StyledPanel)
        card.setFrameShadow(QFrame.Raised)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(8, 8, 8, 8)
        card_layout.setSpacing(16)

        self.label = QLabel("Review transactions and choose what to import:")
        self.label.setProperty('role', 'title')
        self.label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.label)

        # Load icons: success, error, info, spinner
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../resources/icons'))
        # Success icon
        success_path = os.path.join(base, 'success.svg')
        try:
            self.success_icon = QSvgWidget(success_path)
            self.success_icon.setFixedSize(24, 24)
        except Exception:
            self.success_icon = QLabel()
        self.success_icon.hide()
        # Error icon
        error_path = os.path.join(base, 'error.svg')
        try:
            self.error_icon = QSvgWidget(error_path)
            self.error_icon.setFixedSize(24, 24)
        except Exception:
            self.error_icon = QLabel()
        self.error_icon.hide()
        # Info icon
        info_path = os.path.join(base, 'info.svg')
        try:
            self.info_icon = QSvgWidget(info_path)
            self.info_icon.setFixedSize(24, 24)
        except Exception:
            self.info_icon = QLabel()
        self.info_icon.hide()
        # Info label
        self.info_label = QLabel("")
        self.info_label.setObjectName("info-label")
        self.info_label.setWordWrap(True)
        icon_label_layout = QHBoxLayout()
        icon_label_layout.addWidget(self.success_icon)
        icon_label_layout.addWidget(self.error_icon)
        icon_label_layout.addWidget(self.info_icon)
        icon_label_layout.addWidget(self.info_label)
        icon_label_layout.addStretch()
        card_layout.addLayout(icon_label_layout)
        # Spinner icon
        spinner_path = os.path.join(base, 'spinner.svg')
        try:
            self.spinner = QSvgWidget(spinner_path)
            self.spinner.setFixedSize(36, 36)
        except Exception:
            self.spinner = QLabel()
        self.spinner.hide()
        card_layout.addWidget(self.spinner, alignment=Qt.AlignCenter)

        self.table = QTableWidget()
        self.table.setStyleSheet("color: #222; background: #fff;")
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setAlternatingRowColors(True)
        # Respond to Skip item changes
        self.table.itemChanged.connect(self.on_skip_item_changed)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        card_layout.addWidget(self.table)

        self.hide_dup_checkbox = QCheckBox("Hide duplicate records")
        self.hide_dup_checkbox.stateChanged.connect(self.on_hide_duplicates_toggled)
        self.hide_dup_checkbox.setVisible(False)
        card_layout.addWidget(self.hide_dup_checkbox)

        card_layout.addStretch(1)

        # Navigation buttons now handled by main window

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(card)
        self.setLayout(main_layout)
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)

        self.controller.duplicatesFound.connect(self.on_duplicates_found)
        self.controller.uploadFinished.connect(self.on_upload_finished)
        self.controller.errorOccurred.connect(self.on_error)
        self.records = []
        self.dup_idx = set()
        self.skipped_rows = set()
        self.skip_column_index = None
        self.skip_checked_value = True
        self.worker = None

    def initializePage(self):
        parent = self.window()
        if not hasattr(parent, "pages_stack"):
            print("[ReviewUploadPage] Cannot access pages stack")
            return
        import_page = parent.pages_stack.widget(0)
        if not hasattr(import_page, "file_path"):
            print("[ReviewUploadPage] Cannot access file path from import page")
            return
        file_path = import_page.file_path
        self.skipped_rows = set()

        # Branch by mode
        target = getattr(self.controller, 'export_target', 'YNAB')
        if hasattr(parent, 'file_export_path'):
            parent.file_export_path = None
        if target == 'FILE':
            # Pure file-converter mode: convert and show, no API
            try:
                df = self.controller.converter.convert_to_ynab(
                    file_path,
                    write_output=False,
                )
                records = df.to_dict('records') if df is not None else []
                self.populate_file_records(records)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error converting file: {str(e)}")
            return

        if not self.controller.ynab:
            QMessageBox.critical(self, "Error", "Client not initialized. Please authorize.")
            return
        # Get selected IDs from account selection page (YNAB/Actual API)
        account_page = parent.pages_stack.widget(2)
        if not hasattr(account_page, "get_selected_ids"):
            print("[ReviewUploadPage] Cannot access account selection method")
            return
        budget_id, account_id = account_page.get_selected_ids()
        if file_path and budget_id and account_id:
            try:
                self.controller.check_duplicates(file_path, budget_id, account_id)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error checking duplicates: {str(e)}")

    def on_duplicates_found(self, records, dup_idx):
        # Populate table with records and duplicates
        self.records = records
        self.dup_idx = dup_idx
        self.skipped_rows = set(dup_idx)
        self.skip_column_index = None
        self.skip_checked_value = True
        # Clear existing content, then set dimensions and headers
        self.table.clearContents()
        row_count = len(records)
        col_count = len(records[0]) + 2 if records else 0
        self.table.setRowCount(row_count)
        self.table.setColumnCount(col_count)
        headers = list(records[0].keys()) if records else []
        headers += ["Status", "Skip"]
        self.table.setHorizontalHeaderLabels(headers)
        skip_col = col_count - 1 if col_count else None
        self.skip_column_index = skip_col
        # Block signals while initializing
        self.table.blockSignals(True)
        for row, rec in enumerate(records):
            # Data columns
            for col, key in enumerate(rec):
                item = QTableWidgetItem(str(rec[key]))
                if row in dup_idx:
                    item.setBackground(Qt.yellow)
                self.table.setItem(row, col, item)
            # Status column
            status_item = QTableWidgetItem("Duplicate" if row in dup_idx else "Ready")
            status_item.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, col_count - 2, status_item)
            # Skip column as checkable item
            skip_item = QTableWidgetItem()
            skip_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            skip_item.setCheckState(Qt.Checked if row in dup_idx else Qt.Unchecked)
            if row in dup_idx:
                self.skipped_rows.add(row)
            self.table.setItem(row, skip_col, skip_item)
        self.table.blockSignals(False)
        # Resize columns and rows to show checkboxes
        header = self.table.horizontalHeader()
        for c in range(col_count - 1):
            header.setSectionResizeMode(c, QHeaderView.Stretch)
        if skip_col is not None:
            header.setSectionResizeMode(skip_col, QHeaderView.ResizeToContents)
        self.table.resizeRowsToContents()
        self.hide_dup_checkbox.setVisible(bool(dup_idx))
        self.hide_dup_checkbox.setChecked(False)
        self.on_hide_duplicates_toggled(self.hide_dup_checkbox.checkState())
        self.info_icon.hide()
        if records:
            self.info_label.setText("")
        else:
            self.info_label.setText("No transactions to review.")
            self.info_icon.show()
        # Enable Continue button
        # Button is now handled by the main window
        parent = self.window()
        if hasattr(parent, "next_button"):
            parent.next_button.setEnabled(True)

    def on_skip_item_changed(self, item):
        # Track Skip column changes
        if self.skip_column_index is None or item.column() != self.skip_column_index:
            return
        is_checked = item.checkState() == Qt.Checked
        if self.skip_checked_value:
            if is_checked:
                self.skipped_rows.add(item.row())
            else:
                self.skipped_rows.discard(item.row())
        else:
            if is_checked:
                self.skipped_rows.discard(item.row())
            else:
                self.skipped_rows.add(item.row())

    def on_hide_duplicates_toggled(self, state):
        hide = state == Qt.Checked
        for row in range(self.table.rowCount()):
            if row in self.dup_idx:
                self.table.setRowHidden(row, hide)

    def upload_transactions(self):
        print("[DEBUG] upload_transactions called")
        # Get selected IDs from account selection page
        parent = self.window()
        if not hasattr(parent, "pages_stack") or parent.pages_stack.count() <= 2:
            print("[ReviewUploadPage] Cannot access pages stack or account page")
            return

        account_page = parent.pages_stack.widget(2)
        if not hasattr(account_page, "get_selected_ids"):
            print("[ReviewUploadPage] Account page has no get_selected_ids method")
            return

        budget_id, account_id = account_page.get_selected_ids()
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
                    print(
                        "[DEBUG] No valid transactions after formatting. "
                        "Advancing to finish page."
                    )
                    QMessageBox.information(
                        self,
                        "No Valid Transactions",
                        "No valid transactions to upload after formatting."
                    )
                    # Set stats for FinishPage and advance to next page
                    parent = self.window()
                    if not hasattr(parent, 'upload_stats'):
                        parent.upload_stats = {}
                    parent.upload_stats['uploaded'] = 0

                    # Save account name
                    acct_page = parent.pages_stack.widget(2) if hasattr(parent, 'pages_stack') else None
                    if acct_page and hasattr(acct_page, 'account_combo'):
                        idx = acct_page.account_combo.currentIndex()
                        acct_name = acct_page.account_combo.itemText(idx)
                        parent.uploaded_account_name = acct_name
                    else:
                        parent.uploaded_account_name = None

                    # Re-enable navigation and go to next page
                    if hasattr(parent, "next_button"):
                        parent.next_button.setEnabled(True)

                    if hasattr(parent, "go_to_page") and hasattr(parent, "pages_stack"):
                        current_index = parent.pages_stack.indexOf(self)
                        if current_index >= 0:
                            parent.go_to_page(current_index + 1)
            except Exception as e:
                print(f"[DEBUG] Exception in upload_transactions: {e}")
                QMessageBox.critical(self, "Error", f"Error uploading transactions: {str(e)}")
        else:
            print("[DEBUG] No budget/account selected or nothing to upload. Advancing to finish page.")
            # Set stats for FinishPage and advance to next page
            parent = self.window()
            if not hasattr(parent, 'upload_stats'):
                parent.upload_stats = {}
            parent.upload_stats['uploaded'] = 0

            # Save account name
            acct_page = parent.pages_stack.widget(2) if hasattr(parent, 'pages_stack') else None
            if acct_page and hasattr(acct_page, 'account_combo'):
                idx = acct_page.account_combo.currentIndex()
                acct_name = acct_page.account_combo.itemText(idx)
                parent.uploaded_account_name = acct_name
            else:
                parent.uploaded_account_name = None

            # Re-enable navigation and go to next page
            if hasattr(parent, "next_button"):
                parent.next_button.setEnabled(True)

            if hasattr(parent, "go_to_page") and hasattr(parent, "pages_stack"):
                current_index = parent.pages_stack.indexOf(self)
                if current_index >= 0:
                    parent.go_to_page(current_index + 1)

    def validate_and_proceed(self):
        print("[ReviewUploadPage] validate_and_proceed called")
        parent = self.window()
        target = getattr(self.controller, 'export_target', 'YNAB')
        if target == 'FILE':
            # Export selected rows to YNAB CSV and move to Finish
            try:
                selected = [r for i, r in enumerate(self.records) if i not in self.skipped_rows]
                if not selected:
                    QMessageBox.information(self, "Nothing to Export", "No rows selected for export.")
                # Build DataFrame and write
                import pandas as pd
                df = pd.DataFrame(selected)
                import_page = parent.pages_stack.widget(0)
                input_dir = os.path.dirname(os.path.abspath(import_page.file_path))
                out_path = generate_output_filename(
                    import_page.file_path,
                    output_dir=input_dir,
                )
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                df.to_csv(out_path, index=False)
                parent.file_export_path = out_path
                if hasattr(parent, 'actual_export_path'):
                    parent.actual_export_path = None
                parent.upload_stats = {'uploaded': len(selected)}
                if hasattr(parent, "go_to_page") and hasattr(parent, "pages_stack"):
                    cur = parent.pages_stack.indexOf(self)
                    if cur >= 0:
                        parent.go_to_page(cur + 1)
                return True
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))
                return False
        else:
            # Disable navigation to prevent double submission while uploading
            if hasattr(parent, "next_button"):
                parent.next_button.setEnabled(False)
            print(
                f"[ReviewUploadPage] Records: {len(getattr(self, 'records', []))}, "
                f"Duplicates: {len(getattr(self, 'dup_idx', []))}, "
                f"Skipped: {len(getattr(self, 'skipped_rows', []))}"
            )
            self.upload_transactions()
            return True

    def on_upload_finished(self, count):
        self.success_icon.show()
        self.error_icon.hide()
        self.info_icon.hide()
        self.table.setRowCount(0)
        self.info_label.setText(f"Upload complete. {count} transactions uploaded.")
        # Save upload stats and account name to parent window for FinishPage
        parent = self.window()
        if not hasattr(parent, 'upload_stats'):
            parent.upload_stats = {}
        parent.upload_stats['uploaded'] = count

        # Save account name
        acct_page = parent.pages_stack.widget(2) if hasattr(parent, 'pages_stack') else None
        if acct_page and hasattr(acct_page, 'account_combo'):
            idx = acct_page.account_combo.currentIndex()
            acct_name = acct_page.account_combo.itemText(idx)
            parent.uploaded_account_name = acct_name
        else:
            parent.uploaded_account_name = None

        # Re-enable navigation and go to next page
        if hasattr(parent, "next_button"):
            parent.next_button.setEnabled(True)

        if hasattr(parent, "go_to_page") and hasattr(parent, "pages_stack"):
            current_index = parent.pages_stack.indexOf(self)
            if current_index >= 0:
                parent.go_to_page(current_index + 1)

    def on_error(self, msg):
        self.success_icon.hide()
        self.error_icon.show()
        self.info_icon.hide()
        self.info_label.setText(f"Error: {msg}")

    def show_success(self, msg):
        self.spinner.hide()
        self.success_icon.show()
        self.error_icon.hide()
        self.info_icon.hide()
        self.info_label.setText(msg)
        self.info_label.setObjectName("success-label")
        self.info_label.setStyleSheet("")

    def show_error(self, msg):
        self.spinner.hide()
        self.success_icon.hide()
        self.error_icon.show()
        self.info_icon.hide()
        self.info_label.setText(msg)
        self.info_label.setObjectName("error-label")
        self.info_label.setStyleSheet("")

    def on_duplicates_error(self, error_msg):
        try:
            logging.exception("Background duplicate check failed: %s", error_msg)
            self.show_error("Processing error occurred. Check logs for details.")
        except Exception as e:
            logging.exception("Error handling duplicate check error: %s", e)

    def isComplete(self):
        print("[DEBUG] isComplete called for ReviewAndUploadPage, always returns True")
        return True

    def populate_file_records(self, records):
        """Populate table for File Converter mode with selectable transactions."""
        self.records = records
        self.dup_idx = set()
        self.skipped_rows = set()
        self.skip_column_index = 0
        self.skip_checked_value = False  # Checked means include
        self.table.blockSignals(True)
        headers = ["Import", "Date", "Payee", "Amount", "Memo"]
        self.table.clearContents()
        self.table.setRowCount(len(records))
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        for row, rec in enumerate(records):
            include_item = QTableWidgetItem()
            include_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            include_item.setCheckState(Qt.Checked)
            self.table.setItem(row, 0, include_item)
            date_item = QTableWidgetItem(str(rec.get("Date", "")))
            self.table.setItem(row, 1, date_item)
            payee_item = QTableWidgetItem(str(rec.get("Payee", "") or ""))
            self.table.setItem(row, 2, payee_item)
            raw_amount = rec.get("Amount", "")
            try:
                amount_val = float(raw_amount)
                amount_item = QTableWidgetItem(f"{amount_val:.2f}")
                amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            except (TypeError, ValueError):
                amount_item = QTableWidgetItem(str(raw_amount))
            self.table.setItem(row, 3, amount_item)
            memo_item = QTableWidgetItem(str(rec.get("Memo", "") or ""))
            self.table.setItem(row, 4, memo_item)
        self.table.blockSignals(False)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for col in range(1, self.table.columnCount() - 1):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.table.columnCount() - 1, QHeaderView.Stretch)
        self.table.resizeRowsToContents()

        self.hide_dup_checkbox.setVisible(False)
        self.success_icon.hide()
        self.error_icon.hide()
        if records:
            self.info_icon.hide()
            self.info_label.setText("Select or deselect transactions to include in the converted file.")
        else:
            self.info_icon.show()
            self.info_label.setText("No transactions found to convert.")
        parent = self.window()
        if hasattr(parent, "next_button"):
            parent.next_button.setEnabled(bool(records))
