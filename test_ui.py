import os
import unittest
from PyQt5.QtWidgets import QApplication
from ui.wizard import StepLabel, load_style
from main import validate_input_file
import tempfile


class TestUIComponents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        cls.app = QApplication.instance() or QApplication([])

    def test_step_label_selection(self):
        label = StepLabel("Step")
        label.set_selected(True)
        self.assertIn("background-color", label.styleSheet())
        label.set_selected(False)
        self.assertIn("color:#333", label.styleSheet())

    def test_load_style_applies_stylesheet(self):
        load_style(self.app)
        self.assertTrue(self.app.styleSheet())


class TestValidateInputFile(unittest.TestCase):
    def test_validate_input_file_success(self):
        with tempfile.NamedTemporaryFile(suffix='.csv') as tmp:
            validate_input_file(tmp.name)

    def test_validate_input_file_missing(self):
        with self.assertRaises(FileNotFoundError):
            validate_input_file('nonexistent.csv')

    def test_validate_input_file_bad_ext(self):
        with tempfile.NamedTemporaryFile(suffix='.txt') as tmp:
            with self.assertRaises(ValueError):
                validate_input_file(tmp.name)


if __name__ == '__main__':
    unittest.main()
