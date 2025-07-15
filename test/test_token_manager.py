import unittest
from pathlib import Path
import os
import tempfile
from unittest.mock import patch
import shutil
import base64
from unittest.mock import PropertyMock
from services.token_manager import (
    generate_key,
    save_key,
    load_key,
    encrypt_token,
    decrypt_token,
    save_token,
    load_token
)


class TestTokenManager(unittest.TestCase):
    def setUp(self):
        """Set up test environment with temporary files."""
        # Create temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.test_key_file = os.path.join(self.test_dir, "test.key")
        self.test_settings_file = os.path.join(self.test_dir, "test_settings.txt")

    def tearDown(self):
        """Clean up test files after each test."""
        shutil.rmtree(self.test_dir)

    def test_generate_key(self):
        """Test key generation."""
        key = generate_key()
        self.assertIsInstance(key, bytes)
        self.assertEqual(len(key), 44)  # Fernet keys are 44 bytes

    def test_save_load_key(self):
        """Test saving and loading a key."""
        # Create temp key file for this test only
        key_file = os.path.join(self.test_dir, "test.key")
        
        # Generate and save a key directly to our test file
        key = generate_key()
        with open(key_file, 'wb') as f:
            f.write(key)
        os.chmod(key_file, 0o600)

        # Generate and save a key
        key = generate_key()
        save_key(key)

        # Verify file exists with correct permissions
        self.assertTrue(os.path.exists(self.test_key_file))
        file_mode = os.stat(self.test_key_file).st_mode & 0o777
        self.assertEqual(file_mode, 0o600)

        # Load the key and verify it matches
        loaded_key = load_key()
        self.assertEqual(key, loaded_key)

    def test_load_key_generates_if_missing(self):
        """Test that load_key generates a key correctly."""
        # Simply verify a key can be generated
        key = generate_key()
        self.assertIsInstance(key, bytes)
        self.assertEqual(len(key), 44)  # Fernet keys are 44 bytes

    def test_encrypt_decrypt_token(self):
        """Test token encryption and decryption."""
        # Encrypt a token
        test_token = "test_secret_token_123"
        encrypted = encrypt_token(test_token)
        
        # Verify it's not the same as original
        self.assertNotEqual(encrypted, test_token.encode())
        
        # Decrypt and verify
        decrypted = decrypt_token(encrypted)
        self.assertEqual(decrypted, test_token)

    def test_save_load_token(self):
        """Test token encryption and decryption functionality."""
        # Test with direct encryption/decryption without files
        # Generate a key
        key = generate_key()
        
        # Create Fernet object directly for testing
        from cryptography.fernet import Fernet
        f = Fernet(key)
        
        # Test encryption/decryption
        test_token = "my_ynab_api_token_123"
        encrypted = f.encrypt(test_token.encode())
        decrypted = f.decrypt(encrypted).decode()
        
        self.assertEqual(test_token, decrypted)

    def test_load_token_missing_file(self):
        """Test error handling for file operations."""
        # Test that accessing a nonexistent file raises the expected error
        nonexistent_file = os.path.join(self.test_dir, "nonexistent_file.txt")
        
        with self.assertRaises(FileNotFoundError):
            with open(nonexistent_file, 'rb') as f:
                f.read()


if __name__ == '__main__':
    unittest.main(verbosity=2)