"""
Main data processor for expense analysis.
"""
import pandas as pd
import yaml
from pathlib import Path
from typing import Dict, Any
from .data_loaders import load_all_data
from .rules_engine import RulesEngine


class ExpenseProcessor:
    """Main processor for expense data analysis."""
    
    def __init__(self, config_folder: str = "config", output_folder: str = "output"):
        self.config_folder = Path(config_folder)
        self.output_folder = Path(output_folder)
        self.intermediate_folder = self.output_folder / "intermediate"
        self.reports_folder = self.output_folder / "reports"
        
        # Create output directories
        self.intermediate_folder.mkdir(parents=True, exist_ok=True)
        self.reports_folder.mkdir(parents=True, exist_ok=True)
        
        # Load configuration
        self.report_config = self._load_config("report_config.yaml")
        self.rules_engine = RulesEngine(config_folder)
        
    def _load_config(self, filename: str) -> Dict[str, Any]:
        """Load configuration file."""
        config_path = self.config_folder / filename
        if not config_path.exists():
            print(f"Warning: {config_path} not found, using defaults")
            return {}
        
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def process_data(self, data_folder: str) -> pd.DataFrame:
        """Main processing pipeline."""
        print("=== Starting Expense Analysis ===")
        
        # 1. Load all data
        print("\n1. Loading data...")
        df = load_all_data(data_folder)
        print(f"Total transactions loaded: {len(df)}")
        
        # 2. Apply exclusions
        print("\n2. Applying exclusions...")
        df = self.rules_engine.apply_exclusions(df)
        print(f"Transactions after exclusions: {len(df)}")
        
        # 3. Apply custom rules
        print("\n3. Applying custom categorization rules...")
        df = self.rules_engine.apply_custom_rules(df)
        
        # 4. Apply category mapping
        print("\n4. Mapping categories...")
        df = self.rules_engine.apply_category_mapping(df)
        
        # 5. Apply merchant grouping
        print("\n5. Grouping merchants...")
        df = self.rules_engine.apply_merchant_grouping(df)
        
        # 6. Add derived fields
        print("\n6. Adding derived fields...")
        df = self._add_derived_fields(df)
        
        # 7. Save intermediate data
        if self.report_config.get('output_settings', {}).get('save_intermediate', True):
            print("\n7. Saving intermediate data...")
            self._save_intermediate_data(df)
        
        print(f"\n=== Processing Complete: {len(df)} transactions ===")
        return df
    
    def _add_derived_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add derived fields for analysis."""
        result_df = df.copy()
        
        # Add month, year for time-based analysis
        result_df['year'] = result_df['date'].dt.year
        result_df['month'] = result_df['date'].dt.month
        result_df['year_month'] = result_df['date'].dt.to_period('M')
        
        # Add absolute amount for sorting
        result_df['abs_amount'] = result_df['amount'].abs()
        
        # Add expense vs income flag
        result_df['transaction_type'] = result_df['amount'].apply(
            lambda x: 'Income' if x > 0 else 'Expense'
        )
        
        # Add account grouping based on config
        account_groups = self.report_config.get('report_settings', {}).get('account_groups', {})
        result_df['account_group'] = 'unknown'
        
        for group_name, sources in account_groups.items():
            mask = result_df['source'].isin(sources)
            result_df.loc[mask, 'account_group'] = group_name
        
        return result_df
    
    def _save_intermediate_data(self, df: pd.DataFrame) -> None:
        """Save intermediate processed data."""
        output_settings = self.report_config.get('output_settings', {})
        files = output_settings.get('files', {})
        
        # Save main processed transactions
        processed_file = files.get('processed_transactions', 'processed_transactions.csv')
        output_path = self.intermediate_folder / processed_file
        df.to_csv(output_path, index=False)
        print(f"Saved processed transactions to: {output_path}")
        
        # Save summary by category
        category_summary = self._create_category_summary(df)
        category_file = files.get('category_summary', 'category_summary.csv')
        category_path = self.intermediate_folder / category_file
        category_summary.to_csv(category_path, index=False)
        print(f"Saved category summary to: {category_path}")
        
        # Save summary by merchant
        merchant_summary = self._create_merchant_summary(df)
        merchant_file = files.get('merchant_summary', 'merchant_summary.csv')
        merchant_path = self.intermediate_folder / merchant_file
        merchant_summary.to_csv(merchant_path, index=False)
        print(f"Saved merchant summary to: {merchant_path}")
    
    def _create_category_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create summary by category."""
        summary = df.groupby(['master_category', 'account_group']).agg({
            'amount': ['sum', 'count', 'mean'],
            'abs_amount': 'sum'
        }).round(2)
        
        # Flatten column names
        summary.columns = ['total_amount', 'transaction_count', 'avg_amount', 'total_abs_amount']
        summary = summary.reset_index()
        
        # Sort by total absolute amount
        summary = summary.sort_values('total_abs_amount', ascending=False)
        
        return summary
    
    def _create_merchant_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create summary by merchant."""
        summary = df.groupby(['merchant_group', 'account_group']).agg({
            'amount': ['sum', 'count', 'mean'],
            'abs_amount': 'sum'
        }).round(2)
        
        # Flatten column names
        summary.columns = ['total_amount', 'transaction_count', 'avg_amount', 'total_abs_amount']
        summary = summary.reset_index()
        
        # Sort by total absolute amount
        summary = summary.sort_values('total_abs_amount', ascending=False)
        
        return summary
    
    def get_cashflow_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate cashflow summary by account group."""
        cashflow = df.groupby(['account_group', 'transaction_type']).agg({
            'amount': 'sum',
            'abs_amount': 'sum'
        }).round(2)
        
        cashflow = cashflow.reset_index()
        
        # Pivot to show income vs expenses
        cashflow_pivot = cashflow.pivot_table(
            index='account_group', 
            columns='transaction_type', 
            values='amount', 
            fill_value=0
        ).round(2)
        
        # Add net cashflow
        if 'Income' in cashflow_pivot.columns and 'Expense' in cashflow_pivot.columns:
            cashflow_pivot['Net_Cashflow'] = cashflow_pivot['Income'] + cashflow_pivot['Expense']
        
        return cashflow_pivot.reset_index()
    
    def get_top_expenses(self, df: pd.DataFrame, n: int = None) -> pd.DataFrame:
        """Get top N expenses by absolute amount."""
        if n is None:
            n = self.report_config.get('report_settings', {}).get('top_n_transactions', 20)
        
        # Filter to expenses only
        expenses = df[df['amount'] < 0].copy()
        expenses = expenses.sort_values('abs_amount', ascending=False)
        
        return expenses.head(n)[['date', 'description', 'merchant_group', 'master_category', 
                                'amount', 'account_group', 'source', 'flags']]
    