import unittest

import pandas as pd

from converter.dispatcher import detect_processor


class TestDetectProcessor(unittest.TestCase):
    def setUp(self):
        self.revolut_df = pd.DataFrame({
            'Type': ['CARD_PAYMENT'],
            'Started Date': ['2025-07-01'],
            'Description': ['Coffee Shop'],
            'Amount': ['-4.50'],
            'Fee': ['0.00'],
            'State': ['COMPLETED'],
            'Currency': ['EUR'],
        })
        self.account_df = pd.DataFrame({
            'Valeur': ['15/07/2025'],
            'Ονοματεπώνυμο αντισυμβαλλόμενου': ['SUPERMARKET XYZ'],
            'Περιγραφή': ['MARKET PURCHASE'],
            'Ποσό συναλλαγής': ['45,67'],
            'Χρέωση / Πίστωση': ['Χρέωση'],
        })
        self.card_df = pd.DataFrame({
            'Ημερομηνία/Ώρα Συναλλαγής': ['21/2/2025 10:00 μμ'],
            'Περιγραφή Κίνησης': ['SHOP.EXAMPLE.COM'],
            'Ποσό': ['12,34'],
        })
        self.processors = {
            'revolut': lambda df: df.assign(source='revolut'),
            'account': lambda df: df.assign(source='account'),
            'card': lambda df: df.assign(source='card'),
        }

    def test_detects_revolut(self):
        processor, is_revolut, source = detect_processor(self.revolut_df, self.processors)
        self.assertIs(processor, self.processors['revolut'])
        self.assertTrue(is_revolut)
        self.assertEqual(source, 'revolut')

    def test_detects_account(self):
        processor, is_revolut, source = detect_processor(self.account_df, self.processors)
        self.assertIs(processor, self.processors['account'])
        self.assertFalse(is_revolut)
        self.assertEqual(source, 'account')

    def test_detects_card(self):
        processor, is_revolut, source = detect_processor(self.card_df, self.processors)
        self.assertIs(processor, self.processors['card'])
        self.assertFalse(is_revolut)
        self.assertEqual(source, 'card')

    def test_unrecognized_columns(self):
        df = pd.DataFrame({'Column1': [1], 'Column2': [2]})
        with self.assertRaises(ValueError):
            detect_processor(df, self.processors)
