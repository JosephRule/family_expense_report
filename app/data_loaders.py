"""
Data loaders for different expense data sources.
"""
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
from abc import ABC, abstractmethod


class DataLoader(ABC):
    """Base class for data loaders."""
    
    def __init__(self, folder_path: str):
        self.folder_path = Path(folder_path)
        
    @abstractmethod
    def load_data(self) -> pd.DataFrame:
        """Load and standardize data from source."""
        pass
    
    def _load_csv_files(self) -> pd.DataFrame:
        """Load and concatenate all CSV files in folder."""
        csv_files = list(self.folder_path.glob("*.csv"))
        if not csv_files:
            raise FileNotFoundError(f"No CSV files found in {self.folder_path}")
        
        dfs = []
        for file in csv_files:
            df = pd.read_csv(file)
            df['source_file'] = file.name
            dfs.append(df)
        
        return pd.concat(dfs, ignore_index=True)


class ChaseCheckingLoader(DataLoader):
    """Loader for Chase checking account data."""
    
    def load_data(self) -> pd.DataFrame:
        df = self._load_csv_files()
        
        # Standardize columns to common schema
        df_std = pd.DataFrame({
            'date': pd.to_datetime(df['Posting Date']),
            'merchant': df['Description'],
            'type': df['Type'],
            'category': pd.NA,  # Chase checking doesn't have category
            'amount': df['Amount'],
            'source': 'chase_checking',
            'account_owner': 'shared',
            'source_file': df['source_file']
        })
        
        return df_std


class ChaseCreditCardLoader(DataLoader):
    """Loader for Chase credit card data."""
    
    def load_data(self) -> pd.DataFrame:
        df = self._load_csv_files()
        
        # Standardize columns to common schema
        df_std = pd.DataFrame({
            'date': pd.to_datetime(df['Transaction Date']),
            'merchant': df['Description'],
            'type': df['Type'],
            'category': df['Category'],
            'amount': df['Amount'],
            'source': 'chase_credit_card',
            'account_owner': 'shared',
            'source_file': df['source_file']
        })
        
        return df_std


class AppleCardLoader(DataLoader):
    """Loader for Apple Card data."""
    
    def __init__(self, folder_path: str, owner: str):
        super().__init__(folder_path)
        self.owner = owner
        
    def load_data(self) -> pd.DataFrame:
        df = self._load_csv_files()
        
        # Standardize columns to common schema
        df_std = pd.DataFrame({
            'date': pd.to_datetime(df['Transaction Date']),
            'merchant': df['Description'],
            'type': df['Type'],
            'category': df['Category'],
            'amount': df['Amount (USD)'],
            'source': f'apple_card_{self.owner.lower()}',
            'account_owner': self.owner.lower(),
            'source_file': df['source_file']
        })
        
        return df_std


def load_all_data(data_folder: str) -> pd.DataFrame:
    """Load data from all sources and combine."""
    data_path = Path(data_folder)
    
    loaders = [
        ChaseCheckingLoader(data_path / "chase_checking"),
        ChaseCreditCardLoader(data_path / "chase_card"),
        AppleCardLoader(data_path / "joe_apple_card", "Joe"),
        AppleCardLoader(data_path / "nikita_apple_card", "Nikita")
    ]
    
    all_data = []
    for loader in loaders:
        try:
            data = loader.load_data()
            all_data.append(data)
            print(f"Loaded {len(data)} records from {loader.__class__.__name__}")
        except FileNotFoundError as e:
            print(f"Warning: {e}")
    
    if not all_data:
        raise ValueError("No data loaded from any source")
    
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df = combined_df.sort_values('date').reset_index(drop=True)
    
    return combined_df
