#!/usr/bin/env python3
"""
Minimal Step 1 macOS style wizard using PyQt5.
"""

import sys
from PyQt5 import QtCore, QtGui, QtWidgets


class StepSidebar(QtWidgets.QListWidget):
    """Sidebar showing wizard steps."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(200)
        self.setSpacing(5)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        steps = [
            "Import NBG or\nRevolut Statement",
            "Authorize YNAB",
            "Select Budget\nand Account",
            "Check\nTransactions",
            "Review\nTransactions",
            "Status",
        ]
        for i, text in enumerate(steps, start=1):
            item = QtWidgets.QListWidgetItem(f"{i}  {text}")
            item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            item.setFlags(item.flags() & ~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.addItem(item)

        self.setCurrentRow(0)

        self.setStyleSheet(
            """
            QListWidget {
                background: #FFFFFF;
                font-size: 14px;
                font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;
            }
            QListWidget::item {
                padding: 12px 8px;
                color: #000000;
            }
            QListWidget::item:selected {
                background: #007AFF;
                color: #FFFFFF;
                border-radius: 6px;
            }
            """
        )


class DragDropZone(QtWidgets.QFrame):
    """Simple drag and drop file area."""

    fileDropped = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFixedHeight(200)
        self.setStyleSheet(
            """
            QFrame {
                border: 2px dashed #C7C7CC;
                border-radius: 12px;
                background: #FFFFFF;
            }
            """
        )
        layout = QtWidgets.QVBoxLayout(self)
        layout.setAlignment(QtCore.Qt.AlignCenter)

        cloud = QtWidgets.QLabel("\u2601")
        cloud.setFont(QtGui.QFont("Arial", 48))
        cloud.setAlignment(QtCore.Qt.AlignCenter)

        self.instruction = QtWidgets.QLabel(
            "Drag & drop your file here,\nor click 'Browse files…'"
        )
        self.instruction.setAlignment(QtCore.Qt.AlignCenter)
        self.instruction.setFont(QtGui.QFont("-apple-system", 12))
        self.instruction.setStyleSheet("color: #8E8E93;")

        layout.addWidget(cloud)
        layout.addSpacing(4)
        layout.addWidget(self.instruction)
        layout.addSpacing(12)

        self.browse_btn = QtWidgets.QPushButton("Browse files…")
        self.browse_btn.setFixedWidth(140)
        self.browse_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.browse_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #007AFF;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-family: -apple-system;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #0051A8;
            }
            """
        )
        layout.addWidget(self.browse_btn)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self.setStyleSheet(
                """
                QFrame {
                    border: 2px dashed #007AFF;
                    border-radius: 12px;
                    background: #F0F8FF;
                }
                """
            )
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.setStyleSheet(
            """
            QFrame {
                border: 2px dashed #C7C7CC;
                border-radius: 12px;
                background: #FFFFFF;
            }
            """
        )

    def dropEvent(self, event):
        self.setStyleSheet(
            """
            QFrame {
                border: 2px dashed #C7C7CC;
                border-radius: 12px;
                background: #FFFFFF;
            }
            """
        )
        if event.mimeData().hasUrls():
            path = event.mimeData().urls()[0].toLocalFile()
            self.fileDropped.emit(path)
            event.acceptProposedAction()


class MainWindow(QtWidgets.QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Importer")
        self.resize(700, 450)
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        main_layout = QtWidgets.QHBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(0)

        sidebar = StepSidebar()
        main_layout.addWidget(sidebar)

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.VLine)
        sep.setFrameShadow(QtWidgets.QFrame.Sunken)
        sep.setStyleSheet("color: #E5E5EA;")
        main_layout.addWidget(sep)

        right_panel = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        right_layout.setContentsMargins(30, 0, 0, 0)
        right_layout.setSpacing(15)

        header = QtWidgets.QLabel("Import NBG or Revolut Statement")
        header.setFont(QtGui.QFont("-apple-system", 20, QtGui.QFont.Bold))
        header.setStyleSheet("color: #000000;")
        subheader = QtWidgets.QLabel("Supported formats: xlsx, csv")
        subheader.setFont(QtGui.QFont("-apple-system", 12))
        subheader.setStyleSheet("color: #3C3C43;")

        right_layout.addSpacing(10)
        right_layout.addWidget(header)
        right_layout.addWidget(subheader)
        right_layout.addSpacing(20)

        self.drop_zone = DragDropZone()
        right_layout.addWidget(self.drop_zone)
        right_layout.addStretch()

        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setContentsMargins(0, 20, 0, 0)

        quit_btn = QtWidgets.QPushButton("Quit")
        quit_btn.setCursor(QtCore.Qt.PointingHandCursor)
        quit_btn.setFixedSize(100, 32)
        quit_btn.setStyleSheet(
            """
            QPushButton {
                background: #FFFFFF;
                color: #007AFF;
                border: 1px solid #007AFF;
                border-radius: 6px;
                font-family: -apple-system;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #F2F2F7;
            }
            """
        )
        quit_btn.clicked.connect(self.close)

        self.continue_btn = QtWidgets.QPushButton("Continue")
        self.continue_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.continue_btn.setFixedSize(100, 32)
        self.continue_btn.setEnabled(False)
        self.continue_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #007AFF;
                color: white;
                border: none;
                border-radius: 6px;
                font-family: -apple-system;
                font-size: 13px;
            }
            QPushButton:disabled {
                background-color: #A0A0A0;
                color: white;
            }
            QPushButton:hover:!disabled {
                background-color: #0051A8;
            }
            """
        )

        btn_layout.addWidget(quit_btn, alignment=QtCore.Qt.AlignLeft)
        btn_layout.addStretch()
        btn_layout.addWidget(self.continue_btn, alignment=QtCore.Qt.AlignRight)

        right_layout.addLayout(btn_layout)

        main_layout.addWidget(right_panel)

        self.drop_zone.browse_btn.clicked.connect(self.browse_file)
        self.drop_zone.fileDropped.connect(self.handle_path)

    def browse_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select file", "", "CSV/Excel (*.csv *.xlsx)"
        )
        if path:
            self.handle_path(path)

    def handle_path(self, path: str):
        if path.lower().endswith((".csv", ".xlsx")):
            name = QtCore.QFileInfo(path).fileName()
            self.drop_zone.instruction.setText(name)
            self.continue_btn.setEnabled(True)
        else:
            QtWidgets.QMessageBox.warning(
                self,
                "Unsupported format",
                "Unsupported format. Please use .csv or .xlsx.",
            )


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
