from PyQt5.QtWidgets import (
    QWizardPage, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QListWidget, QListWidgetItem, QWidget, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap
import os
import sys
from config import SETTINGS_FILE

class FileDropWidget(QFrame):
    fileDropped = pyqtSignal(str)
    clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("drop-widget")
        self.setAcceptDrops(True)
        self.setFixedSize(320, 200)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        self.icon = QLabel()
        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../resources/upload.svg'))
        if os.path.exists(icon_path):
            self.icon.setPixmap(QPixmap(icon_path).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(self.icon)

        self.text = QLabel("Drag & drop your file here,\nor click \u201cBrowse files\u2026\u201d")
        self.text.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.text)

        self.file_label = QLabel("")
        self.file_label.setAlignment(Qt.AlignCenter)
        self.file_label.hide()
        layout.addWidget(self.file_label)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            path = event.mimeData().urls()[0].toLocalFile()
            if path.lower().endswith((".csv", ".xlsx")):
                event.acceptProposedAction()
                self.setProperty("drag", True)
                self.style().unpolish(self)
                self.style().polish(self)
            else:
                event.ignore()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setProperty("drag", False)
        self.style().polish(self)

    def dropEvent(self, event):
        self.setProperty("drag", False)
        self.style().polish(self)
        if event.mimeData().hasUrls():
            path = event.mimeData().urls()[0].toLocalFile()
            self.fileDropped.emit(path)
        event.accept()

    def mousePressEvent(self, event):
        self.clicked.emit()

class ImportFilePage(QWizardPage):
    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.selected_file = None
        self.setTitle("")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        root.addLayout(body, 1)

        # Sidebar
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(200)
        steps = [
            "Import NBG or Revolut Statement",
            "Authorize with YNAB",
            "Select YNAB Budget and Account",
            "Check Recent Transactions",
            "Review New Transactions",
            "Status",
        ]
        for i, step in enumerate(steps):
            item = QListWidgetItem(f"{i + 1}. {step}")
            self.sidebar.addItem(item)
        self.sidebar.setCurrentRow(0)
        body.addWidget(self.sidebar)

        # Main pane
        pane_widget = QWidget()
        pane_widget.setObjectName("main-pane")
        pane = QVBoxLayout(pane_widget)
        pane.setContentsMargins(40, 40, 40, 40)
        pane.setSpacing(12)
        body.addWidget(pane_widget, 1)

        title = QLabel("Import NBG or Revolut Statement")
        title.setObjectName("main-title")
        pane.addWidget(title)

        subtitle = QLabel("Supported formats: .xlsx, .csv")
        subtitle.setObjectName("subtext")
        pane.addWidget(subtitle)

        pane.addSpacing(20)

        self.drop_widget = FileDropWidget()
        pane.addWidget(self.drop_widget, alignment=Qt.AlignHCenter)

        self.browse_btn = QPushButton("Browse files…")
        self.browse_btn.setObjectName("browse-btn")
        pane.addWidget(self.browse_btn, alignment=Qt.AlignCenter)

        self.error_label = QLabel("")
        self.error_label.setObjectName("error-label")
        pane.addWidget(self.error_label)

        pane.addStretch(1)

        footer = QHBoxLayout()
        footer.setContentsMargins(20, 12, 20, 12)
        exit_text = "Quit" if sys.platform.startswith('darwin') else "Exit"
        self.exit_button = QPushButton(exit_text)
        self.exit_button.setObjectName("exit-btn")
        self.exit_button.clicked.connect(lambda: self.wizard().reject())
        footer.addWidget(self.exit_button)
        footer.addStretch(1)
        self.continue_button = QPushButton("Continue")
        self.continue_button.setObjectName("continue-btn")
        self.continue_button.setEnabled(False)
        self.continue_button.clicked.connect(self.validate_and_proceed)
        footer.addWidget(self.continue_button)
        root.addLayout(footer)

        self.drop_widget.fileDropped.connect(self.on_file_selected)
        self.drop_widget.clicked.connect(self.browse_file)

        self.last_folder = self.load_last_folder()

    def load_last_folder(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    for line in f:
                        if line.startswith("FOLDER:"):
                            return line.strip().split("FOLDER:", 1)[1]
            except Exception:
                pass
        return ""

    def save_last_folder(self, folder):
        lines = []
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                for line in f:
                    if line.startswith("TOKEN:"):
                        lines.append(line)
        lines.append(f"FOLDER:{folder}\n")
        with open(SETTINGS_FILE, "w") as f:
            f.writelines(lines)

    def browse_file(self):
        folder = self.last_folder if self.last_folder else os.path.expanduser("~")
        path, _ = QFileDialog.getOpenFileName(self, "Select file", folder, "CSV/Excel (*.csv *.xlsx)")
        if path:
            self.on_file_selected(path)

    def on_file_selected(self, path):
        if path.lower().endswith((".csv", ".xlsx")):
            self.selected_file = path
            self.drop_widget.icon.hide()
            self.drop_widget.text.hide()
            self.drop_widget.file_label.setText(os.path.basename(path))
            self.drop_widget.file_label.show()
            self.error_label.setText("")
            self.continue_button.setEnabled(True)
            folder = os.path.dirname(path)
            self.last_folder = folder
            self.save_last_folder(folder)
        else:
            self.selected_file = None
            self.error_label.setText("Unsupported format. Please use .csv or .xlsx.")
            self.drop_widget.file_label.hide()
            self.drop_widget.icon.show()
            self.drop_widget.text.show()
            self.continue_button.setEnabled(False)

    def validate_and_proceed(self):
        if self.selected_file:
            self.wizard().next()

    def nextId(self):
        return 1
