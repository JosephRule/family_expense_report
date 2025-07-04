"""
Report generator for expense analysis.
"""
import pandas as pd
import yaml
from pathlib import Path
from typing import Dict, List, Any


class ReportGenerator:
    """Generates various reports from processed expense data."""
    
    def __init__(self, processor, output_folder: str = "output"):
        self.processor = processor
        self.output_folder = Path(output_folder)
        self.reports_folder = self.output_folder / "reports"
        self.reports_folder.mkdir(parents=True, exist_ok=True)
        
        self.config = processor.report_config
        
    def generate_all_reports(self, df: pd.DataFrame) -> None:
        """Generate all reports."""
        print("\n=== Generating Reports ===")
        
        # 1. Cashflow summary
        print("Generating cashflow summary...")
        cashflow = self.processor.get_cashflow_summary(df)
        self._save_report(cashflow, "cashflow_summary.csv")
        self._print_cashflow_summary(cashflow)
        
        # 2. Top expenses
        print("\nGenerating top expenses...")
        top_expenses = self.processor.get_top_expenses(df)
        self._save_report(top_expenses, "top_expenses.csv")
        self._print_top_expenses(top_expenses)
        
        # 3. Category analysis by account group
        print("\nGenerating category analysis...")
        self._generate_category_reports(df)
        
        # 4. Merchant analysis by account group
        print("\nGenerating merchant analysis...")
        self._generate_merchant_reports(df)
        
        # 5. Monthly trends
        print("\nGenerating monthly trends...")
        self._generate_monthly_reports(df)
        
        print(f"\n=== All reports saved to: {self.reports_folder} ===")
    
    def _save_report(self, df: pd.DataFrame, filename: str) -> None:
        """Save report to CSV file."""
        output_path = self.reports_folder / filename
        df.to_csv(output_path, index=False)
        print(f"Saved: {output_path}")
    
    def _print_cashflow_summary(self, cashflow_df: pd.DataFrame) -> None:
        """Print cashflow summary to console."""
        print("\n--- CASHFLOW SUMMARY ---")
        print(cashflow_df.to_string(index=False))
    
    def _print_top_expenses(self, top_expenses_df: pd.DataFrame, n: int = 10) -> None:
        """Print top expenses to console."""
        print(f"\n--- TOP {n} EXPENSES ---")
        display_df = top_expenses_df.head(n)[['date', 'merchant_group', 'amount', 'master_category', 'account_group']]
        print(display_df.to_string(index=False))
    
    def _generate_category_reports(self, df: pd.DataFrame) -> None:
        """Generate category analysis reports by account group."""
        report_settings = self.config.get('report_settings', {})
        account_groups = report_settings.get('account_groups', {})
        top_n = report_settings.get('top_n_categories', 10)
        
        for group_name, sources in account_groups.items():
            if group_name == 'all':
                continue  # Skip 'all' group to avoid duplication
                
            # Filter data for this account group
            group_df = df[df['source'].isin(sources)].copy()
            
            if len(group_df) == 0:
                continue
            
            # Category summary for expenses only
            expenses = group_df[group_df['amount'] < 0].copy()
            if len(expenses) > 0:
                category_summary = expenses.groupby('master_category').agg({
                    'amount': 'sum',
                    'abs_amount': 'sum'
                }).round(2)
                category_summary = category_summary.sort_values('abs_amount', ascending=False)
                category_summary = category_summary.reset_index()
                
                # Save top categories
                filename = f"top_categories_{group_name}.csv"
                self._save_report(category_summary.head(top_n), filename)
                
                # Print summary
                print(f"\n--- TOP EXPENSE CATEGORIES: {group_name.upper()} ---")
                display_df = category_summary.head(10)[['master_category', 'amount', 'abs_amount']]
                display_df.columns = ['Category', 'Total_Spent', 'Absolute_Amount']
                print(display_df.to_string(index=False))
    
    def _generate_merchant_reports(self, df: pd.DataFrame) -> None:
        """Generate merchant analysis reports by account group."""
        report_settings = self.config.get('report_settings', {})
        account_groups = report_settings.get('account_groups', {})
        top_n = report_settings.get('top_n_merchants', 15)
        min_amount = report_settings.get('min_transaction_amount', 10.0)
        
        for group_name, sources in account_groups.items():
            if group_name == 'all':
                continue
                
            # Filter data for this account group
            group_df = df[df['source'].isin(sources)].copy()
            
            if len(group_df) == 0:
                continue
            
            # Merchant summary for expenses only, above minimum amount
            # Exclude fixed/structural categories: Housing, Debt, Childcare, Savings
            excluded_categories = ['Home & Garden', 'Debt Payments', 'Childcare', 'Savings']
            expenses = group_df[
                (group_df['amount'] < 0) & 
                (group_df['abs_amount'] >= min_amount) &
                (~group_df['master_category'].isin(excluded_categories))
            ].copy()
            
            if len(expenses) > 0:
                merchant_summary = expenses.groupby('merchant_group').agg({
                    'amount': 'sum',
                    'abs_amount': ['sum', 'count']
                }).round(2)
                
                # Flatten column names
                merchant_summary.columns = ['total_spent', 'total_abs_amount', 'transaction_count']
                merchant_summary = merchant_summary.sort_values('total_abs_amount', ascending=False)
                merchant_summary = merchant_summary.reset_index()
                
                # Save top merchants
                filename = f"top_merchants_{group_name}.csv"
                self._save_report(merchant_summary.head(top_n), filename)
                
                # Print summary
                print(f"\n--- TOP DISCRETIONARY MERCHANTS: {group_name.upper()} ---")
                print("(Excludes: Housing, Debt Payments, Childcare, Savings)")
                display_df = merchant_summary.head(10)[['merchant_group', 'total_spent', 'transaction_count']]
                display_df.columns = ['Merchant', 'Total_Spent', 'Transactions']
                print(display_df.to_string(index=False))
    
    def _generate_monthly_reports(self, df: pd.DataFrame) -> None:
        """Generate monthly trend reports."""
        # Create year_month on the fly
        df_monthly = df.copy()
        df_monthly['year_month'] = df_monthly['date'].dt.to_period('M')
        
        # Monthly spending by category
        monthly_categories = df_monthly[df_monthly['amount'] < 0].groupby(['year_month', 'master_category']).agg({
            'amount': 'sum',
            'abs_amount': 'sum'
        }).round(2)
        
        monthly_categories = monthly_categories.reset_index()
        self._save_report(monthly_categories, "monthly_spending_by_category.csv")
        
        # Monthly totals by account group
        monthly_totals = df_monthly.groupby(['year_month', 'account_group', 'transaction_type']).agg({
            'amount': 'sum'
        }).round(2)
        
        monthly_totals = monthly_totals.reset_index()
        self._save_report(monthly_totals, "monthly_totals_by_account.csv")
        
        # Overall monthly summary
        monthly_summary = df_monthly.groupby(['year_month', 'transaction_type']).agg({
            'amount': 'sum'
        }).round(2)
        
        monthly_pivot = monthly_summary.reset_index().pivot_table(
            index='year_month',
            columns='transaction_type', 
            values='amount',
            fill_value=0
        ).round(2)
        
        if 'Income' in monthly_pivot.columns and 'Expense' in monthly_pivot.columns:
            monthly_pivot['Net_Cashflow'] = monthly_pivot['Income'] + monthly_pivot['Expense']
        
        monthly_pivot = monthly_pivot.reset_index()
        self._save_report(monthly_pivot, "monthly_cashflow_summary.csv")
        
        print("\n--- MONTHLY CASHFLOW TRENDS ---")
        print(monthly_pivot.to_string(index=False))
    
    def print_summary_statistics(self, df: pd.DataFrame) -> None:
        """Print high-level summary statistics."""
        print("\n=== SUMMARY STATISTICS ===")
        
        total_transactions = len(df)
        date_range = f"{df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}"
        
        print(f"Total Transactions: {total_transactions:,}")
        print(f"Date Range: {date_range}")
        
        # Income vs Expenses
        income = df[df['amount'] > 0]['amount'].sum()
        expenses = df[df['amount'] < 0]['amount'].sum()
        net = income + expenses
        
        print(f"\nTotal Income: ${income:,.2f}")
        print(f"Total Expenses: ${expenses:,.2f}")
        print(f"Net Cashflow: ${net:,.2f}")
        
        # By account group
        print(f"\nBy Account Group:")
        account_summary = df.groupby('account_group')['amount'].sum().round(2)
        for account, amount in account_summary.items():
            print(f"  {account}: ${amount:,.2f}")
        
        # Transaction sources
        print(f"\nTransactions by Source:")
        source_counts = df['source'].value_counts()
        for source, count in source_counts.items():
            print(f"  {source}: {count:,}")