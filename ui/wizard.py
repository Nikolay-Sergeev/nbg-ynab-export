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
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QFont
from PyQt5.QtCore import Qt
from PyQt5.QtSvg import QSvgRenderer

# Fix relative imports when running directly
if __name__ == "__main__":
    # Add parent directory to path so imports work
    sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    from ui.controller import WizardController
    from ui.pages.import_file import ImportFilePage
    from ui.pages.auth import YNABAuthPage
    from ui.pages.actual_auth import ActualAuthPage
    from ui.pages.account_select import AccountSelectionPage  # Using standard implementation
    from ui.pages.transactions import (TransactionsPage)

    from ui.pages.review_upload import (ReviewAndUploadPage)

    from ui.pages.finish_page import FinishPage
else:
    # Normal relative imports when imported as a module
    from .controller import WizardController
    from .pages.import_file import ImportFilePage
    from .pages.auth import YNABAuthPage
    from .pages.actual_auth import ActualAuthPage
    from .pages.account_select import AccountSelectionPage  # Using standard implementation
    from .pages.transactions import (TransactionsPage)

    from .pages.review_upload import (ReviewAndUploadPage)

    from .pages.finish_page import FinishPage

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCE_DIR = os.path.join(PROJECT_ROOT, "resources")
ICON_DIR = os.path.join(RESOURCE_DIR, "icons")
STYLE_PATH = os.path.join(RESOURCE_DIR, "style.qss")
ICON_PATH = os.path.join(ICON_DIR, "app_icon.svg")


class StepLabel(QLabel):
    """Sidebar step label with selectable style and click handling."""

    def __init__(self, text: str):
        super().__init__(text)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setContentsMargins(0, 4, 0, 4)
        # Show hand cursor for clickable items
        self.setCursor(Qt.PointingHandCursor)

        # Use system font on macOS
        if sys.platform.startswith('darwin'):
            self.setFont(QFont(".AppleSystemUIFont", 13))
        else:
            # Replace San Francisco with Segoe UI
            self.setFont(QFont("Segoe UI", 13))

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
        print("[Wizard] closeEvent triggered. "
              "Attempting to stop all worker threads...")
        try:
            for page_id in self.pageIds():
                page = self.page(page_id)
                if page is None:
                    continue
                print(f"[Wizard] Checking page id {page_id}: "
                      f"{type(page).__name__}")
                for attr in ("worker", "review_upload_worker"):
                    worker = getattr(page, attr, None)
                    if worker is not None:
                        print(f"[Wizard] Found worker attribute '{attr}' "
                              f"on page id {page_id}.")
                        if hasattr(worker, 'isRunning'):
                            print(f"[Wizard] Worker is running: {worker.isRunning()}")
                            if worker.isRunning():
                                print(f"[Thread] Stopping {attr} thread on "
                                      f"page id {page_id}...")
                                worker.quit()
                                worker.wait(2000)
        except Exception as e:
            print(f"[Thread] Exception while stopping threads: {e}")
            traceback.print_exc()
        super().closeEvent(event)

    def initializePage(self, id):
        print(f"[Wizard] initializePage called for page id {id} "
              f"({type(self.page(id)).__name__})")
        super().initializePage(id)

    def nextId(self):
        # Custom nextId logic to ensure finish page is shown after ReviewAndUploadPage
        current_id = self.currentId()
        # Assuming page IDs are added in order:
        # 0=Import, 1=Auth, 2=Account, 3=Transactions, 4=Review, 5=Finish
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
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)  # No margins

        # Create controller for business logic
        self.controller = WizardController()

        # Create a container for the pages and navigation buttons
        page_container = QWidget()
        page_container_layout = QVBoxLayout(page_container)
        page_container_layout.setContentsMargins(0, 0, 0, 0)  # No margins
        page_container_layout.setSpacing(0)  # No spacing between elements

        # Create stacked widget for pages
        self.pages_stack = QStackedWidget()
        page_container_layout.addWidget(self.pages_stack)

        # Create navigation buttons
        nav_button_container = QWidget()
        nav_button_container.setObjectName("nav-button-container")
        nav_button_container.setMinimumHeight(60)  # Ensure consistent height
        nav_button_layout = QHBoxLayout(nav_button_container)
        nav_button_layout.setContentsMargins(20, 10, 20, 10)  # Add some padding

        # Back button
        self.back_button = QPushButton("Back")
        self.back_button.setObjectName("back-btn")
        self.back_button.setFixedWidth(120)
        self.back_button.setFixedHeight(40)
        self.back_button.clicked.connect(self.go_back)
        nav_button_layout.addWidget(self.back_button)

        # Add spacer to push buttons to sides
        nav_button_layout.addStretch(1)

        # Next/Continue button
        self.next_button = QPushButton("Continue")
        self.next_button.setObjectName("continue-btn")
        self.next_button.setFixedWidth(120)
        self.next_button.setFixedHeight(40)
        self.next_button.clicked.connect(self.go_forward)
        nav_button_layout.addWidget(self.next_button)

        # Add a separator line above buttons
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setObjectName("nav-separator")
        separator.setStyleSheet("background-color: #E1E3E5; max-height: 1px;")
        page_container_layout.addWidget(separator)

        # Add buttons to page container layout
        page_container_layout.addWidget(nav_button_container)

        # Add page container to content layout
        content_layout.addWidget(page_container)

        # Create all pages (original pages from QWizard)
        self.import_page = ImportFilePage(self.controller)
        self.auth_page = YNABAuthPage(self.controller)
        self.actual_auth_page = ActualAuthPage(self.controller)
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
        # Include Actual auth page in stack for navigation, though not part of linear order
        self.pages_stack.addWidget(self.actual_auth_page)

        # Connect page signals - ensure all pages emit completeChanged signal
        # Create an empty signal handler for pages that might not have completeChanged yet
        for i in range(self.pages_stack.count()):
            page = self.pages_stack.widget(i)
            try:
                page.completeChanged.connect(self.update_nav_buttons)
                print(f"[SidebarWizardWindow] Connected completeChanged for {type(page).__name__}")
            except (AttributeError, TypeError) as e:
                print(f"[SidebarWizardWindow] Could not connect completeChanged for {type(page).__name__}: {e}")

        # Add extra safety to connect specific pages we know should have the signal
        for page in [self.import_page, self.auth_page, self.account_page,
                     self.transactions_page, self.review_page, self.finish_page]:
            try:
                if not page.receivers(page.completeChanged):
                    page.completeChanged.connect(self.update_nav_buttons)
            except (AttributeError, TypeError):
                pass

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

            # Update navigation button states
            self.update_nav_buttons()

    def go_back(self):
        """Go to the previous page"""
        # Special-case: if on Actual auth page, go back to Import (logical step 0)
        if self.pages_stack.currentWidget() is getattr(self, 'actual_auth_page', None):
            self.go_to_page(0)
            return
        current = self.pages_stack.currentIndex()
        if current > 0:
            self.go_to_page(current - 1)

    def go_forward(self):
        """Go to the next page"""
        current = self.pages_stack.currentIndex()
        if current < self.pages_stack.count() - 1:
            # Get current page
            page = self.pages_stack.currentWidget()

            # Check if page is complete before proceeding
            if hasattr(page, 'isComplete') and not page.isComplete():
                print(f"[SidebarWizardWindow] Page {current} is not complete, cannot proceed")
                return

            # Check if page has a validate_and_proceed method
            if hasattr(page, 'validate_and_proceed'):
                print(f"[SidebarWizardWindow] Using validate_and_proceed for page {current}")
                result = page.validate_and_proceed()
                if not result:
                    print(f"[SidebarWizardWindow] validate_and_proceed returned "
                          f"False for page {current}")
            else:
                # If no validation needed, proceed to next page, with special handling for Actual export
                print(f"[SidebarWizardWindow] No validate_and_proceed method "
                      f"for page {current}, proceeding")
                # If leaving Import page and target is Actual (CSV), export and jump to Finish
                if current == 0 and getattr(self.controller, 'export_target', 'YNAB') == 'ACTUAL':
                    try:
                        file_path = getattr(self.import_page, 'file_path', None)
                        if file_path:
                            df = self.controller.converter.convert_to_actual(file_path)
                            # Save export path hint on window for FinishPage
                            # The converter writes to SETTINGS_DIR; reconstruct path similarly
                            from services.conversion_service import generate_actual_output_filename
                            export_path = generate_actual_output_filename(file_path)
                            self.actual_export_path = export_path
                            print(f"[Wizard] Actual CSV saved to {export_path}")
                        else:
                            print("[Wizard] No file_path set on import page for Actual export")
                    except Exception as e:
                        print(f"[Wizard] Error exporting for Actual: {e}")
                    # Jump to Finish page (last index)
                    self.go_to_page(self.pages_stack.count() - 1)
                # If leaving Import page and target is Actual API, go to Actual auth page and keep sidebar on step 1
                elif current == 0 and getattr(self.controller, 'export_target', 'YNAB') == 'ACTUAL_API':
                    if hasattr(self, 'actual_auth_page') and self.actual_auth_page is not None:
                        page = self.actual_auth_page
                        if hasattr(page, 'initializePage'):
                            page.initializePage()
                        self.pages_stack.setCurrentWidget(page)
                        self.update_sidebar(1)
                        self.update_nav_buttons()
                    else:
                        # Fallback to standard auth page if Actual page is unavailable
                        self.go_to_page(1)
                else:
                    self.go_to_page(current + 1)
        elif current == self.pages_stack.count() - 1:
            # On the last page, check if we should close the app
            page = self.pages_stack.currentWidget()
            if hasattr(page, 'validate_and_proceed'):
                print("[SidebarWizardWindow] Calling validate_and_proceed on final page")
                page.validate_and_proceed()
            else:
                print("[SidebarWizardWindow] Closing application from final page")
                self.close()

    def update_nav_buttons(self):
        """Update navigation buttons based on current page"""
        current = self.pages_stack.currentIndex()

        # First page has Exit button instead of Back
        if current == 0:
            self.back_button.setText("Exit")
            self.back_button.setEnabled(True)
            try:
                self.back_button.clicked.disconnect()
            except Exception as e:
                print(f"[SidebarWizardWindow] Error disconnecting back button: {e}")
                pass
            self.back_button.clicked.connect(self.close)
        else:
            self.back_button.setText("Back")
            self.back_button.setEnabled(True)
            try:
                self.back_button.clicked.disconnect()
            except Exception as e:
                print(f"[SidebarWizardWindow] Error disconnecting back button: {e}")
                pass
            self.back_button.clicked.connect(self.go_back)

        # Hide back button on last page
        if current == self.pages_stack.count() - 1:
            self.back_button.hide()
        else:
            self.back_button.show()

        # Next button text changes on last page
        if current == self.pages_stack.count() - 1:
            self.next_button.setText("Finish")
        else:
            self.next_button.setText("Continue")

        # Check if current page has isComplete method to determine if next is enabled
        page = self.pages_stack.currentWidget()
        if hasattr(page, 'isComplete'):
            try:
                is_complete = page.isComplete()
                self.next_button.setEnabled(is_complete)
                print(f"[SidebarWizardWindow] Page {current} isComplete: "
                      f"{is_complete}")
            except Exception as e:
                print(f"[SidebarWizardWindow] Error checking isComplete: "
                      f"{e}")
                self.next_button.setEnabled(False)
        else:
            print(f"[SidebarWizardWindow] Page {current} has no isComplete "
                  f"method")
            self.next_button.setEnabled(True)


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
        app.setFont(QFont("Segoe UI", 13))  # Replace San Francisco with Segoe UI
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

        if (sys.platform.startswith('linux') and
            not os.environ.get('DISPLAY') and
                not os.environ.get('WAYLAND_DISPLAY')):
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
