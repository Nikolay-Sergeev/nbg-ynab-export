import unittest
import os
import tempfile
import shutil
import services.token_manager
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
        self.test_settings_file = os.path.join(
            self.test_dir, "test_settings.txt"
        )

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
        # Mock the key file path
        original_key_file = services.token_manager.KEY_FILE
        test_key_path = os.path.join(self.test_dir, "test.key")
        services.token_manager.KEY_FILE = test_key_path

        try:
            # Generate and save a key
            key = generate_key()
            save_key(key)

            # Verify file exists with correct permissions
            self.assertTrue(os.path.exists(test_key_path))
            file_mode = os.stat(test_key_path).st_mode & 0o777
            self.assertEqual(file_mode, 0o600)

            # Load the key and verify it matches
            loaded_key = load_key()
            self.assertEqual(key, loaded_key)
        finally:
            # Restore the original KEY_FILE path
            services.token_manager.KEY_FILE = original_key_file

    def test_load_key_missing_file(self):
        """load_key should raise FileNotFoundError if key file is missing."""
        # Mock the key file path
        original_key_file = services.token_manager.KEY_FILE
        test_key_path = os.path.join(self.test_dir, "missing.key")
        # Set mock path
        services.token_manager.KEY_FILE = test_key_path

        try:
            # Ensure the file does not exist
            if os.path.exists(test_key_path):
                os.remove(test_key_path)

            with self.assertRaises(FileNotFoundError):
                load_key()
        finally:
            # Restore the original KEY_FILE path
            services.token_manager.KEY_FILE = original_key_file

    def test_encrypt_decrypt_token(self):
        """Test token encryption and decryption."""
        original_key_file = services.token_manager.KEY_FILE
        test_key_path = os.path.join(self.test_dir, "encrypt_test.key")
        services.token_manager.KEY_FILE = test_key_path

        try:
            # Encrypt a token
            test_token = "test_secret_token"
            encrypted = encrypt_token(test_token)

            # Verify it's not the same as original
            self.assertNotEqual(encrypted, test_token.encode())

            # Decrypt and verify
            decrypted = decrypt_token(encrypted)
            self.assertEqual(decrypted, test_token)
        finally:
            services.token_manager.KEY_FILE = original_key_file

    def test_save_load_token(self):
        """Test token encryption and decryption functionality."""
        # Mock paths
        original_key_file = services.token_manager.KEY_FILE
        original_settings_file = services.token_manager.SETTINGS_FILE
        # Create test paths
        test_key_path = os.path.join(self.test_dir, "token_test.key")
        test_settings_path = os.path.join(self.test_dir, "settings.txt")
        # Set the mocked paths
        services.token_manager.KEY_FILE = test_key_path
        services.token_manager.SETTINGS_FILE = test_settings_path

        try:
            # Generate a test token
            test_token = "my_ynab_api_token_123"

            # Save the token using our system
            save_token(test_token)

            # Verify file exists with correct permissions
            self.assertTrue(os.path.exists(test_settings_path))
            file_mode = os.stat(test_settings_path).st_mode & 0o777
            self.assertEqual(file_mode, 0o600)

            # Load the token back and verify it matches
            loaded_token = load_token()
            self.assertEqual(test_token, loaded_token)
        finally:
            # Restore the original paths
            services.token_manager.KEY_FILE = original_key_file
            services.token_manager.SETTINGS_FILE = original_settings_file

    def test_load_token_missing_file(self):
        """Test error handling for file operations."""
        # Mock the settings file path
        original_settings_file = services.token_manager.SETTINGS_FILE
        nonexistent_file = os.path.join(
            self.test_dir, "nonexistent_settings.txt"
        )
        services.token_manager.SETTINGS_FILE = nonexistent_file

        try:
            # Ensure the file does not exist
            if os.path.exists(nonexistent_file):
                os.remove(nonexistent_file)

            # Attempt to load token from nonexistent file
            with self.assertRaises(FileNotFoundError):
                load_token()
        finally:
            # Restore the original SETTINGS_FILE path
            services.token_manager.SETTINGS_FILE = original_settings_file


if __name__ == '__main__':
    unittest.main(verbosity=2)
