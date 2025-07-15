# Test Coverage Analysis

## Current Test Coverage

### Well Covered Areas
1. **Core Utility Functions**
   - Amount conversion (`convert_amount`)
   - Date extraction from filenames
   - Output filename generation
   - DataFrame validation
   - Transaction exclusion logic

2. **Converter Modules**
   - NBG Account statement processing
   - NBG Card statement processing
   - Revolut export processing
   - Error handling for empty/invalid files
   - Currency validation

3. **UI Components**
   - Basic testing of StepLabel
   - Style loading

### Missing or Limited Coverage

1. **YNAB API Client**
   - No tests for `YnabClient` class
   - No coverage of token handling, API error responses, or rate limiting

2. **UI Integration**
   - Limited testing of UI wizard flow
   - Missing tests for wizard pages
   - No testing of QThread workers in UI controller

3. **Error Handling**
   - Limited coverage of error handling scenarios
   - Network failures not tested
   - API response error handling not tested

4. **Config Module**
   - No tests for configuration loading/saving
   - Token encryption/decryption not tested

5. **Integration Tests**
   - No end-to-end integration tests
   - Missing tests for CLI to file output workflow

## Recommended Additional Tests

1. **YNAB API Client Tests**
```python
class TestYnabClient(unittest.TestCase):
    def setUp(self):
        self.client = YnabClient("test_token")
        self.mock_response = MagicMock()
        
    @patch('requests.get')
    def test_get_budgets(self, mock_get):
        mock_get.return_value.json.return_value = {"data": {"budgets": [{"id": "123", "name": "Test"}]}}
        mock_get.return_value.status_code = 200
        
        budgets = self.client.get_budgets()
        
        self.assertEqual(len(budgets), 1)
        self.assertEqual(budgets[0]["name"], "Test")
        mock_get.assert_called_once()
        
    @patch('requests.get')
    def test_get_accounts(self, mock_get):
        mock_get.return_value.json.return_value = {"data": {"accounts": [{"id": "456", "name": "Checking"}]}}
        mock_get.return_value.status_code = 200
        
        accounts = self.client.get_accounts("123")
        
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0]["name"], "Checking")
        mock_get.assert_called_once()
        
    @patch('requests.post')
    def test_upload_transactions(self, mock_post):
        mock_post.return_value.json.return_value = {"data": {"transaction_ids": ["t1"]}}
        mock_post.return_value.status_code = 200
        
        transactions = [{"account_id": "456", "date": "2025-01-01", "amount": 1000, "payee_name": "Test"}]
        result = self.client.upload_transactions("123", transactions)
        
        self.assertIn("transaction_ids", result["data"])
        mock_post.assert_called_once()
        
    @patch('requests.get')
    def test_api_error_handling(self, mock_get):
        mock_get.return_value.status_code = 401
        mock_get.return_value.raise_for_status.side_effect = requests.exceptions.HTTPError("Unauthorized")
        
        with self.assertRaises(requests.exceptions.HTTPError):
            self.client.get_budgets()
```

2. **Config and Token Handling Tests**
```python
class TestConfig(unittest.TestCase):
    def setUp(self):
        self.test_config_path = Path("test_config.txt")
        
    def tearDown(self):
        if self.test_config_path.exists():
            self.test_config_path.unlink()
            
    @patch('config.get_config_path')
    def test_save_and_load_token(self, mock_get_path):
        mock_get_path.return_value = self.test_config_path
        
        token = "test_token_123"
        save_token(token)
        
        loaded_token = load_token()
        self.assertEqual(loaded_token, token)
        
    @patch('config.get_config_path')
    def test_encrypt_decrypt_token(self, mock_get_path):
        mock_get_path.return_value = self.test_config_path
        
        token = "secret_api_key"
        encrypted = encrypt_token(token)
        decrypted = decrypt_token(encrypted)
        
        self.assertNotEqual(token, encrypted)
        self.assertEqual(token, decrypted)
```

3. **UI Integration Tests**
```python
class TestWizardIntegration(unittest.TestCase):
    @patch('PyQt5.QtWidgets.QFileDialog.getOpenFileName')
    def test_file_import_flow(self, mock_dialog):
        mock_dialog.return_value = ("test_file.xlsx", "Excel Files (*.xlsx)")
        
        # Create wizard and test the import file page
        wizard = RobustWizard()
        import_page = ImportFilePage(wizard)
        
        # Simulate button click
        import_page.browse_button.click()
        
        self.assertEqual(import_page.file_path, "test_file.xlsx")
        self.assertTrue(import_page.isComplete())
```

4. **CLI Integration Tests**
```python
class TestCLIIntegration(unittest.TestCase):
    def setUp(self):
        self.test_output_dir = Path("test_output")
        self.test_output_dir.mkdir(exist_ok=True)
        
    def tearDown(self):
        for file in self.test_output_dir.glob("*"):
            file.unlink()
        self.test_output_dir.rmdir()
        
    def test_end_to_end_conversion(self):
        # Create a sample input file
        test_input = self.test_output_dir / "test_input.csv"
        with open(test_input, "w") as f:
            f.write("Type,Started Date,Description,Amount,Fee,State,Currency\n")
            f.write("CARD_PAYMENT,2024-02-15,Test,10.00,0.00,COMPLETED,EUR\n")
            
        # Run the conversion command
        import main
        with patch.object(sys, 'argv', ['main.py', str(test_input)]):
            main.main()
            
        # Check that output file was created with expected name pattern
        output_files = list(self.test_output_dir.glob("*_ynab.csv"))
        self.assertEqual(len(output_files), 1)
        
        # Verify content
        output_df = pd.read_csv(output_files[0])
        self.assertEqual(len(output_df), 1)
        self.assertEqual(output_df.iloc[0]["Amount"], 10.0)
```

5. **Error Handling Tests**
```python
class TestErrorHandling(unittest.TestCase):
    def test_network_failure(self):
        client = YnabClient("test_token")
        
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Network failure")
            
            with self.assertRaises(requests.exceptions.ConnectionError):
                client.get_budgets()
                
    def test_malformed_input_file(self):
        # Create malformed file
        with tempfile.NamedTemporaryFile(suffix='.csv') as tmp:
            tmp.write(b"Invalid,Headers\n1,2,3\n")  # Wrong number of columns
            tmp.flush()
            
            with self.assertRaises(ValueError):
                process_revolut_operations(read_input(tmp.name))
```

6. **Memory and Performance Tests**
```python
class TestPerformance(unittest.TestCase):
    def test_large_file_handling(self):
        # Generate large DataFrame
        large_df = pd.DataFrame({
            'Started Date': ['2024-02-15'] * 10000,
            'Description': ['Test'] * 10000,
            'Type': ['CARD_PAYMENT'] * 10000,
            'Amount': ['10.00'] * 10000,
            'Fee': ['0.00'] * 10000,
            'State': ['COMPLETED'] * 10000,
            'Currency': ['EUR'] * 10000
        })
        
        # Measure time
        start_time = time.time()
        result = process_revolut_operations(large_df)
        duration = time.time() - start_time
        
        # Check result and performance
        self.assertEqual(len(result), 10000)
        self.assertLess(duration, 2.0)  # Should process within 2 seconds
```