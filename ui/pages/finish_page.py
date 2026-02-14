from PyQt5.QtWidgets import (
    QFrame, QLabel, QVBoxLayout, QWizardPage, QSizePolicy,
)
from PyQt5.QtCore import Qt
import sys
import logging

logger = logging.getLogger(__name__)


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
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        card_layout.addWidget(self.label)
        card_layout.addStretch(1)

        # Navigation buttons are completely handled by main window
        # No local buttons to avoid duplication

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(card)
        self.setLayout(main_layout)

    def validate_and_proceed(self):
        """Implementation for consistency with other pages"""
        logger.info("[FinishPage] validate_and_proceed called")
        # This is the final page, so just close the application
        self.window().close()
        return True

    def initializePage(self):
        # Get stats from parent window instead of wizard
        parent = self.window()
        stats = getattr(parent, 'upload_stats', None)
        acct = getattr(parent, 'uploaded_account_name', None)
        file_export_path = getattr(parent, 'file_export_path', None)
        actual_path = getattr(parent, 'actual_export_path', None)

        if file_export_path:
            text = (
                "<b>File converted</b><br><br>"
                f"<span style='font-family:monospace;'>{file_export_path}</span>"
            )
        elif actual_path:
            text = (
                "<b>Export complete!</b><br><br>"
                f"CSV for <b>Actual Budget</b> saved at:<br>"
                f"<span style='font-family:monospace;'>{actual_path}</span><br><br>"
                "Open Actual and import this file via Transactions → Import."
            )
        elif stats and acct:
            uploaded = stats.get('uploaded', 0)
            selected = stats.get('selected')
            if uploaded == 0:
                text = (
                    f"<b>No new transactions were uploaded to <b>{acct}</b>.</b>"
                    "<br><br>You may now close the wizard."
                )
            else:
                text = "<b>Import complete!</b><br><br>"
                uploaded_text = (
                    f"<span style='font-size:18px;color:#1976d2;'><b>{uploaded}</b>"
                    f" transaction{'s' if uploaded != 1 else ''} uploaded to <b>{acct}</b>"
                    ".</span>"
                )
                if selected is not None:
                    details = (
                        f"{uploaded_text}<br><span style='color:#555;'>Selected to import: "
                        f"{selected}</span><br><br>You may now close the wizard."
                    )
                else:
                    details = f"{uploaded_text}<br><br>You may now close the wizard."
                text += details
        else:
            text = "<b>Import complete!</b> You may now close the wizard."

        self.label.setText(text)

        # Update parent window next button if possible
        if hasattr(parent, "next_button"):
            finish_label = "Finish & Quit" if sys.platform.startswith('darwin') else "Finish & Exit"
            parent.next_button.setText(finish_label)

        # Hide back button on last page if possible
        if hasattr(parent, "back_button"):
            parent.back_button.hide()

        # No mode chooser when finishing
