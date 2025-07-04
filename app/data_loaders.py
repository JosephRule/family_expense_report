"""
Data loaders for different expense data sources.
"""
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
from abc import ABC, abstractmethod
from .constants import SourceIds, AccountOwners, SourceFolders


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
        csv_files = list(self.folder_path.glob("*.csv")) + list(self.folder_path.glob("*.CSV"))
        if not csv_files:
            raise FileNotFoundError(f"No CSV files found in {self.folder_path}")
        
        dfs = []
        for file in csv_files:
            df = pd.read_csv(file, dtype=str)  # Load all columns as strings to avoid parsing issues
            df['source_file'] = file.name
            dfs.append(df)
        
        return pd.concat(dfs, ignore_index=True)


class ChaseCheckingLoader(DataLoader):
    """Loader for Chase checking account data."""
    
    def load_data(self) -> pd.DataFrame:
        df = self._load_csv_files()
        
        # CSV columns are shifted: Details=date, Posting Date=description, Description=amount, Amount=type, Type=balance
        df_std = pd.DataFrame({
            'date': pd.to_datetime(df['Details'], format='%m/%d/%Y'),
            'merchant': df['Posting Date'],
            'type': df['Amount'],
            'category': pd.NA,  # Chase checking doesn't have category
            'amount': pd.to_numeric(df['Description']),
            'source': SourceIds.CHASE_CHECKING,
            'account_owner': AccountOwners.SHARED,
            'source_file': df['source_file']
        })
        
        return df_std


class ChaseCreditCardLoader(DataLoader):
    """Loader for Chase credit card data."""
    
    def load_data(self) -> pd.DataFrame:
        df = self._load_csv_files()
        
        # Standardize columns to common schema
        df_std = pd.DataFrame({
            'date': pd.to_datetime(df['Transaction Date'], format='%m/%d/%Y'),
            'merchant': df['Description'],
            'type': df['Type'],
            'category': df['Category'],
            'amount': pd.to_numeric(df['Amount']),
            'source': SourceIds.CHASE_CREDIT_CARD,
            'account_owner': AccountOwners.SHARED,
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
            'date': pd.to_datetime(df['Transaction Date'], format='%m/%d/%Y'),
            'merchant': df['Description'],
            'type': df['Type'],
            'category': df['Category'],
            'amount': -pd.to_numeric(df['Amount (USD)']),  # Flip sign to make purchases negative
            'source': SourceIds.apple_card_for_owner(self.owner),
            'account_owner': self.owner.lower(),
            'source_file': df['source_file']
        })
        
        return df_std


def load_all_data(data_folder: str) -> pd.DataFrame:
    """Load data from all sources and combine."""
    data_path = Path(data_folder)
    
    loaders = [
        ChaseCheckingLoader(data_path / SourceFolders.CHASE_CHECKING),
        ChaseCreditCardLoader(data_path / SourceFolders.CHASE_CREDIT_CARD),
        AppleCardLoader(data_path / SourceFolders.JOE_APPLE_CARD, "Joe"),
        AppleCardLoader(data_path / SourceFolders.NIKITA_APPLE_CARD, "Nikita")
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
