import argparse
import csv
import sys
from pathlib import Path

# Fix path to include src if running from root
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.postprocess.report_lib import ReportStandardizer

def export_datavyu_csv(report_path, output_path):
    print(f"Reading report: {report_path}")
    
    standardizer = ReportStandardizer()
    data = standardizer.load_report(report_path)
    
    if not data:
        print("Error: Could not load report data.")
        return False
        
    events = data.get("aggregated_events", [])
    if not events:
        print("Warning: No events found in report.")
        
    rows = standardizer.get_datavyu_rows(events)
    
    # Write to CSV
    # Datavyu typically accepts a flexible CSV but having a header is good practice for import mapping.
    # Columns: onset, offset, code01, code02, comment
    
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["onset", "offset", "code01", "code02", "comment"])
            writer.writeheader()
            writer.writerows(rows)
            
        print(f"Successfully exported {len(rows)} events to {output_path}")
        return True
    except Exception as e:
        print(f"Failed to write CSV: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Export AQC Master Report to Datavyu CSV")
    parser.add_argument("--input", required=True, help="Path to Master_Report.json")
    parser.add_argument("--output", required=True, help="Output path for .csv file")
    
    args = parser.parse_args()
    
    export_datavyu_csv(args.input, args.output)

if __name__ == "__main__":
    main()
