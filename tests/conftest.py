import sys
import os

# UI tests create QApplication during module import. Select a display-free Qt
# backend before test modules load, unless the caller chose one explicitly.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

# Add the parent directory to the path so imports work correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
