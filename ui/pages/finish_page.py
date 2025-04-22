from PyQt5.QtWidgets import QWizardPage, QVBoxLayout, QLabel, QWizard, QHBoxLayout, QPushButton, QFrame, QSizePolicy
from PyQt5.QtCore import Qt
from .account_select import StepperWidget  # Import StepperWidget from account_select.py

class FinishPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Step 6: Import Complete")
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        layout = QVBoxLayout(self)
        
        # Stepper (6/6)
        self.stepper = StepperWidget(step_idx=5, total_steps=6)
        layout.insertWidget(0, self.stepper)
        indicator = QLabel("6/6")
        indicator.setAlignment(Qt.AlignRight)
        indicator.setStyleSheet("font-size:14px;color:#888;margin-bottom:8px;")
        layout.insertWidget(1, indicator)

        self.label = QLabel()
        self.label.setProperty('role', 'title')
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        # Navigation Buttons (Back/Exit, same size, Exit on right)
        btn_layout = QHBoxLayout()
        self.back_btn = QPushButton("Back")
        self.back_btn.setObjectName("back-btn")
        self.back_btn.setFixedWidth(160)
        self.back_btn.setFixedHeight(48)
        self.back_btn.clicked.connect(lambda: self.wizard().back())
        btn_layout.addWidget(self.back_btn)
        btn_layout.addStretch(1)
        self.exit_btn = QPushButton("Exit")
        self.exit_btn.setObjectName("exit-btn")
        self.exit_btn.setFixedWidth(160)
        self.exit_btn.setFixedHeight(48)
        self.exit_btn.clicked.connect(lambda: self.wizard().reject())
        btn_layout.addWidget(self.exit_btn)
        layout.addLayout(btn_layout)

        card = self.findChild(QFrame, "card-panel")
        if card:
            card.setMinimumWidth(500)
            card.setMaximumWidth(500)
            card.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        self.setLayout(layout)

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
        w.setButtonText(QWizard.FinishButton, "Finish & Exit")
        w.setOption(QWizard.NoCancelButtonOnLastPage, False)
