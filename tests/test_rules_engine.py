"""
Simple tests for rules engine.
"""
import unittest
import pandas as pd
import tempfile
import shutil
import yaml
from pathlib import Path

from app.rules_engine import RulesEngine


class TestRulesEngine(unittest.TestCase):
    """Test rules engine functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.test_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.test_dir) / "config"
        self.config_dir.mkdir()
        
        # Create test configuration files
        self.create_test_configs()
        
        # Create test dataframe with comprehensive exclusion test cases
        self.test_df = pd.DataFrame({
            'date': pd.to_datetime(['2025-06-30', '2025-06-29', '2025-06-28', '2025-06-27', '2025-06-26', '2025-06-25']),
            'merchant': [
                'Payment Thank You-Mobile',  # Chase credit card payment
                'Payment to Chase card ending in 4754 06/30',  # Chase checking payment
                'APPLECARD GSBANK PAYMENT 06/29',  # Apple Card payment from checking
                'C98698 CLOCKWISE DIR DEP',  # Regular income - should NOT be excluded
                'AMAZON MKTPL*N37EE9E02',  # Regular purchase - should NOT be excluded
                'Apple Store Payment'  # Apple Card payment
            ],
            'amount': [3958.49, -3958.49, -1262.22, 5000.0, -50.0, -200.0],
            'category': [pd.NA, pd.NA, pd.NA, pd.NA, 'Shopping', 'Other'],
            'type': ['Payment', 'LOAN_PMT', 'LOAN_PMT', 'ACH_CREDIT', 'Sale', 'Payment'],
            'source': ['chase_credit_card', 'chase_checking', 'chase_checking', 'chase_checking', 'chase_credit_card', 'apple_card_joe'],
            'account_owner': ['shared', 'shared', 'shared', 'shared', 'shared', 'joe'],
            'source_file': ['test.csv'] * 6
        })
    
    def tearDown(self):
        """Clean up test data."""
        shutil.rmtree(self.test_dir)
    
    def create_test_configs(self):
        """Create test configuration files."""
        # Category mapping
        category_mapping = {
            'master_categories': {
                'Payment': 'Payments',
                'ACH_CREDIT': 'Income',
                'Shopping': 'Shopping'
            },
            'default_category': 'Uncategorized'
        }
        with open(self.config_dir / "category_mapping.yaml", 'w') as f:
            yaml.dump(category_mapping, f)
        
        # Exclusions - comprehensive test cases
        exclusions = {
            'exclusions': [
                # Card payments (to avoid double counting transfers between accounts)
                {
                    'source': 'apple_card_joe',
                    'type': 'Payment',
                    'reason': 'Credit card payment - avoid double counting'
                },
                {
                    'source': 'chase_credit_card',
                    'type': 'Payment',
                    'reason': 'Credit card payment - avoid double counting'
                },
                # Checking account payments to cards (to avoid double counting)
                {
                    'source': 'chase_checking',
                    'description_contains': 'Payment to Chase card ending in 4754',
                    'reason': 'Payment to Chase credit card - avoid double counting'
                },
                {
                    'source': 'chase_checking',
                    'description_contains': 'APPLECARD GSBANK PAYMENT',
                    'reason': 'Payment to Apple Card - avoid double counting'
                }
            ]
        }
        with open(self.config_dir / "exclusions.yaml", 'w') as f:
            yaml.dump(exclusions, f)
        
        # Custom rules
        custom_rules = {
            'custom_rules': [
                {
                    'name': 'Salary Income',
                    'conditions': {
                        'source': 'chase_checking',
                        'type': 'ACH_CREDIT',
                        'description_contains': 'CLOCKWISE'
                    },
                    'action': {
                        'category': 'Salary Income',
                        'flag': 'primary_income'
                    }
                }
            ],
            'merchant_groups': {
                'Amazon': {
                    'patterns': ['AMAZON'],
                    'master_name': 'Amazon'
                }
            }
        }
        with open(self.config_dir / "rules.yaml", 'w') as f:
            yaml.dump(custom_rules, f)
    
    def test_exclusions(self):
        """Test exclusion rules comprehensively."""
        rules_engine = RulesEngine(str(self.config_dir))
        
        # Verify initial data
        self.assertEqual(len(self.test_df), 6)
        
        # Apply exclusions
        result_df = rules_engine.apply_exclusions(self.test_df)
        
        # Should exclude 4 transactions:
        # 1. Chase credit card Payment (Payment Thank You-Mobile)
        # 2. Apple Card Payment (Apple Store Payment)  
        # 3. Chase checking payment to Chase card (Payment to Chase card ending in 4754 06/30)
        # 4. Chase checking payment to Apple Card (APPLECARD GSBANK PAYMENT 06/29)
        self.assertEqual(len(result_df), 2, f"Expected 2 transactions after exclusions, got {len(result_df)}")
        
        # Verify only the non-payment transactions remain
        remaining_merchants = result_df['merchant'].tolist()
        self.assertIn('C98698 CLOCKWISE DIR DEP', remaining_merchants)  # Income should remain
        self.assertIn('AMAZON MKTPL*N37EE9E02', remaining_merchants)  # Purchase should remain
        
        # Verify excluded transactions are gone
        self.assertNotIn('Payment Thank You-Mobile', remaining_merchants)
        self.assertNotIn('Payment to Chase card ending in 4754 06/30', remaining_merchants)
        self.assertNotIn('APPLECARD GSBANK PAYMENT 06/29', remaining_merchants)
        self.assertNotIn('Apple Store Payment', remaining_merchants)
        
    def test_card_payment_exclusions(self):
        """Test that card payments are excluded based on type."""
        rules_engine = RulesEngine(str(self.config_dir))
        
        # Filter to just payment type transactions
        payment_transactions = self.test_df[self.test_df['type'] == 'Payment']
        self.assertEqual(len(payment_transactions), 2)  # Chase credit and Apple Card payments
        
        # Apply exclusions
        result_df = rules_engine.apply_exclusions(self.test_df)
        
        # No Payment type transactions should remain
        remaining_payments = result_df[result_df['type'] == 'Payment']
        self.assertEqual(len(remaining_payments), 0, "All Payment type transactions should be excluded")
        
    def test_checking_description_exclusions(self):
        """Test that checking account transfers are excluded based on description."""
        rules_engine = RulesEngine(str(self.config_dir))
        
        # Filter to checking transactions with payment descriptions
        chase_checking = self.test_df[self.test_df['source'] == 'chase_checking']
        payment_descriptions = chase_checking[
            chase_checking['merchant'].str.contains('Payment to Chase card|APPLECARD GSBANK PAYMENT', case=False, na=False)
        ]
        self.assertEqual(len(payment_descriptions), 2)  # Two payment descriptions
        
        # Apply exclusions
        result_df = rules_engine.apply_exclusions(self.test_df)
        
        # These specific payment descriptions should be excluded
        remaining_checking = result_df[result_df['source'] == 'chase_checking']
        remaining_descriptions = remaining_checking['merchant'].tolist()
        
        self.assertNotIn('Payment to Chase card ending in 4754 06/30', remaining_descriptions)
        self.assertNotIn('APPLECARD GSBANK PAYMENT 06/29', remaining_descriptions)
        
        # But regular checking transactions should remain
        self.assertIn('C98698 CLOCKWISE DIR DEP', remaining_descriptions)
    
    def test_custom_rules(self):
        """Test custom categorization rules."""
        rules_engine = RulesEngine(str(self.config_dir))
        result_df = rules_engine.apply_custom_rules(self.test_df)
        
        # Should have custom category and flags columns
        self.assertTrue('custom_category' in result_df.columns)
        self.assertTrue('flags' in result_df.columns)
        
        # Check that CLOCKWISE transaction got custom category
        clockwise_row = result_df[result_df['merchant'].str.contains('CLOCKWISE')]
        self.assertEqual(clockwise_row['custom_category'].iloc[0], 'Salary Income')
        self.assertEqual(clockwise_row['flags'].iloc[0], 'primary_income')
    
    def test_category_mapping(self):
        """Test category mapping."""
        rules_engine = RulesEngine(str(self.config_dir))
        
        # First apply custom rules to get custom_category column
        df_with_custom = rules_engine.apply_custom_rules(self.test_df)
        result_df = rules_engine.apply_category_mapping(df_with_custom)
        
        # Should have master_category column
        self.assertTrue('master_category' in result_df.columns)
        
        # Check mappings
        shopping_row = result_df[result_df['category'] == 'Shopping']
        self.assertEqual(shopping_row['master_category'].iloc[0], 'Shopping')
        
        # Custom category should override original category
        clockwise_row = result_df[result_df['merchant'].str.contains('CLOCKWISE')]
        self.assertEqual(clockwise_row['master_category'].iloc[0], 'Salary Income')
    
    def test_merchant_grouping(self):
        """Test merchant grouping."""
        rules_engine = RulesEngine(str(self.config_dir))
        result_df = rules_engine.apply_merchant_grouping(self.test_df)
        
        # Should have merchant_group column
        self.assertTrue('merchant_group' in result_df.columns)
        
        # Amazon should be grouped
        amazon_row = result_df[result_df['merchant'].str.contains('AMAZON', case=False, na=False)]
        if len(amazon_row) > 0:
            self.assertEqual(amazon_row['merchant_group'].iloc[0], 'Amazon')


if __name__ == '__main__':
    unittest.main()
    