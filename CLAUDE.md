# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a family expense report generator that processes transaction data from multiple financial sources (Chase checking, Chase credit card, Apple Card) and generates comprehensive spending reports. The application uses a configurable rules engine for categorization, exclusions, and merchant grouping.

## Architecture

### Core Components

- **`app/data_loaders.py`**: Abstract base class and concrete loaders for different financial data sources
  - `ChaseCheckingLoader`: Processes Chase checking account CSV exports
  - `ChaseCreditCardLoader`: Processes Chase credit card CSV exports  
  - `AppleCardLoader`: Processes Apple Card CSV exports (supports multiple users)
  - `load_all_data()`: Orchestrates loading from all configured sources

- **`app/rules_engine.py`**: Configurable rules system for data processing
  - Exclusion rules to filter unwanted transactions
  - Custom categorization rules with pattern matching
  - Category mapping to standardize categories
  - Merchant grouping to consolidate similar merchants

- **`app/processor.py`**: Main data processing pipeline (`ExpenseProcessor`)
  - Loads data from all sources
  - Applies rules engine transformations
  - Adds derived fields (year, month, transaction type, etc.)
  - Saves intermediate data files

- **`app/report_generator.py`**: Report generation system (`ReportGenerator`)
  - Cashflow summaries by account group
  - Top expenses and categories analysis
  - Merchant spending analysis
  - Monthly trend reports

### Configuration System

Configuration files in `app/config/`:
- **`report.yaml`**: Report settings, account groupings, output preferences
- **`exclusions.yaml`**: Rules for filtering out transactions (e.g., credit card payments)
- **`rules.yaml`**: Custom categorization rules and merchant grouping patterns
- **`category_mapping.yaml`**: Master category mappings

### Data Flow

1. Load CSV files from multiple sources using data loaders
2. Apply exclusion rules to filter unwanted transactions
3. Apply custom categorization rules for specific transaction patterns
4. Map categories to master categories for consistent reporting
5. Group similar merchants together
6. Add derived fields (dates, amounts, account groups)
7. Generate comprehensive reports and save intermediate data

## Development Commands

### Dependencies and Environment
```bash
# Install dependencies
poetry install --with dev

# Run tests
poetry run pytest tests/ -v

# Run with coverage
poetry run pytest tests/ --cov=app
```

### Running the Application
```bash
# Run the main application
poetry run python -m app.main app/data/

# With custom config and output folders
poetry run python -m app.main app/data/ --config config --output output --verbose
```

### Testing
```bash
# Run all tests
poetry run pytest tests/ -v

# Run specific test file
poetry run pytest tests/test_rules_engine.py -v

# Run specific test method
poetry run pytest tests/test_rules_engine.py::TestRulesEngine::test_category_mapping -v
```

## Data Sources Structure

The application expects data in the following structure:
```
data/
├── chase_checking/          # Chase checking account CSV files
├── chase_credit_card/       # Chase credit card CSV files  
├── joe_apple_card/         # Joe's Apple Card CSV files
└── nikita_apple_card/      # Nikita's Apple Card CSV files
```

## Key Implementation Details

### Account Grouping
- `shared`: Chase checking and credit card accounts
- `joe`: Joe's Apple Card
- `nikita`: Nikita's Apple Card
- `all`: All accounts combined

### Standard Transaction Fields
All data loaders normalize transactions to these fields:
- `date`: Transaction date
- `description`: Transaction description
- `amount`: Transaction amount (negative for expenses)
- `category`: Original category from source
- `merchant`: Merchant name
- `source`: Data source identifier
- `account_owner`: Account owner (shared, joe, nikita)

### Rules Engine Processing Order
1. Exclusions (remove unwanted transactions)
2. Custom rules (apply special categorization)
3. Category mapping (standardize categories)
4. Merchant grouping (consolidate merchants)

## Project Structure Notes

- The `app/` directory is a Python package with proper imports
- Tests use `from app.module import Class` syntax
- Run tests from project root with `poetry run pytest`
- Main application runs with `poetry run python -m app.main`
- Configuration files are in `app/config/`
- Data files go in `app/data/sources/`
- Reports are generated in `output/reports/`
- Intermediate data saved in `output/intermediate/`