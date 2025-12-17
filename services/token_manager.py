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
    key_path = Path(KEY_FILE)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(key)
    os.chmod(key_path, 0o600)  # Secure permissions


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
    """Encrypt and save token to settings file.

    Preserves non-token metadata lines (e.g., last-used folder) when the file
    is text-based, and remains compatible with legacy binary-only storage.
    """
    encrypted_token = encrypt_token(token).decode()
    token_path = Path(SETTINGS_FILE)
    token_path.parent.mkdir(parents=True, exist_ok=True)

    # Preserve existing non-token lines if the file is text-readable
    lines = []
    try:
        with token_path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.startswith("TOKEN:") and line.strip():
                    lines.append(line.rstrip("\n"))
    except FileNotFoundError:
        pass
    except UnicodeDecodeError:
        # Legacy binary content; drop it when rewriting with structured lines
        lines = []

    lines.insert(0, f"TOKEN:{encrypted_token}")
    token_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(token_path, 0o600)  # Secure permissions
    logger.info("Token saved securely")


def load_token() -> str:
    """Load and decrypt token from settings file.

    Environment variable ``YNAB_TOKEN`` takes precedence if set.
    """
    env_token = os.getenv("YNAB_TOKEN")
    if env_token:
        return env_token

    token_path = Path(SETTINGS_FILE)
    if not token_path.exists():
        raise FileNotFoundError(f"Token file not found: {SETTINGS_FILE}")

    # First, try to read token from structured text (TOKEN:<cipher>)
    try:
        content = token_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.startswith("TOKEN:"):
                enc = line.split("TOKEN:", 1)[1].strip()
                if enc:
                    return decrypt_token(enc.encode())
        # If no prefixed line but content exists, try to decrypt the raw text
        stripped = content.strip()
        if stripped:
            try:
                return decrypt_token(stripped.encode())
            except Exception:
                pass
    except UnicodeDecodeError:
        # Fall back to binary decryption
        pass

    # Fallback to legacy binary format
    encrypted_token = token_path.read_bytes()
    return decrypt_token(encrypted_token)
