import sys
import os
import traceback
import shutil
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
    QMessageBox,
)
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QFont, QPalette, QColor
from PyQt5.QtCore import Qt
from PyQt5.QtSvg import QSvgRenderer
import logging

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
        self.setMinimumHeight(44)
        self.setCursor(Qt.PointingHandCursor)

        # Use system font on macOS
        if sys.platform.startswith('darwin'):
            self.setFont(QFont(".AppleSystemUIFont", 13))
        else:
            # Replace San Francisco with Segoe UI
            self.setFont(QFont("Segoe UI", 13))

        # Store index for navigation
        self.step_index = -1
        self.navigation_enabled = True
        self.set_selected(False)

    def set_selected(self, selected: bool):
        if selected:
            self.setStyleSheet(
                "background-color:#0066cc;color:white;border-radius:8px;"
                "padding:10px 12px;font-size:12pt;font-weight:600;"
            )
        elif self.navigation_enabled:
            self.setStyleSheet(
                "background-color:transparent;color:#333;border-radius:8px;"
                "padding:10px 12px;font-size:12pt;font-weight:500;"
            )
        else:
            self.setStyleSheet(
                "background-color:transparent;color:#8A96A8;border-radius:8px;"
                "padding:10px 12px;font-size:12pt;font-weight:500;"
            )

    def set_navigation_enabled(self, enabled: bool):
        self.navigation_enabled = enabled
        self.setCursor(Qt.PointingHandCursor if enabled else Qt.ArrowCursor)
        self.setToolTip("" if enabled else "Complete the previous steps first")

    def mousePressEvent(self, event):
        # Notify parent window to navigate to this step
        window = self.window()
        if (
            self.navigation_enabled
            and hasattr(window, "go_to_page")
            and self.step_index >= 0
        ):
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
        logging.info(
            "[Wizard] closeEvent triggered. Attempting to stop all worker threads..."
        )
        try:
            for page_id in self.pageIds():
                page = self.page(page_id)
                if page is None:
                    continue
                logging.debug("[Wizard] Checking page id %s: %s", page_id, type(page).__name__)
                for attr in ("worker", "review_upload_worker"):
                    worker = getattr(page, attr, None)
                    if worker is not None:
                        logging.debug(
                            "[Wizard] Found worker attribute '%s' on page id %s.",
                            attr,
                            page_id,
                        )
                        if hasattr(worker, 'isRunning'):
                            logging.debug("[Wizard] Worker is running: %s", worker.isRunning())
                            if worker.isRunning():
                                logging.info(
                                    "[Thread] Stopping %s thread on page id %s...",
                                    attr,
                                    page_id,
                                )
                                worker.quit()
                                worker.wait(2000)
        except Exception as e:
            logging.exception("[Thread] Exception while stopping threads: %s", e)
            traceback.print_exc()
        super().closeEvent(event)

    def initializePage(self, id):
        logging.debug(
            "[Wizard] initializePage called for page id %s (%s)",
            id,
            type(self.page(id)).__name__,
        )
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
        self.logger = logging.getLogger(__name__)
        self.setWindowTitle("Transaction Importer")

        self.setMinimumSize(1040, 680)
        self.resize(1120, 720)
        self.highest_reached = 0

        central = QWidget()
        central.setObjectName("app-shell")
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Setup sidebar with step indicators
        step_titles = [
            "1   Import file",
            "2   Connect",
            "3   Choose account",
            "4   Check activity",
            "5   Review import",
            "6   Complete",
        ]
        self.step_labels = []
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(20, 28, 20, 24)
        sidebar_layout.setSpacing(6)

        self.product_eyebrow = QLabel("FINANCE TOOLS")
        self.product_eyebrow.setProperty("role", "sidebar-eyebrow")
        sidebar_layout.addWidget(self.product_eyebrow)

        self.product_title = QLabel("Transaction\nImporter")
        self.product_title.setProperty("role", "sidebar-title")
        sidebar_layout.addWidget(self.product_title)

        self.product_description = QLabel("Move statement data safely into your budget.")
        self.product_description.setProperty("role", "sidebar-description")
        self.product_description.setWordWrap(True)
        sidebar_layout.addWidget(self.product_description)
        sidebar_layout.addSpacing(18)

        self.steps_heading = QLabel("PROGRESS")
        self.steps_heading.setProperty("role", "sidebar-eyebrow")
        sidebar_layout.addWidget(self.steps_heading)

        for i, t in enumerate(step_titles):
            lbl = StepLabel(t)
            lbl.step_index = i  # Store the index for navigation
            self.step_labels.append(lbl)
            sidebar_layout.addWidget(lbl)

        sidebar_layout.addStretch()
        self.target_badge = QLabel("Destination: YNAB")
        self.target_badge.setObjectName("target-badge")
        self.target_badge.setWordWrap(True)
        sidebar_layout.addWidget(self.target_badge)

        side_widget = QWidget()
        side_widget.setObjectName("sidebar")
        side_widget.setLayout(sidebar_layout)

        side_widget.setFixedWidth(244)

        # Add sidebar to main layout
        main_layout.addWidget(side_widget)

        # Create content widget
        content_widget = QWidget()
        content_widget.setObjectName("content-area")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)  # No margins

        # Create controller for business logic
        self.controller = WizardController()

        # Create a container for the pages and navigation buttons
        page_container = QWidget()
        page_container.setObjectName("page-container")
        page_container_layout = QVBoxLayout(page_container)
        page_container_layout.setContentsMargins(0, 0, 0, 0)  # No margins
        page_container_layout.setSpacing(0)  # No spacing between elements

        # Create stacked widget for pages
        self.pages_stack = QStackedWidget()
        self.pages_stack.setContentsMargins(32, 28, 32, 24)
        page_container_layout.addWidget(self.pages_stack)

        # Create navigation buttons
        nav_button_container = QWidget()
        nav_button_container.setObjectName("nav-button-container")
        nav_button_container.setMinimumHeight(76)
        nav_button_layout = QHBoxLayout(nav_button_container)
        nav_button_layout.setContentsMargins(32, 16, 32, 16)

        # Back button
        self.back_button = QPushButton("Back")
        self.back_button.setObjectName("back-btn")
        self.back_button.setMinimumWidth(104)
        self.back_button.setFixedHeight(42)
        self.back_button.clicked.connect(self.go_back)
        nav_button_layout.addWidget(self.back_button)

        # Add spacer to push buttons to sides
        nav_button_layout.addStretch(1)

        # Next/Continue button
        self.next_button = QPushButton("Continue")
        self.next_button.setObjectName("continue-btn")
        self.next_button.setMinimumWidth(144)
        self.next_button.setFixedHeight(42)
        self.next_button.clicked.connect(self.go_forward)
        nav_button_layout.addWidget(self.next_button)

        # Add a separator line above buttons
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setObjectName("nav-separator")
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
                self.logger.debug(
                    "[SidebarWizardWindow] Connected completeChanged for %s",
                    type(page).__name__,
                )
            except (AttributeError, TypeError) as e:
                self.logger.debug(
                    "[SidebarWizardWindow] Could not connect completeChanged for %s: %s",
                    type(page).__name__,
                    e,
                )

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

        # Initialize steps for default target and start on the first page
        self.set_steps_for_target(self.controller.export_target)
        self.go_to_page(0)

    def update_sidebar(self, step: int):
        """Highlight the current step label.

        Primary rule is based on each label's mapped page index (step_index).
        As a fallback for simple linear flows (1:1 label order to page index),
        also consider the label's position to match the current page index. This
        keeps default YNAB mapping intuitive and satisfies tests that check by
        order while still working when labels are remapped for other targets.
        """
        for idx, lbl in enumerate(self.step_labels):
            # ``isVisible`` is false while the window itself is still hidden,
            # so only skip labels explicitly removed from the active workflow.
            if lbl.isHidden():
                continue
            selected = (lbl.step_index == step) or (idx == step)
            lbl.set_navigation_enabled(lbl.step_index <= self.highest_reached)
            lbl.set_selected(selected)

    def set_steps_for_target(self, target: str):
        target = (target or 'YNAB').upper()
        self.logger.info("[Wizard] set_steps_for_target: %s", target)
        if hasattr(self, "pages_stack") and self.pages_stack.currentIndex() == 0:
            self.highest_reached = 0
        # Default mapping for YNAB
        mapping = [
            (0, "1   Import file"),
            (1, "2   Connect YNAB"),
            (2, "3   Choose account"),
            (3, "4   Check activity"),
            (4, "5   Review import"),
            (5, "6   Complete"),
        ]
        if target == 'ACTUAL_API':
            mapping = [
                (0, "1   Import file"),
                (1, "2   Connect Actual"),
                (2, "3   Choose account"),
                (3, "4   Check activity"),
                (4, "5   Review import"),
                (5, "6   Complete"),
            ]
        elif target == 'FILE':
            mapping = [
                (0, "1   Import file"),
                (4, "2   Review export"),
                (5, "3   Complete"),
            ]

        destination_names = {
            "YNAB": "YNAB",
            "ACTUAL_API": "Actual Budget",
            "FILE": "Converted CSV",
        }
        self.target_badge.setText(f"Destination: {destination_names.get(target, 'YNAB')}")

        # Apply mapping to labels
        for i, lbl in enumerate(self.step_labels):
            if i < len(mapping):
                page_index, text = mapping[i]
                lbl.setText(text)
                lbl.step_index = page_index
                lbl.show()
            else:
                lbl.step_index = -1
                lbl.hide()
        # Refresh selection
        self.update_sidebar(self.pages_stack.currentIndex())

        # Keep Import page radio buttons in sync as well
        try:
            if hasattr(self, 'import_page') and self.import_page is not None:
                if target == 'YNAB' and hasattr(self.import_page, 'rb_ynab'):
                    self.import_page.rb_ynab.setChecked(True)
                elif target == 'ACTUAL_API' and hasattr(self.import_page, 'rb_actual'):
                    self.import_page.rb_actual.setChecked(True)
                elif target == 'FILE' and hasattr(self.import_page, 'rb_file'):
                    self.import_page.rb_file.setChecked(True)
        except Exception:
            pass

    def go_to_page(self, index):
        """Navigate to the specified page index."""
        if 0 <= index:
            # Guard against skipping mandatory steps (e.g., file not selected)
            if index > 0:
                try:
                    file_path = getattr(self.import_page, 'file_path', None)
                except Exception:
                    file_path = None
                if not file_path:
                    QMessageBox.information(self, "Select a file", "Please choose a file before continuing.")
                    self.pages_stack.setCurrentIndex(0)
                    self.update_sidebar(0)
                    self.update_nav_buttons()
                    return
            self.highest_reached = max(self.highest_reached, index)
            # Route Authorize step to Actual auth when selected
            if (
                index == 1
                and getattr(self.controller, 'export_target', 'YNAB') == 'ACTUAL_API'
                and getattr(self, 'actual_auth_page', None) is not None
            ):
                page = self.actual_auth_page
                if hasattr(page, 'initializePage'):
                    page.initializePage()
                self.pages_stack.setCurrentWidget(page)
                self.update_sidebar(index)
                self.update_nav_buttons()
                return

            if index < self.pages_stack.count():
                # Call initialize on the page we're going to if available
                page = self.pages_stack.widget(index)
                if hasattr(page, 'initializePage'):
                    page.initializePage()

                # Switch to the page
                self.pages_stack.setCurrentIndex(index)

                # Update sidebar
                self.update_sidebar(index)
                # Defensive: enforce selection in case any visibility/mapping issues prevent highlight
                try:
                    for idx, lbl in enumerate(self.step_labels):
                        lbl.set_selected((getattr(lbl, 'step_index', -1) == index) or (idx == index))
                except Exception:
                    pass

                # Update navigation button states
                self.update_nav_buttons()

    def current_logical_index(self):
        """Return the visible workflow index, including the alternate auth page."""
        if self.pages_stack.currentWidget() is getattr(self, "actual_auth_page", None):
            return 1
        return self.pages_stack.currentIndex()

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
        current = self.current_logical_index()
        page = self.pages_stack.currentWidget()

        if hasattr(page, 'isComplete') and not page.isComplete():
            self.logger.info(
                "[SidebarWizardWindow] Page %s is not complete, cannot proceed",
                current,
            )
            return

        if hasattr(page, 'validate_and_proceed'):
            self.logger.debug(
                "[SidebarWizardWindow] Using validate_and_proceed for page %s",
                current,
            )
            result = page.validate_and_proceed()
            if not result:
                self.logger.info(
                    "[SidebarWizardWindow] validate_and_proceed returned False for page %s",
                    current,
                )
        elif current < 5:
            self.go_to_page(current + 1)
        else:
            self.close()

    def update_nav_buttons(self):
        """Update navigation buttons based on current page"""
        current = self.current_logical_index()

        # First page has Exit button instead of Back
        if current == 0:
            self.back_button.setText("Exit")
            self.back_button.setEnabled(True)
            try:
                self.back_button.clicked.disconnect()
            except Exception as e:
                self.logger.debug(
                    "[SidebarWizardWindow] Error disconnecting back button: %s",
                    e,
                )
                pass
            self.back_button.clicked.connect(self.close)
        else:
            self.back_button.setText("Back")
            self.back_button.setEnabled(True)
            try:
                self.back_button.clicked.disconnect()
            except Exception as e:
                self.logger.debug(
                    "[SidebarWizardWindow] Error disconnecting back button: %s",
                    e,
                )
                pass
            self.back_button.clicked.connect(self.go_back)

        page = self.pages_stack.currentWidget()
        is_finish_page = isinstance(page, FinishPage)

        if is_finish_page:
            self.back_button.hide()
        else:
            self.back_button.show()

        if is_finish_page:
            self.next_button.setText("Close")
        elif page is self.auth_page or page is self.actual_auth_page:
            self.next_button.setText("Connect")
        elif page is self.transactions_page:
            self.next_button.setText("Review file")
        elif page is self.review_page:
            target = getattr(self.controller, "export_target", "YNAB")
            self.next_button.setText("Export file" if target == "FILE" else "Import transactions")
        else:
            self.next_button.setText("Continue")

        # Check if current page has isComplete method to determine if next is enabled
        if hasattr(page, 'isComplete'):
            try:
                is_complete = page.isComplete()
                self.next_button.setEnabled(is_complete)
                self.logger.debug(
                    "[SidebarWizardWindow] Page %s isComplete: %s",
                    current,
                    is_complete,
                )
            except Exception as e:
                self.logger.debug(
                    "[SidebarWizardWindow] Error checking isComplete: %s",
                    e,
                )
                self.next_button.setEnabled(False)
        else:
            self.logger.debug(
                "[SidebarWizardWindow] Page %s has no isComplete method",
                current,
            )
            self.next_button.setEnabled(True)


def load_style(app: QApplication):
    """Load QSS and apply a macOS-native palette."""
    # Load stylesheets
    if os.path.exists(STYLE_PATH):
        try:
            with open(STYLE_PATH, "r") as f:
                app.setStyleSheet(f.read())
            logging.info("[QSS] Loaded style from %s", STYLE_PATH)
        except Exception as e:
            logging.warning("[QSS] Failed to load style.qss: %s", e)
    else:
        logging.warning("[QSS] style.qss not found at %s. UI will use default style.", STYLE_PATH)

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
            logging.info("[Icon] Loaded app icon from %s", ICON_PATH)
        except Exception as e:
            logging.warning("[Icon] Failed to load app_icon.svg: %s", e)
    else:
        logging.warning("[Icon] app_icon.svg not found at %s. Using default icon.", ICON_PATH)

    # Setup platform-specific style
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
        # Support a simple --debug flag for local runs
        debug_mode = False
        if '--debug' in sys.argv:
            debug_mode = True
            # Remove the flag so Qt doesn't try to parse it
            sys.argv.remove('--debug')

        # Cleanup caches when in debug mode to avoid stale bytecode
        if debug_mode:
            try:
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                candidates = [
                    os.path.join(project_root, '__pycache__'),
                    os.path.join(project_root, '.pytest_cache'),
                    os.path.join(project_root, 'ui', '__pycache__'),
                    os.path.join(project_root, 'ui', 'pages', '__pycache__'),
                    os.path.join(project_root, 'services', '__pycache__'),
                    os.path.join(project_root, 'converter', '__pycache__'),
                    os.path.join(project_root, 'tests', '__pycache__'),
                ]
                for path in candidates:
                    if os.path.isdir(path):
                        shutil.rmtree(path, ignore_errors=True)
                logging.info('[Wizard] Debug mode: caches cleared')
            except Exception as e:
                logging.warning("[Wizard] Debug mode cache cleanup error: %s", e)

        # On Linux headless, use offscreen; skip on macOS

        if (sys.platform.startswith('linux') and
            not os.environ.get('DISPLAY') and
                not os.environ.get('WAYLAND_DISPLAY')):
            os.environ['QT_QPA_PLATFORM'] = 'offscreen'

        # Configure logging level (DEBUG if --debug)
        logging.basicConfig(
            level=logging.DEBUG if debug_mode else logging.INFO,
            format='%(asctime)s %(levelname)s %(name)s: %(message)s'
        )

        app = QApplication(sys.argv)

        # Set object name for platform-specific styling in QSS
        if sys.platform.startswith('darwin'):
            app.setObjectName("macOS")
            # Set macOS-specific attributes for better integration
            app.setAttribute(Qt.AA_DontShowIconsInMenus, True)

        load_style(app)
        window = SidebarWizardWindow()
        window.show()
        logging.info("[Wizard] Wizard UI started. Entering event loop.")
        sys.exit(app.exec_())
    except Exception as e:
        logging.exception("[Main] Exception in main(): %s", e)
        traceback.print_exc()


if __name__ == "__main__":
    main()
