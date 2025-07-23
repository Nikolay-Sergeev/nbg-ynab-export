from PyQt5.QtWidgets import QFrame, QLabel, QVBoxLayout, QWizardPage, QSizePolicy
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

        if stats and acct:
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
