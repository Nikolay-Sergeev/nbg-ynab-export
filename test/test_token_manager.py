import unittest
from pathlib import Path
import os
import tempfile
from unittest.mock import patch
import shutil
import base64
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

    @patch('services.token_manager.KEY_FILE')
    def test_save_load_key(self, mock_key_file):
        """Test saving and loading a key."""
        mock_key_file.__str__.return_value = self.test_key_file

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

    @patch('services.token_manager.KEY_FILE')
    def test_load_key_generates_if_missing(self, mock_key_file):
        """Test that load_key generates a new key if it doesn't exist."""
        mock_key_file.__str__.return_value = self.test_key_file

        # Ensure file doesn't exist
        if os.path.exists(self.test_key_file):
            os.unlink(self.test_key_file)

        # Load key should generate a new one
        key = load_key()
        
        # Verify file was created
        self.assertTrue(os.path.exists(self.test_key_file))
        self.assertIsInstance(key, bytes)

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

    @patch('services.token_manager.SETTINGS_FILE')
    @patch('services.token_manager.KEY_FILE')
    def test_save_load_token(self, mock_key_file, mock_settings_file):
        """Test saving and loading a token to a file."""
        mock_key_file.__str__.return_value = self.test_key_file
        mock_settings_file.__str__.return_value = self.test_settings_file

        # Generate a key first
        key = generate_key()
        save_key(key)
        
        # Save a token
        test_token = "my_ynab_api_token_123"
        save_token(test_token)
        
        # Verify file exists with correct permissions
        self.assertTrue(os.path.exists(self.test_settings_file))
        file_mode = os.stat(self.test_settings_file).st_mode & 0o777
        self.assertEqual(file_mode, 0o600)
        
        # Load the token and verify it matches
        loaded_token = load_token()
        self.assertEqual(test_token, loaded_token)

    @patch('services.token_manager.SETTINGS_FILE')
    def test_load_token_missing_file(self, mock_settings_file):
        """Test error handling when token file is missing."""
        mock_settings_file.__str__.return_value = os.path.join(
            self.test_dir, "nonexistent_file.txt"
        )
        
        with self.assertRaises(FileNotFoundError):
            load_token()


if __name__ == '__main__':
    unittest.main(verbosity=2)