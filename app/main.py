#!/usr/bin/env python3
"""
Quarterly Expense Report Generator

Usage:
    python -m app.main [data_folder]
    or
    poetry run python -m app.main [data_folder]

Example:
    python -m app.main app/data/
"""
import sys
import argparse
from pathlib import Path
from .processor import ExpenseProcessor
from .report_generator import ReportGenerator


def main():
    """Main entry point for expense analysis."""
    parser = argparse.ArgumentParser(description='Generate expense reports from CSV data')
    parser.add_argument('data_folder', 
                       help='Folder containing expense data (with subfolders for each source)')
    parser.add_argument('--config', '-c', 
                       default='config',
                       help='Configuration folder (default: config)')
    parser.add_argument('--output', '-o',
                       default='output', 
                       help='Output folder (default: output)')
    parser.add_argument('--verbose', '-v',
                       action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Validate input folder
    data_path = Path(args.data_folder)
    if not data_path.exists():
        print(f"Error: Data folder '{data_path}' does not exist")
        sys.exit(1)
    
    try:
        # Initialize processor
        processor = ExpenseProcessor(
            config_folder=args.config,
            output_folder=args.output
        )
        
        # Process data
        df = processor.process_data(args.data_folder)
        
        if len(df) == 0:
            print("Warning: No data to process after filtering")
            return
        
        # Generate reports
        report_generator = ReportGenerator(processor, args.output)
        report_generator.print_summary_statistics(df)
        report_generator.generate_all_reports(df)
        
        print("\n✅ Analysis complete!")
        print(f"📊 Reports saved to: {Path(args.output) / 'reports'}")
        print(f"📁 Intermediate data saved to: {Path(args.output) / 'intermediate'}")
        
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()