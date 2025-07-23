from cryptography.fernet import Fernet
from pathlib import Path
import os
from config import KEY_FILE, SETTINGS_FILE, get_logger

logger = get_logger(__name__)


def generate_key() -> bytes:
    """Generate a new encryption key."""
    return Fernet.generate_key()


def save_key(key: bytes) -> None:
    """Save encryption key to file."""
    Path(KEY_FILE).write_bytes(key)
    os.chmod(KEY_FILE, 0o600)  # Secure permissions


def load_key() -> bytes:
    """Load encryption key from file."""
    key_path = Path(KEY_FILE)
    if not key_path.exists():
        raise FileNotFoundError(f"Encryption key not found: {KEY_FILE}")
    return key_path.read_bytes()


def encrypt_token(token: str) -> bytes:
    """Encrypt a token using the stored key."""
    try:
        key = load_key()
    except FileNotFoundError:
        logger.info("Generating new encryption key")
        key = generate_key()
        save_key(key)
    f = Fernet(key)
    return f.encrypt(token.encode())


def decrypt_token(token_bytes: bytes) -> str:
    """Decrypt a token using the stored key."""
    key = load_key()
    f = Fernet(key)
    return f.decrypt(token_bytes).decode()


def save_token(token: str) -> None:
    """Encrypt and save token to settings file."""
    encrypted_token = encrypt_token(token)
    Path(SETTINGS_FILE).write_bytes(encrypted_token)
    os.chmod(SETTINGS_FILE, 0o600)  # Secure permissions
    logger.info("Token saved securely")


def load_token() -> str:
    """Load and decrypt token from settings file."""
    token_path = Path(SETTINGS_FILE)
    if not token_path.exists():
        raise FileNotFoundError(f"Token file not found: {SETTINGS_FILE}")

    encrypted_token = token_path.read_bytes()
    return decrypt_token(encrypted_token)
