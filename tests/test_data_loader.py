"""
Simple tests for data loaders.
"""
import unittest
import pandas as pd
import tempfile
import shutil
from pathlib import Path

from app.data_loaders import ChaseCheckingLoader, ChaseCreditCardLoader, AppleCardLoader


class TestDataLoaders(unittest.TestCase):
    """Test data loader functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        
        # Create test CSV data
        self.create_test_files()
    
    def tearDown(self):
        """Clean up test data."""
        shutil.rmtree(self.test_dir)
    
    def create_test_files(self):
        """Create test CSV files."""
        # Chase checking test data
        checking_data = {
            'Details': ['DEBIT', 'CREDIT'],
            'Posting Date': ['06/30/2025', '06/29/2025'],
            'Description': ['ATM WITHDRAWAL', 'SALARY DEPOSIT'],
            'Amount': [-100.0, 5000.0],
            'Type': ['ATM', 'ACH_CREDIT'],
            'Balance': [4900.0, 5000.0],
            'Check or Slip #': ['', '']
        }
        checking_df = pd.DataFrame(checking_data)
        checking_folder = self.test_path / "chase_checking"
        checking_folder.mkdir()
        checking_df.to_csv(checking_folder / "test_checking.csv", index=False)
        
        # Chase credit card test data
        credit_data = {
            'Transaction Date': ['06/30/2025', '06/29/2025'],
            'Post Date': ['06/30/2025', '06/30/2025'],
            'Description': ['AMAZON PURCHASE', 'RESTAURANT'],
            'Category': ['Shopping', 'Food & Drink'],
            'Type': ['Sale', 'Sale'],
            'Amount': [-50.0, -30.0]
        }
        credit_df = pd.DataFrame(credit_data)
        credit_folder = self.test_path / "chase_credit"
        credit_folder.mkdir()
        credit_df.to_csv(credit_folder / "test_credit.csv", index=False)
        
        # Apple card test data
        apple_data = {
            'Transaction Date': ['06/30/2025', '06/29/2025'],
            'Clearing Date': ['06/30/2025', '06/30/2025'],
            'Description': ['APPLE STORE', 'STARBUCKS'],
            'Merchant': ['Apple Store', 'Starbucks'],
            'Category': ['Other', 'Restaurants'],
            'Type': ['Purchase', 'Purchase'],
            'Amount (USD)': [-200.0, -15.0],
            'Purchased By': ['Joseph Rule', 'Joseph Rule']
        }
        apple_df = pd.DataFrame(apple_data)
        apple_folder = self.test_path / "apple_joe"
        apple_folder.mkdir()
        apple_df.to_csv(apple_folder / "test_apple.csv", index=False)
    
    def test_chase_checking_loader(self):
        """Test Chase checking loader."""
        loader = ChaseCheckingLoader(self.test_path / "chase_checking")
        df = loader.load_data()
        
        self.assertEqual(len(df), 2)
        self.assertTrue('date' in df.columns)
        self.assertTrue('amount' in df.columns)
        self.assertTrue('source' in df.columns)
        self.assertEqual(df['source'].iloc[0], 'chase_checking')
        self.assertEqual(df['account_owner'].iloc[0], 'shared')
    
    def test_chase_credit_loader(self):
        """Test Chase credit card loader."""
        loader = ChaseCreditCardLoader(self.test_path / "chase_credit")
        df = loader.load_data()
        
        self.assertEqual(len(df), 2)
        self.assertTrue('category' in df.columns)
        self.assertEqual(df['source'].iloc[0], 'chase_credit_card')
        self.assertEqual(df['account_owner'].iloc[0], 'shared')
    
    def test_apple_card_loader(self):
        """Test Apple card loader."""
        loader = AppleCardLoader(self.test_path / "apple_joe", "Joe")
        df = loader.load_data()
        
        self.assertEqual(len(df), 2)
        self.assertTrue('merchant' in df.columns)
        self.assertEqual(df['source'].iloc[0], 'apple_card_joe')
        self.assertEqual(df['account_owner'].iloc[0], 'joe')
    
    def test_missing_folder(self):
        """Test behavior with missing folder."""
        with self.assertRaises(FileNotFoundError):
            loader = ChaseCheckingLoader(self.test_path / "nonexistent")
            loader.load_data()


if __name__ == '__main__':
    unittest.main()
    