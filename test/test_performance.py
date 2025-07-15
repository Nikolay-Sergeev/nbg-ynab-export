import unittest
import tempfile
import time
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Import modules to test
from converter.revolut import process_revolut
from converter.account import process_account
from converter.card import process_card
from converter.utils import convert_amount, exclude_existing


class TestPerformance(unittest.TestCase):
    def setUp(self):
        """Set up large test datasets."""
        # Generate a large Revolut dataset (10,000 rows)
        self.large_revolut_df = self._generate_revolut_data(10000)
        
        # Generate a large NBG account dataset
        self.large_account_df = self._generate_account_data(5000)
        
        # Generate a large NBG card dataset
        self.large_card_df = self._generate_card_data(5000)
        
        # Generate large datasets for exclusion testing
        self.large_new_df = self._generate_ynab_data(5000)
        self.large_prev_df = self._generate_ynab_data(2000)
    
    def _generate_revolut_data(self, num_rows):
        """Generate a large Revolut test dataset."""
        # Create random dates within the last 180 days
        today = datetime.now()
        dates = [
            (today - timedelta(days=np.random.randint(0, 180)))
            .strftime('%Y-%m-%d %H:%M:%S')
            for _ in range(num_rows)
        ]
        
        # Create random transaction types
        types = np.random.choice(
            ['CARD_PAYMENT', 'TRANSFER', 'EXCHANGE'], 
            size=num_rows, 
            p=[0.7, 0.2, 0.1]
        )
        
        # Create random descriptions
        merchants = [
            'Coffee Shop', 'Grocery Store', 'Restaurant', 'Online Store', 
            'Gas Station', 'Pharmacy', 'Department Store', 'Electronics'
        ]
        descriptions = np.random.choice(merchants, size=num_rows)
        
        # Create random amounts (negative for payments, positive for transfers)
        amounts = []
        fees = []
        for t in types:
            if t == 'CARD_PAYMENT':
                amount = -np.random.uniform(1, 200)
                fee = -np.random.uniform(0, 2) if np.random.random() < 0.3 else 0
            else:
                amount = np.random.uniform(10, 1000) if t == 'TRANSFER' else -np.random.uniform(10, 500)
                fee = 0
            amounts.append(str(round(amount, 2)))
            fees.append(str(round(fee, 2)))
        
        # Create the DataFrame
        return pd.DataFrame({
            'Type': types,
            'Started Date': dates,
            'Description': descriptions,
            'Amount': amounts,
            'Fee': fees,
            'State': ['COMPLETED'] * num_rows,
            'Currency': ['EUR'] * num_rows
        })
    
    def _generate_account_data(self, num_rows):
        """Generate a large NBG account test dataset."""
        # Create random dates
        dates = [
            (datetime.now() - timedelta(days=np.random.randint(0, 180)))
            .strftime('%d/%m/%Y')
            for _ in range(num_rows)
        ]
        
        # Create random payees
        payees = [
            f"Merchant {i}" for i in range(100)
        ]
        payee_idx = np.random.choice(len(payees), size=num_rows)
        merchant_names = [payees[i] for i in payee_idx]
        
        # Create random amounts
        debit_credit = np.random.choice(['Χρέωση', 'Πίστωση'], size=num_rows, p=[0.7, 0.3])
        amounts = []
        for dc in debit_credit:
            if dc == 'Χρέωση':
                amount = -np.random.uniform(1, 200)
            else:
                amount = np.random.uniform(100, 2000)
            # Format with European decimal separator
            amounts.append(str(round(amount, 2)).replace('.', ','))
        
        # Create the DataFrame
        return pd.DataFrame({
            'Valeur': dates,
            'Ονοματεπώνυμο αντισυμβαλλόμενου': merchant_names,
            'Περιγραφή': [f"Transaction {i}" for i in range(num_rows)],
            'Ποσό συναλλαγής': amounts,
            'Χρέωση / Πίστωση': debit_credit
        })
    
    def _generate_card_data(self, num_rows):
        """Generate a large NBG card test dataset."""
        # Create random dates
        dates = [
            (datetime.now() - timedelta(days=np.random.randint(0, 180)))
            .strftime('%d/%m/%Y %I:%M %p')
            for _ in range(num_rows)
        ]
        
        # Create descriptions with some e-commerce prefixes
        descriptions = []
        for _ in range(num_rows):
            if np.random.random() < 0.3:
                descriptions.append(f"E-COMMERCE ΑΓΟΡΑ - Merchant {np.random.randint(1, 1000)}")
            elif np.random.random() < 0.2:
                descriptions.append(f"3D SECURE E-COMMERCE ΑΓΟΡΑ - Merchant {np.random.randint(1, 1000)}")
            else:
                descriptions.append(f"Regular Merchant {np.random.randint(1, 1000)}")
        
        # Create random amounts
        debit_credit = np.random.choice(['Χ', 'Π'], size=num_rows, p=[0.8, 0.2])
        amounts = []
        for dc in debit_credit:
            if dc == 'Χ':
                amount = -np.random.uniform(1, 300)
            else:
                amount = np.random.uniform(50, 500)
            # Format with European decimal separator
            amounts.append(str(round(amount, 2)).replace('.', ','))
        
        # Create the DataFrame
        return pd.DataFrame({
            'Ημερομηνία/Ώρα Συναλλαγής': dates,
            'Περιγραφή Κίνησης': descriptions,
            'Ποσό': amounts,
            'Χ/Π': debit_credit
        })
    
    def _generate_ynab_data(self, num_rows):
        """Generate a large YNAB export test dataset."""
        # Create random dates within the last 90 days
        today = datetime.now()
        dates = [
            (today - timedelta(days=np.random.randint(0, 90)))
            .strftime('%Y-%m-%d')
            for _ in range(num_rows)
        ]
        
        # Create random payees
        payees = [f"Merchant {i}" for i in range(500)]
        payee_idx = np.random.choice(len(payees), size=num_rows)
        merchant_names = [payees[i] for i in payee_idx]
        
        # Create random amounts
        amounts = [
            round(np.random.uniform(-200, 200), 2)
            for _ in range(num_rows)
        ]
        
        # Create random memos
        memos = [f"Memo {i}" for i in range(num_rows)]
        
        # Create the DataFrame
        return pd.DataFrame({
            'Date': dates,
            'Payee': merchant_names,
            'Memo': memos,
            'Amount': amounts
        })
    
    def test_revolut_processing_performance(self):
        """Test performance of Revolut processing with large dataset."""
        start_time = time.time()
        result_df = process_revolut(self.large_revolut_df)
        duration = time.time() - start_time
        
        # Should have the same number of rows as input (all COMPLETED)
        self.assertEqual(len(result_df), len(self.large_revolut_df))
        
        # Performance assertion - should process quickly
        self.assertLess(duration, 2.0, f"Revolut processing took too long: {duration:.2f}s")
        print(f"Revolut processing of {len(self.large_revolut_df)} rows took {duration:.2f}s")
    
    def test_account_processing_performance(self):
        """Test performance of NBG account processing with large dataset."""
        start_time = time.time()
        result_df = process_account(self.large_account_df)
        duration = time.time() - start_time
        
        # Should have the same number of rows as input
        self.assertEqual(len(result_df), len(self.large_account_df))
        
        # Performance assertion - should process quickly
        self.assertLess(duration, 2.0, f"Account processing took too long: {duration:.2f}s")
        print(f"Account processing of {len(self.large_account_df)} rows took {duration:.2f}s")
    
    def test_card_processing_performance(self):
        """Test performance of NBG card processing with large dataset."""
        start_time = time.time()
        result_df = process_card(self.large_card_df)
        duration = time.time() - start_time
        
        # Should have the same number of rows as input
        self.assertEqual(len(result_df), len(self.large_card_df))
        
        # Performance assertion - should process quickly
        self.assertLess(duration, 2.0, f"Card processing took too long: {duration:.2f}s")
        print(f"Card processing of {len(self.large_card_df)} rows took {duration:.2f}s")
    
    def test_exclusion_performance(self):
        """Test performance of transaction exclusion with large datasets."""
        start_time = time.time()
        result_df = exclude_existing(self.large_new_df, self.large_prev_df)
        duration = time.time() - start_time
        
        # Should have fewer rows than input
        self.assertLess(len(result_df), len(self.large_new_df))
        
        # Performance assertion - should process quickly
        self.assertLess(duration, 2.0, f"Transaction exclusion took too long: {duration:.2f}s")
        print(f"Exclusion of {len(self.large_prev_df)} transactions from {len(self.large_new_df)} took {duration:.2f}s")
    
    def test_amount_conversion_performance(self):
        """Test performance of amount conversion with large dataset."""
        # Create large list of amount strings with European format
        amount_strings = [f"{np.random.uniform(1, 1000):.2f}".replace('.', ',') for _ in range(50000)]
        
        start_time = time.time()
        # Convert all amounts
        for amount in amount_strings:
            convert_amount(amount)
        duration = time.time() - start_time
        
        # Performance assertion - should process quickly
        self.assertLess(duration, 1.0, f"Amount conversion took too long: {duration:.2f}s")
        print(f"Conversion of {len(amount_strings)} amounts took {duration:.2f}s")


if __name__ == '__main__':
    unittest.main(verbosity=2)