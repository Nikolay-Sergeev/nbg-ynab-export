from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt

class StepSidebar(QWidget):
    def __init__(self, steps, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.steps = steps
        self.current_index = 0
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 40, 20, 40)
        layout.setSpacing(0)
        self.items = []
        for idx, text in enumerate(steps):
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)
            circle = QFrame()
            circle.setObjectName("step-circle")
            circle.setProperty("current", idx == 0)
            circle.setFixedSize(12, 12)
            row_layout.addWidget(circle, 0, Qt.AlignTop)
            label = QLabel(text)
            label.setWordWrap(True)
            label.setObjectName("step-label")
            label.setProperty("current", idx == 0)
            row_layout.addWidget(label)
            row_layout.addStretch()
            row_widget = QWidget()
            row_widget.setLayout(row_layout)
            layout.addWidget(row_widget)
            self.items.append((circle, label))
            if idx < len(steps) - 1:
                connector = QFrame()
                connector.setObjectName("step-connector")
                connector.setFixedWidth(1)
                connector.setMinimumHeight(24)
                layout.addWidget(connector, 0, Qt.AlignHCenter)
        layout.addStretch()

    def set_current(self, index):
        self.current_index = index
        for idx, (circle, label) in enumerate(self.items):
            circle.setProperty("current", idx == index)
            label.setProperty("current", idx == index)
            circle.style().unpolish(circle)
            circle.style().polish(circle)
            label.style().unpolish(label)
            label.style().polish(label)
