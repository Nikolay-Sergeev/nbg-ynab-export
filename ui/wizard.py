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
    QProxyStyle,
    QStyleFactory,
    QFrame,
    QStackedWidget,
    QPushButton,
)
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QFont, QFontDatabase
from PyQt5.QtCore import Qt
from PyQt5.QtSvg import QSvgRenderer

# Fix relative imports when running directly
if __name__ == "__main__":
    # Add parent directory to path so imports work
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ui.controller import WizardController
    from ui.pages.import_file import ImportFilePage
    from ui.pages.auth import YNABAuthPage
    from ui.pages.account_select import AccountSelectionPage
    from ui.pages.transactions import TransactionsPage
    from ui.pages.review_upload import ReviewAndUploadPage
    from ui.pages.finish_page import FinishPage
else:
    # Normal relative imports when imported as a module
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
    """Sidebar step label with selectable style and click handling."""

    def __init__(self, text: str):
        super().__init__(text)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setContentsMargins(0, 4, 0, 4)
        self.setCursor(Qt.PointingHandCursor)  # Show hand cursor for clickable items
        
        # Use system font on macOS
        if sys.platform.startswith('darwin'):
            self.setFont(QFont(".AppleSystemUIFont", 13))
        else:
            self.setFont(QFont("San Francisco", 13))
            
        # Store index for navigation
        self.step_index = -1
        self.set_selected(False)

    def set_selected(self, selected: bool):
        if selected:
            # Use more prominent styling for selected step
            self.setStyleSheet(
                "background-color:#0066cc;color:white;border-radius:6px;"
                "padding:8px 16px;font-size:13pt;font-weight:bold;"
                "margin:2px 0px;border-left:4px solid #0066cc;"
            )
        else:
            self.setStyleSheet(
                "color:#333;padding:8px 16px;font-size:13pt;margin:2px 0px;"
                "border-left:4px solid transparent;"
            )
    
    def mousePressEvent(self, event):
        # Notify parent window to navigate to this step
        window = self.window()
        if hasattr(window, "go_to_page") and self.step_index >= 0:
            window.go_to_page(self.step_index)
        
        # Call parent implementation
        super().mousePressEvent(event)

class MacOSProxyStyle(QProxyStyle):
    """
    Custom style proxy to better match macOS native UI patterns.
    """
    def __init__(self):
        super().__init__(QStyleFactory.create("Fusion"))
        
    def drawControl(self, element, option, painter, widget=None):
        super().drawControl(element, option, painter, widget)
        
    def pixelMetric(self, metric, option=None, widget=None):
        # Adjust spacing for macOS
        if metric in (self.PM_ButtonMargin, self.PM_LayoutHorizontalSpacing):
            return 8
        return super().pixelMetric(metric, option, widget)
        
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
    """Custom wizard window with navigation sidebar and stacked widget content."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NBG/Revolut to YNAB Wizard")
        
        # Use dimensions that fit content properly
        fixed_w, fixed_h = 960, 600
            
        self.setFixedSize(fixed_w, fixed_h)

        # Create single widget with no borders or spacing
        central = QWidget()
        central.setStyleSheet("QWidget { border: none; }")  # Ensure no borders anywhere
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)  # No margins
        main_layout.setSpacing(0)  # No spacing between widgets

        # Setup sidebar with step indicators
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
        
        # Use macOS-style margins and spacing
        if sys.platform.startswith('darwin'):
            sidebar_layout.setContentsMargins(10, 18, 0, 18)
            sidebar_layout.setSpacing(10)
        else:
            sidebar_layout.setContentsMargins(10, 16, 0, 16)
            sidebar_layout.setSpacing(12)
            
        for i, t in enumerate(step_titles):
            lbl = StepLabel(t)
            lbl.step_index = i  # Store the index for navigation
            self.step_labels.append(lbl)
            sidebar_layout.addWidget(lbl)
        
        sidebar_layout.addStretch()
        side_widget = QWidget()
        side_widget.setLayout(sidebar_layout)
        
        # Use consistent styling for sidebar - fixed width
        side_widget.setFixedWidth(180)
        side_widget.setStyleSheet("background-color: #F7F8FA;")  # Light gray background
            
        # Add sidebar to main layout
        main_layout.addWidget(side_widget)

        # Create content widget
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: white;")  # White background
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)  # No margins
        
        # Create controller for business logic
        self.controller = WizardController()
        
        # Create stacked widget for pages
        self.pages_stack = QStackedWidget()
        
        # Create all pages (original pages from QWizard)
        self.import_page = ImportFilePage(self.controller)
        self.auth_page = YNABAuthPage(self.controller)
        self.account_page = AccountSelectionPage(self.controller)
        self.transactions_page = TransactionsPage(self.controller)
        self.review_page = ReviewAndUploadPage(self.controller)
        self.finish_page = FinishPage()
        
        # Add pages to stacked widget
        self.pages_stack.addWidget(self.import_page)
        self.pages_stack.addWidget(self.auth_page)
        self.pages_stack.addWidget(self.account_page)
        self.pages_stack.addWidget(self.transactions_page)
        self.pages_stack.addWidget(self.review_page)
        self.pages_stack.addWidget(self.finish_page)
        
        # Add stacked widget to content layout
        content_layout.addWidget(self.pages_stack)
        
        # Add content widget to main layout
        main_layout.addWidget(content_widget, 1)  # Stretch factor of 1
        
        self.setCentralWidget(central)
        
        # Start on the first page
        self.go_to_page(0)

    def update_sidebar(self, step: int):
        """Update the sidebar labels to show the current step."""
        for i, lbl in enumerate(self.step_labels):
            lbl.set_selected(i == step)
    
    def go_to_page(self, index):
        """Navigate to the specified page index."""
        if 0 <= index < self.pages_stack.count():
            # Call initialize on the page we're going to if available
            page = self.pages_stack.widget(index)
            if hasattr(page, 'initializePage'):
                page.initializePage()
                
            # Switch to the page
            self.pages_stack.setCurrentIndex(index)
            
            # Update sidebar
            self.update_sidebar(index)


def load_style(app: QApplication):
    """Load QSS and apply a macOS-native palette."""
    # Load stylesheets
    if os.path.exists(STYLE_PATH):
        try:
            with open(STYLE_PATH, "r") as f:
                app.setStyleSheet(f.read())
            print(f"[QSS] Loaded style from {STYLE_PATH}")
        except Exception as e:
            print(f"[QSS] Failed to load style.qss: {e}")
    else:
        print(f"[QSS] style.qss not found at {STYLE_PATH}. UI will use default style.")
        
    # Load and set app icon
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

    # Setup platform-specific style
    from PyQt5.QtGui import QPalette, QColor
    
    # Use system font on macOS
    if sys.platform.startswith('darwin'):
        # Try to load system font
        system_font = QFont(".AppleSystemUIFont", 13)
        app.setFont(system_font)
        
        # Apply macOS style proxy for better native feel
        app.setStyle(MacOSProxyStyle())
        
        # Use more macOS-like palette (subtle colors)
        pal = app.palette()
        pal.setColor(QPalette.Window, QColor("#F5F5F7"))
        pal.setColor(QPalette.WindowText, QColor("#1D1D1F"))
        pal.setColor(QPalette.Base, QColor("#FFFFFF"))
        pal.setColor(QPalette.Button, QColor("#F5F5F7"))
        pal.setColor(QPalette.Text, QColor("#1D1D1F"))
        pal.setColor(QPalette.ButtonText, QColor("#1D1D1F"))
        pal.setColor(QPalette.Highlight, QColor("#0071E3"))
        app.setPalette(pal)
    else:
        # For other platforms use Fusion with light palette
        app.setStyle("Fusion")
        app.setFont(QFont("San Francisco", 13))
        pal = app.palette()
        pal.setColor(QPalette.Window, QColor("#F7F7F7"))
        pal.setColor(QPalette.WindowText, Qt.black)
        pal.setColor(QPalette.Base, QColor("#FFFFFF"))
        pal.setColor(QPalette.Button, QColor("#FFFFFF"))
        pal.setColor(QPalette.Text, Qt.black)
        pal.setColor(QPalette.ButtonText, Qt.black)
        app.setPalette(pal)

def main():
    try:
        # On Linux headless, use offscreen; skip on macOS
        if sys.platform.startswith('linux') and not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY'):
            os.environ['QT_QPA_PLATFORM'] = 'offscreen'
            
        app = QApplication(sys.argv)
        
        # Set object name for platform-specific styling in QSS
        if sys.platform.startswith('darwin'):
            app.setObjectName("macOS")
            # Set macOS-specific attributes for better integration
            app.setAttribute(Qt.AA_DontShowIconsInMenus, True)
        
        load_style(app)
        window = SidebarWizardWindow()
        window.show()
        print("[Wizard] Wizard UI started. Entering event loop.")
        sys.exit(app.exec_())
    except Exception as e:
        print(f"[Main] Exception in main(): {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
