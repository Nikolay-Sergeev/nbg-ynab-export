import os

HOME_DIR = os.path.expanduser("~")
SETTINGS_DIR = os.path.join(HOME_DIR, ".nbg-ynab-export")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "nbg_ynab_settings.txt")
KEY_FILE = os.path.join(SETTINGS_DIR, "nbg_ynab_settings.key")
