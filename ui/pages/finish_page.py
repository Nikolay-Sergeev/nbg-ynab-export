from PyQt5.QtWidgets import QWizardPage, QVBoxLayout, QLabel, QWizard, QHBoxLayout, QPushButton, QFrame, QSizePolicy
from PyQt5.QtCore import Qt
import sys

class FinishPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Step 6: Import Complete")
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)

        card = QFrame()
        card.setObjectName("card-panel")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(16)

        # Final message

        self.label = QLabel()
        self.label.setProperty('role', 'title')
        self.label.setWordWrap(True)
        card_layout.addWidget(self.label)

        # Navigation Buttons (Back/Exit, same size, Exit on right)
        btn_layout = QHBoxLayout()
        self.back_btn = QPushButton("Back")
        self.back_btn.setObjectName("back-btn")
        self.back_btn.setFixedWidth(100)
        self.back_btn.setFixedHeight(40)
        self.back_btn.clicked.connect(lambda: self.wizard().back())
        btn_layout.addWidget(self.back_btn)
        btn_layout.addStretch(1)
        exit_text = "Quit" if sys.platform.startswith('darwin') else "Exit"
        self.exit_btn = QPushButton(exit_text)
        self.exit_btn.setObjectName("exit-btn")
        self.exit_btn.setFixedWidth(100)
        self.exit_btn.setFixedHeight(40)
        self.exit_btn.clicked.connect(lambda: self.wizard().reject())
        btn_layout.addWidget(self.exit_btn)
        card_layout.addLayout(btn_layout)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.addWidget(card)
        self.setLayout(main_layout)

    def initializePage(self):
        w = self.wizard()
        stats = getattr(w, 'upload_stats', None)
        acct = getattr(w, 'uploaded_account_name', None)
        if stats and acct:
            uploaded = stats.get('uploaded', 0)
            if uploaded == 0:
                text = f"<b>No new transactions were uploaded to <b>{acct}</b>.</b><br><br>You may now close the wizard."  
            else:
                text = "<b>Import complete!</b><br><br>"
                text += f"<span style='font-size:18px;color:#1976d2;'><b>{uploaded}</b> transaction{'s' if uploaded != 1 else ''} uploaded to <b>{acct}</b>.</span><br><br>You may now close the wizard."
        else:
            text = "<b>Import complete!</b> You may now close the wizard."
        self.label.setText(text)
        finish_text = "Finish & Quit" if sys.platform.startswith('darwin') else "Finish & Exit"
        w.setButtonText(QWizard.FinishButton, finish_text)
        w.setOption(QWizard.NoCancelButtonOnLastPage, False)
