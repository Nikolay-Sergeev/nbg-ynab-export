import sys
import os
import traceback
from PyQt5.QtWidgets import (
    QApplication,
    QWizard,
    QMainWindow,
    QWidget,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
)
from PyQt5.QtGui import QIcon, QPixmap, QPainter
from PyQt5.QtCore import Qt
from PyQt5.QtSvg import QSvgRenderer
from .controller import WizardController
from .pages.import_file import ImportFilePage
from .pages.auth import YNABAuthPage
from .pages.account_select import AccountSelectionPage
from .pages.transactions import TransactionsPage
from .pages.review_upload import ReviewAndUploadPage
from .pages.finish_page import FinishPage

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STYLE_PATH = os.path.join(PROJECT_ROOT, "resources", "style.qss")
ICON_PATH = os.path.join(PROJECT_ROOT, "resources", "app_icon.svg")


class StepLabel(QLabel):
    """Sidebar step label with selectable style."""

    def __init__(self, text: str):
        super().__init__(text)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(32)
        self.set_selected(False)

    def set_selected(self, selected: bool):
        if selected:
            self.setStyleSheet(
                "background-color:#007AFF;color:white;border-radius:16px;"
                "padding:8px 16px;font-size:13pt;"
            )
        else:
            self.setStyleSheet(
                "color:#333;padding:8px 16px;font-size:13pt;"
            )

class RobustWizard(QWizard):
    def closeEvent(self, event):
        print("[Wizard] closeEvent triggered. Attempting to stop all worker threads...")
        try:
            for page_id in self.pageIds():
                page = self.page(page_id)
                if page is None:
                    continue
                print(f"[Wizard] Checking page id {page_id}: {type(page).__name__}")
                for attr in ("worker", "review_upload_worker"):
                    worker = getattr(page, attr, None)
                    if worker is not None:
                        print(f"[Wizard] Found worker attribute '{attr}' on page id {page_id}.")
                        if hasattr(worker, 'isRunning'):
                            print(f"[Wizard] Worker is running: {worker.isRunning()}")
                            if worker.isRunning():
                                print(f"[Thread] Stopping {attr} thread on page id {page_id}...")
                                worker.quit()
                                worker.wait(2000)
        except Exception as e:
            print(f"[Thread] Exception while stopping threads: {e}")
            traceback.print_exc()
        super().closeEvent(event)

    def initializePage(self, id):
        print(f"[Wizard] initializePage called for page id {id} ({type(self.page(id)).__name__})")
        super().initializePage(id)

    def nextId(self):
        # Custom nextId logic to ensure finish page is shown after ReviewAndUploadPage
        current_id = self.currentId()
        # Assuming page IDs are added in order: 0=Import, 1=Auth, 2=Account, 3=Transactions, 4=Review, 5=Finish
        if current_id == 4:
            return 5  # Go to FinishPage
        return super().nextId()


class SidebarWizardWindow(QMainWindow):
    """Main window embedding the wizard with a navigation sidebar."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NBG/Revolut to YNAB Wizard")
        self.resize(900, 600)

        central = QWidget()
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)

        step_titles = [
            "Import File",
            "Authorize",
            "Select Budget\nand Account",
            "Transactions",
            "Review",
            "Finish",
        ]
        self.step_labels = []
        sidebar_layout = QVBoxLayout()
        for t in step_titles:
            lbl = StepLabel(t)
            self.step_labels.append(lbl)
            sidebar_layout.addWidget(lbl)
        sidebar_layout.addStretch()
        side_widget = QWidget()
        side_widget.setLayout(sidebar_layout)
        side_widget.setFixedWidth(160)
        side_widget.setStyleSheet("background:#F7F7F7;")
        main_layout.addWidget(side_widget)

        self.controller = WizardController()
        self.wizard = RobustWizard()
        if sys.platform.startswith("darwin"):
            self.wizard.setWizardStyle(QWizard.MacStyle)
        else:
            self.wizard.setWizardStyle(QWizard.ModernStyle)
        self.wizard.setButtonLayout([])

        self.wizard.addPage(ImportFilePage(self.controller))
        self.wizard.addPage(YNABAuthPage(self.controller))
        self.wizard.addPage(AccountSelectionPage(self.controller))
        self.wizard.addPage(TransactionsPage(self.controller))
        self.wizard.addPage(ReviewAndUploadPage(self.controller))
        self.wizard.addPage(FinishPage())

        resource_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../resources")
        )
        icon_names = [
            "upload.svg",
            "info.svg",
            "info.svg",
            "spinner.svg",
            "error.svg",
            "success.svg",
        ]
        for pid, name in zip(self.wizard.pageIds(), icon_names):
            icon_path = os.path.join(resource_dir, name)
            if os.path.exists(icon_path):
                renderer_page = QSvgRenderer(icon_path)
                pixmap_page = QPixmap(24, 24)
                pixmap_page.fill(Qt.transparent)
                painter = QPainter(pixmap_page)
                renderer_page.render(painter)
                painter.end()
                self.wizard.page(pid).setPixmap(QWizard.BannerPixmap, pixmap_page)

        self.wizard.currentIdChanged.connect(self.update_sidebar)

        main_layout.addWidget(self.wizard, 1)
        self.setCentralWidget(central)
        self.update_sidebar(self.wizard.currentId())

    def update_sidebar(self, step: int):
        for i, lbl in enumerate(self.step_labels):
            lbl.set_selected(i == step)


def load_style(app: QApplication):
    if os.path.exists(STYLE_PATH):
        try:
            with open(STYLE_PATH, "r") as f:
                app.setStyleSheet(f.read())
            print(f"[QSS] Loaded style from {STYLE_PATH}")
        except Exception as e:
            print(f"[QSS] Failed to load style.qss: {e}")
    else:
        print(f"[QSS] style.qss not found at {STYLE_PATH}. UI will use default style.")
    if os.path.exists(ICON_PATH):
        try:
            renderer = QSvgRenderer(ICON_PATH)
            pixmap = QPixmap(128, 128)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            app.setWindowIcon(QIcon(pixmap))
            print(f"[Icon] Loaded app icon from {ICON_PATH}")
        except Exception as e:
            print(f"[Icon] Failed to load app_icon.svg: {e}")
    else:
        print(f"[Icon] app_icon.svg not found at {ICON_PATH}. Using default icon.")

def main():
    try:
        # On Linux headless, use offscreen; skip on macOS
        if sys.platform.startswith('linux') and not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY'):
            os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        app = QApplication(sys.argv)
        load_style(app)
        window = SidebarWizardWindow()
        if sys.platform.startswith('darwin'):
            window.show()
        else:
            window.showMaximized()
        print("[Wizard] Wizard UI started. Entering event loop.")
        sys.exit(app.exec_())
    except Exception as e:
        print(f"[Main] Exception in main(): {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
