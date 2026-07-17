from PyQt5.QtWidgets import (
    QFrame, QLabel, QVBoxLayout, QWizardPage, QSizePolicy,
)
from PyQt5.QtCore import Qt
from PyQt5.QtSvg import QSvgWidget
import html
import os
import logging

logger = logging.getLogger(__name__)


class FinishPage(QWizardPage):
    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setTitle("Step 6: Import Complete")
        self.setObjectName("finish-page")
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)

        card = QFrame()
        card.setObjectName("card-panel")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(48, 48, 48, 48)
        card_layout.setSpacing(12)
        card_layout.setAlignment(Qt.AlignCenter)

        success_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../resources/icons/success.svg")
        )
        self.success_icon = QSvgWidget(success_path)
        self.success_icon.setFixedSize(56, 56)
        card_layout.addWidget(self.success_icon, alignment=Qt.AlignHCenter)

        eyebrow = QLabel("ALL DONE")
        eyebrow.setProperty("role", "eyebrow")
        eyebrow.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(eyebrow)

        self.title_label = QLabel("Import complete")
        self.title_label.setProperty("role", "page-title")
        self.title_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.title_label)

        self.label = QLabel()
        self.label.setObjectName("completion-details")
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        card_layout.addWidget(self.label)

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
            self.title_label.setText("Converted file ready")
            text = (
                "Your selected transactions were saved beside the source statement.<br><br>"
                f"<span style='font-family:monospace;'>{html.escape(file_export_path)}</span>"
            )
        elif actual_path:
            self.title_label.setText("Actual Budget export ready")
            text = (
                "Your CSV was created successfully.<br><br>"
                f"<span style='font-family:monospace;'>{html.escape(actual_path)}</span><br><br>"
                "Open Actual and import this file via Transactions → Import."
            )
        elif stats and acct:
            uploaded = stats.get('uploaded', 0)
            selected = stats.get('selected')
            safe_acct = html.escape(str(acct))
            if uploaded == 0:
                self.title_label.setText("Nothing new to import")
                text = (
                    f"No new transactions were added to <b>{safe_acct}</b>. "
                    "The selected rows may already exist in the account."
                )
            else:
                self.title_label.setText("Import complete")
                uploaded_text = (
                    f"<b>{uploaded}</b> transaction{'s' if uploaded != 1 else ''} "
                    f"added to <b>{safe_acct}</b>."
                )
                if selected is not None:
                    details = (
                        f"{uploaded_text}<br><br>{selected} selected for import."
                    )
                else:
                    details = uploaded_text
                text = details
        else:
            self.title_label.setText("Import complete")
            text = "The workflow finished successfully. You can now close the importer."

        self.label.setText(text)

        # Update parent window next button if possible
        if hasattr(parent, "next_button"):
            parent.next_button.setText("Close")

        # Hide back button on last page if possible
        if hasattr(parent, "back_button"):
            parent.back_button.hide()

        # No mode chooser when finishing
