from PyQt5.QtWidgets import (
    QFrame, QLabel, QVBoxLayout, QWizardPage, QSizePolicy,
    QHBoxLayout, QPushButton
)
import sys


class FinishPage(QWizardPage):
    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setTitle("Step 6: Import Complete")
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)

        card = QFrame()
        card.setObjectName("card-panel")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(8, 8, 8, 8)
        card_layout.setSpacing(16)

        # Final message
        self.label = QLabel()
        self.label.setProperty('role', 'title')
        self.label.setWordWrap(True)
        card_layout.addWidget(self.label)
        card_layout.addStretch(1)

        # Optional: quick mode chooser for starting another run
        chooser_title = QLabel("Start another conversion:")
        chooser_title.setStyleSheet("font-size:13px;color:#333;")
        card_layout.addWidget(chooser_title)

        btn_row = QHBoxLayout()
        self.btn_mode_ynab = QPushButton("YNAB")
        self.btn_mode_actual_api = QPushButton("Actual Budget (API)")
        self.btn_mode_file = QPushButton("File Converter")
        for b in (self.btn_mode_ynab, self.btn_mode_actual_api, self.btn_mode_file):
            b.setFixedHeight(32)
            btn_row.addWidget(b)
        btn_row.addStretch(1)
        card_layout.addLayout(btn_row)

        # Navigation buttons are completely handled by main window
        # No local buttons to avoid duplication

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(card)
        self.setLayout(main_layout)

    def validate_and_proceed(self):
        """Implementation for consistency with other pages"""
        print("[FinishPage] validate_and_proceed called")
        # This is the final page, so just close the application
        self.window().close()
        return True

    def initializePage(self):
        # Get stats from parent window instead of wizard
        parent = self.window()
        stats = getattr(parent, 'upload_stats', None)
        acct = getattr(parent, 'uploaded_account_name', None)
        actual_path = getattr(parent, 'actual_export_path', None)

        if actual_path:
            text = (
                "<b>Export complete!</b><br><br>"
                f"CSV for <b>Actual Budget</b> saved at:<br>"
                f"<span style='font-family:monospace;'>{actual_path}</span><br><br>"
                "Open Actual and import this file via Transactions → Import."
            )
        elif stats and acct:
            uploaded = stats.get('uploaded', 0)
            if uploaded == 0:
                text = (
                    f"<b>No new transactions were uploaded to <b>{acct}</b>.</b>"
                    "<br><br>You may now close the wizard."
                )
            else:
                text = "<b>Import complete!</b><br><br>"
                details = (
                    f"<span style='font-size:18px;color:#1976d2;'><b>{uploaded}</b>"
                    f" transaction{'s' if uploaded != 1 else ''} uploaded to <b>{acct}</b>"
                    ".</span><br><br>You may now close the wizard."
                )
                text += details
        else:
            text = "<b>Import complete!</b> You may now close the wizard."

        self.label.setText(text)

        # Update parent window next button if possible
        if hasattr(parent, "next_button"):
            parent.next_button.setText("Finish & Quit" if sys.platform.startswith('darwin') else "Finish & Exit")

        # Hide back button on last page if possible
        if hasattr(parent, "back_button"):
            parent.back_button.hide()

        # Wire up mode chooser actions to restart flow at page 0
        def _set_mode_and_restart(mode_key: str):
            try:
                if hasattr(parent, 'controller') and hasattr(parent.controller, 'set_export_target'):
                    parent.controller.set_export_target(mode_key)
                if hasattr(parent, 'set_steps_for_target'):
                    parent.set_steps_for_target(mode_key)
                if hasattr(parent, 'go_to_page'):
                    parent.go_to_page(0)
            except Exception:
                pass

        self.btn_mode_ynab.clicked.disconnect() if self.btn_mode_ynab.receivers(self.btn_mode_ynab.clicked) else None
        self.btn_mode_actual_api.clicked.disconnect() if self.btn_mode_actual_api.receivers(self.btn_mode_actual_api.clicked) else None
        self.btn_mode_file.clicked.disconnect() if self.btn_mode_file.receivers(self.btn_mode_file.clicked) else None
        self.btn_mode_ynab.clicked.connect(lambda: _set_mode_and_restart('YNAB'))
        self.btn_mode_actual_api.clicked.connect(lambda: _set_mode_and_restart('ACTUAL_API'))
        self.btn_mode_file.clicked.connect(lambda: _set_mode_and_restart('FILE'))
