import sys
import logging
from pathlib import Path
from PyQt5.QtCore import QSettings

__all__ = [
    'APP_NAME', 'ORGANIZATION',
    'DATE_FMT_ACCOUNT', 'DATE_FMT_YNAB',
    'SUPPORTED_EXT',
    'get_settings', 'SETTINGS_DIR', 'SETTINGS_FILE', 'KEY_FILE', 'ACTUAL_SETTINGS_FILE',
    'get_logger',
    'DUP_CHECK_DAYS', 'DUP_CHECK_COUNT',
]

APP_NAME = "nbg-ynab-export"
ORGANIZATION = "Me"

DATE_FMT_ACCOUNT = "%d/%m/%Y"
DATE_FMT_YNAB = "%Y-%m-%d"
SUPPORTED_EXT = {'.csv', '.xls', '.xlsx'}

# Duplicate checking configuration
DUP_CHECK_DAYS = 90
DUP_CHECK_COUNT = 500

# Directory and file paths for UI wizard settings and encryption key
SETTINGS_DIR = Path.home() / f".{APP_NAME}"
SETTINGS_FILE = str(SETTINGS_DIR / "settings.txt")
KEY_FILE = str(SETTINGS_DIR / "settings.key")
ACTUAL_SETTINGS_FILE = str(SETTINGS_DIR / "actual_settings.txt")


def ensure_app_dir() -> None:
    """Create the application directory if it doesn't exist."""
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)


def get_settings() -> QSettings:
    """Return a QSettings instance, creating directories on first use."""
    ensure_app_dir()
    return QSettings(QSettings.IniFormat, QSettings.UserScope,
                     ORGANIZATION, APP_NAME)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
        handler.setFormatter(logging.Formatter(fmt))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
