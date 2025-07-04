"""
Rules engine for processing expense data.
"""
import pandas as pd
import yaml
from pathlib import Path
from typing import Dict, List, Any
import re


class RulesEngine:
    """Rules engine for categorization and exclusions."""

    def __init__(self, config_folder: str):
        self.config_folder = Path(config_folder)
        self.exclusions = self._load_config("exclusions.yaml")
        self.custom_rules = self._load_config("rules.yaml")
        self.category_mapping = self._load_config("category_mapping.yaml")

    def _load_config(self, filename: str) -> Dict[str, Any]:
        """Load configuration file."""
        config_path = self.config_folder / filename
        if not config_path.exists():
            print(f"Warning: {config_path} not found, using defaults")
            return {}

        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def apply_exclusions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply exclusion rules to filter out unwanted transactions."""
        result_df = df.copy()

        exclusions = self.exclusions.get('exclusions', [])

        for exclusion in exclusions:
            # Build filter conditions on current dataframe
            mask = pd.Series([True] * len(result_df), index=result_df.index)

            if 'source' in exclusion:
                mask &= (result_df['source'] == exclusion['source'])

            if 'type' in exclusion:
                mask &= (result_df['type'] == exclusion['type'])

            if 'category' in exclusion:
                mask &= (result_df['category'] == exclusion['category'])

            if 'description_contains' in exclusion:
                mask &= result_df['merchant'].str.contains(
                    exclusion['description_contains'], case=False, na=False
                )

            # Remove matching transactions
            excluded_count = mask.sum()
            if excluded_count > 0:
                print(f"Excluded {excluded_count} transactions: {exclusion.get('reason', 'No reason provided')}")
                result_df = result_df[~mask].reset_index(drop=True)

        return result_df

    def apply_custom_rules(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply custom categorization rules."""
        result_df = df.copy()

        # Custom rules will override categories directly

        custom_rules = self.custom_rules.get('custom_rules', [])

        for rule in custom_rules:
            # Build filter conditions
            mask = pd.Series([True] * len(result_df))

            conditions = rule.get('conditions', {})

            if 'source' in conditions:
                mask &= (result_df['source'] == conditions['source'])

            if 'type' in conditions:
                mask &= (result_df['type'] == conditions['type'])

            if 'category' in conditions:
                mask &= (result_df['category'] == conditions['category'])

            if 'description_contains' in conditions:
                mask &= result_df['merchant'].str.contains(
                    conditions['description_contains'], case=False, na=False
                )

            if 'amount_min' in conditions:
                mask &= (result_df['amount'] >= conditions['amount_min'])

            if 'amount_max' in conditions:
                mask &= (result_df['amount'] <= conditions['amount_max'])

            # Apply actions
            if mask.any():
                actions = rule.get('action', {})

                if 'category' in actions:
                    result_df.loc[mask, 'category'] = actions['category']


                matched_count = mask.sum()
                print(f"Applied rule '{rule.get('name', 'Unknown')}' to {matched_count} transactions")

        return result_df

    def apply_category_mapping(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply category mapping to create master categories."""
        result_df = df.copy()

        # Initialize master_category column
        result_df['master_category'] = self.category_mapping.get('default_category', 'Uncategorized')

        master_categories = self.category_mapping.get('master_categories', {})

        # Apply mappings based on category
        for orig_category, master_category in master_categories.items():
            orig_mask = (result_df['category'] == orig_category)
            result_df.loc[orig_mask, 'master_category'] = master_category

        return result_df

    def apply_merchant_grouping(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply merchant grouping rules."""
        result_df = df.copy()

        # Initialize merchant_group with original merchant names
        result_df['merchant_group'] = result_df['merchant']

        merchant_groups = self.custom_rules.get('merchant_groups', {})

        for group_name, group_config in merchant_groups.items():
            patterns = group_config.get('patterns', [])
            master_name = group_config.get('master_name', group_name)

            # Apply patterns
            for pattern in patterns:
                mask = result_df['merchant'].str.contains(pattern, case=False, na=False)
                result_df.loc[mask, 'merchant_group'] = master_name

        return result_df