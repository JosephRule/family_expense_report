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
        
        # Create test dataframe
        self.test_df = pd.DataFrame({
            'date': pd.to_datetime(['2025-06-30', '2025-06-29', '2025-06-28']),
            'description': ['Payment to Chase card', 'CLOCKWISE DIR DEP', 'AMAZON PURCHASE'],
            'amount': [3000.0, 5000.0, -50.0],
            'category': ['Payment', 'ACH_CREDIT', 'Shopping'],
            'type': ['Payment', 'ACH_CREDIT', 'Sale'],
            'source': ['apple_card_joe', 'chase_checking', 'chase_credit_card'],
            'merchant': ['Chase', 'Bank', 'Amazon']
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
        
        # Exclusions
        exclusions = {
            'exclusions': [
                {
                    'source': 'apple_card_joe',
                    'type': 'Payment',
                    'reason': 'Credit card payment'
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
                    'source': 'chase_checking',
                    'conditions': {
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
        """Test exclusion rules."""
        rules_engine = RulesEngine(str(self.config_dir))
        result_df = rules_engine.apply_exclusions(self.test_df)
        
        # Should exclude the payment transaction
        self.assertEqual(len(result_df), 2)
        self.assertNotIn('Payment to Chase card', result_df['description'].values)
    
    def test_custom_rules(self):
        """Test custom categorization rules."""
        rules_engine = RulesEngine(str(self.config_dir))
        result_df = rules_engine.apply_custom_rules(self.test_df)
        
        # Should have custom category and flags columns
        self.assertTrue('custom_category' in result_df.columns)
        self.assertTrue('flags' in result_df.columns)
        
        # Check that CLOCKWISE transaction got custom category
        clockwise_row = result_df[result_df['description'].str.contains('CLOCKWISE')]
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
        clockwise_row = result_df[result_df['description'].str.contains('CLOCKWISE')]
        self.assertEqual(clockwise_row['master_category'].iloc[0], 'Salary Income')
    
    def test_merchant_grouping(self):
        """Test merchant grouping."""
        rules_engine = RulesEngine(str(self.config_dir))
        result_df = rules_engine.apply_merchant_grouping(self.test_df)
        
        # Should have merchant_group column
        self.assertTrue('merchant_group' in result_df.columns)
        
        # Amazon should be grouped
        amazon_row = result_df[result_df['merchant'] == 'Amazon']
        self.assertEqual(amazon_row['merchant_group'].iloc[0], 'Amazon')


if __name__ == '__main__':
    unittest.main()
    