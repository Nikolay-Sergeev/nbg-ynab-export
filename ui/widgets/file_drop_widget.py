from PyQt5.QtWidgets import QFrame, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap
import os

class FileDropWidget(QFrame):
    """Reusable drag-and-drop file selector."""
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
        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../resources/upload.svg"))
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
