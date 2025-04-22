import sys
import os
import traceback
from PyQt5.QtWidgets import QApplication, QWizard
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
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

def main():
    try:
        # On Linux headless, use offscreen; skip on macOS
        if sys.platform.startswith('linux') and not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY'):
            os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        app = QApplication(sys.argv)
        # Load QSS stylesheet
        STYLE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../resources/style.qss'))
        ICON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../resources/app_icon.svg'))
        if os.path.exists(STYLE_PATH):
            try:
                with open(STYLE_PATH, "r") as f:
                    app.setStyleSheet(f.read())
                print(f"[QSS] Loaded style from {STYLE_PATH}")
            except Exception as e:
                print(f"[QSS] Failed to load style.qss: {e}")
        else:
            print(f"[QSS] style.qss not found at {STYLE_PATH}. UI will use default style.")
        # Skipping icon setup to avoid Qt-related crash
        print("[Icon] Icon setup skipped.")
        print("[Debug] About to initialize WizardController")
        controller = WizardController()
        print("[Debug] WizardController initialized")
        print("[Debug] About to initialize RobustWizard")
        wizard = RobustWizard()
        print("[Debug] RobustWizard initialized")
        wizard.setWindowTitle("NBG/Revolut to YNAB Wizard")
        # Hide default QWizard footer buttons
        wizard.setButtonLayout([])
        # wizard.setOptions(QWizard.NoDefaultButton) # Causes segfault on macOS
        # Add pages
        wizard.addPage(ImportFilePage(controller))
        wizard.addPage(YNABAuthPage(controller))
        wizard.addPage(AccountSelectionPage(controller))
        wizard.addPage(TransactionsPage(controller))
        wizard.addPage(ReviewAndUploadPage(controller))
        wizard.addPage(FinishPage())
        wizard.showFullScreen()
        print("[Wizard] Wizard UI started. Entering event loop.")
        sys.exit(app.exec_())
    except Exception as e:
        print(f"[Main] Exception in main(): {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
