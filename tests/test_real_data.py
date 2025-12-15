"""Test cases based on real NBG bank statement data."""
import unittest
import pandas as pd
from datetime import datetime
from services.conversion_service import (
    process_account_operations,
    process_card_operations,
    validate_dataframe
)

class TestRealNBGData(unittest.TestCase):
    """Test cases using anonymized real NBG bank statement data."""
    
    def test_organization_payment(self):
        """Test processing of organization payment transaction."""
        test_data = pd.DataFrame({
            'Valeur': ['23/07/2025'],
            'Κατάστημα': ['700 Internet Banking'],
            'Κατηγορία συναλλαγής': ['68 ΜΕΤΑΦΟΡΑ ΣΕ ΛΟΓ/ΜΟ'],
            'Είδος εργασίας': ['12010 Πληρωμή Οργανισμού μέσω ΔΙΑΣ Credit Transfer'],
            'Ποσό συναλλαγής': ['-43,20'],
            'Χρέωση / Πίστωση': ['Χρέωση'],
            'Περιγραφή': ['ΠΛΗΡΩΜΗ ΟΡΓΑΝΩΣΗ ΚΟΙΝΟΧΡΗΣΤΑ'],
            'Ονοματεπώνυμο συμβαλλόμενου': ['CUSTOMER NAME'],
            'Ονοματεπώνυμο αντισυμβαλλόμενου': ['ORGANIZATION NAME']
        })
        
        result = process_account_operations(test_data)
        
        # Verify the transaction was processed correctly
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['Date'], '2025-07-23')
        self.assertEqual(result.iloc[0]['Payee'], 'ORGANIZATION NAME')
        self.assertEqual(result.iloc[0]['Memo'], 'ΠΛΗΡΩΜΗ ΟΡΓΑΝΩΣΗ ΚΟΙΝΟΧΡΗΣΤΑ')
        self.assertEqual(result.iloc[0]['Amount'], -43.20)

    def test_interest_tax(self):
        """Test processing of interest tax transaction."""
        test_data = pd.DataFrame({
            'Valeur': ['30/06/2025'],
            'Κατηγορία συναλλαγής': ['9 ΦΟΡΟΙ ΤΟΚΩΝ'],
            'Είδος εργασίας': ['70060 Φόρος Τόκων'],
            'Ποσό συναλλαγής': ['-0,13'],
            'Χρέωση / Πίστωση': ['Χρέωση'],
            'Περιγραφή': ['ΦΟΡΟΣ ΤΟΚΩΝ'],
            'Ονοματεπώνυμο αντισυμβαλλόμενου': ['NATIONAL BANK OF GREECE']
        })
        
        result = process_account_operations(test_data)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['Date'], '2025-06-30')
        self.assertEqual(result.iloc[0]['Payee'], 'NATIONAL BANK OF GREECE')
        self.assertEqual(result.iloc[0]['Memo'], 'ΦΟΡΟΣ ΤΟΚΩΝ')
        self.assertEqual(result.iloc[0]['Amount'], -0.13)

    def test_interest_credit(self):
        """Test processing of interest credit transaction."""
        test_data = pd.DataFrame({
            'Valeur': ['30/06/2025'],
            'Κατηγορία συναλλαγής': ['18 ΠΙΣΤΩΤΙΚΟΙ ΤΟΚΟΙ'],
            'Είδος εργασίας': ['70062 Πίστωση τόκων'],
            'Ποσό συναλλαγής': ['0,87'],
            'Χρέωση / Πίστωση': ['Πίστωση'],
            'Περιγραφή': ['ΠΙΣΤΩΤΙΚΟΙ ΤΟΚΟΙ'],
            'Ονοματεπώνυμο αντισυμβαλλόμενου': ['NATIONAL BANK OF GREECE']
        })
        
        result = process_account_operations(test_data)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['Date'], '2025-06-30')
        self.assertEqual(result.iloc[0]['Payee'], 'NATIONAL BANK OF GREECE')
        self.assertEqual(result.iloc[0]['Memo'], 'ΠΙΣΤΩΤΙΚΟΙ ΤΟΚΟΙ')
        self.assertEqual(result.iloc[0]['Amount'], 0.87)

    def test_account_maintenance_fee(self):
        """Test processing of account maintenance fee."""
        test_data = pd.DataFrame({
            'Valeur': ['07/07/2025'],
            'Κατάστημα': ['942 ΑΝΑΠΤΥΞΗΣ ΚΑΙ ΣΥΝΤΗΡΗΣΗΣ ΕΦΑΡΜΟΓΩΝ ΠΛΗΡΟΦΟΡΙΚΗΣ'],
            'Κατηγορία συναλλαγής': ['24 ΠΡΟΜΗΘΕΙΑ'],
            'Είδος εργασίας': ['70280 Προμήθεια τήρησης λογ/σμού ταμιευτηρίου'],
            'Ποσό συναλλαγής': ['-2,00'],
            'Χρέωση / Πίστωση': ['Χρέωση'],
            'Περιγραφή': ['ΜΗΝ.ΚΟΣΤ.ΠΑΡ.ΥΠΗΡ'],
            'Ονοματεπώνυμο αντισυμβαλλόμενου': ['NATIONAL BANK OF GREECE']
        })
        
        result = process_account_operations(test_data)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['Date'], '2025-07-07')
        self.assertEqual(result.iloc[0]['Payee'], 'NATIONAL BANK OF GREECE')
        self.assertEqual(result.iloc[0]['Memo'], 'ΜΗΝ.ΚΟΣΤ.ΠΑΡ.ΥΠΗΡ')
        self.assertEqual(result.iloc[0]['Amount'], -2.00)

    def test_card_purchase(self):
        """Test processing of card purchase transaction."""
        test_data = pd.DataFrame({
            'Ημερομηνία/Ώρα Συναλλαγής': ['23/07/2025 12:34'],
            'Περιγραφή Κίνησης': ['E-COMMERCE ΑΓΟΡΑ - MERCHANT NAME'],
            'Χ/Π': ['Χ'],
            'Ποσό': ['78,33']
        })
        
        result = process_card_operations(test_data)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['Date'], '2025-07-23')
        self.assertEqual(result.iloc[0]['Payee'], 'MERCHANT NAME')
        self.assertEqual(result.iloc[0]['Memo'], 'MERCHANT NAME')
        self.assertEqual(result.iloc[0]['Amount'], -78.33)

if __name__ == '__main__':
    unittest.main()
