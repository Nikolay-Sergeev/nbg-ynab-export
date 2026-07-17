import os
import stat
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet

from config import KEY_FILE, SETTINGS_FILE, get_logger

logger = get_logger(__name__)


def generate_key() -> bytes:
    """Generate a new encryption key."""
    return Fernet.generate_key()


def _validate_private_file_descriptor(fd: int, path: Path) -> None:
    file_stat = os.fstat(fd)
    if not stat.S_ISREG(file_stat.st_mode):
        raise OSError(f"Refusing to use non-regular private file: {path}")
    if hasattr(os, 'getuid') and file_stat.st_uid != os.getuid():
        raise PermissionError(f"Private file is not owned by the current user: {path}")


def _read_private_bytes(path: Path) -> bytes:
    if path.is_symlink():
        raise OSError(f"Refusing to read symlinked private file: {path}")
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        if path.is_symlink():
            raise OSError(f"Refusing to read symlinked private file: {path}") from exc
        raise

    try:
        _validate_private_file_descriptor(fd, path)
        if os.name == 'posix':
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'rb') as private_file:
            fd = -1
            return private_file.read()
    finally:
        if fd >= 0:
            os.close(fd)


def _atomic_write_private_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink():
        raise OSError(f"Refusing to replace symlinked private file: {path}")

    fd, temp_name = tempfile.mkstemp(prefix=f'.{path.name}.', dir=str(path.parent))
    try:
        if os.name == 'posix':
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'wb') as private_file:
            fd = -1
            private_file.write(data)
            private_file.flush()
            os.fsync(private_file.fileno())
        os.replace(temp_name, path)
    except Exception:
        if fd >= 0:
            os.close(fd)
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def _create_key_if_missing(key: bytes) -> bytes:
    key_path = Path(KEY_FILE)
    key_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    try:
        fd = os.open(key_path, flags, 0o600)
    except FileExistsError:
        return load_key()

    try:
        _validate_private_file_descriptor(fd, key_path)
        with os.fdopen(fd, 'wb') as key_file:
            fd = -1
            key_file.write(key)
            key_file.flush()
            os.fsync(key_file.fileno())
    finally:
        if fd >= 0:
            os.close(fd)
    return key


def save_key(key: bytes) -> None:
    """Save encryption key to file."""
    Fernet(key)  # Validate before replacing a working key.
    key_path = Path(KEY_FILE)
    _atomic_write_private_bytes(key_path, key)


def load_key() -> bytes:
    """Load encryption key from file."""
    key_path = Path(KEY_FILE)
    if not key_path.exists():
        raise FileNotFoundError(f"Encryption key not found: {KEY_FILE}")
    return _read_private_bytes(key_path)


def encrypt_token(token: str) -> bytes:
    """Encrypt a token using the stored key."""
    if not isinstance(token, str) or not token:
        raise ValueError("Token must be a non-empty string")
    try:
        key = load_key()
    except FileNotFoundError:
        logger.info("Generating new encryption key")
        key = _create_key_if_missing(generate_key())
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
        content = _read_private_bytes(token_path).decode('utf-8')
        for line in content.splitlines():
            if not line.startswith("TOKEN:") and line.strip():
                lines.append(line)
    except FileNotFoundError:
        pass
    except UnicodeDecodeError:
        # Legacy binary content; drop it when rewriting with structured lines
        lines = []

    lines.insert(0, f"TOKEN:{encrypted_token}")
    content = ("\n".join(lines) + "\n").encode('utf-8')
    _atomic_write_private_bytes(token_path, content)
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
        raw_content = _read_private_bytes(token_path)
        content = raw_content.decode('utf-8')
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
    encrypted_token = _read_private_bytes(token_path)
    return decrypt_token(encrypted_token)
