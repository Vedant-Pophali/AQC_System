
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from src.postprocess.master_aggregator import MasterAggregator

def test_aggregator_loss():
    # Simulate Validator Output (Top-level events)
    segment_results = [
        {
            "segment_id": 0,
            "start_time": 0.0,
            "reports": [
                {
                    "module": "validate_black_freeze",
                    "status": "REJECTED",
                    "details": {
                        "events": [
                            {
                                "type": "black_frame",
                                "start_time": 2.0,
                                "end_time": 5.0
                            }
                        ]
                    }
                }
            ]
        }
    ]
    
    print("--- INPUT ---")
    print(json.dumps(segment_results, indent=2))
    
    agg = MasterAggregator(segment_results, "strict")
    master = agg.aggregate()
    
    print("\n--- OUTPUT ---")
    print(json.dumps(master, indent=2))
    
    # Check if events survived
    module_data = master["modules"]["validate_black_freeze"]
    
    # Check details['events']
    events_in_details = module_data.get("details", {}).get("events", [])
    
    if not events_in_details:
        print("\n[FAIL] Events were LOST during aggregation!")
        return False
    else:
        print(f"\n[PASS] Found {len(events_in_details)} events in aggregated report.")
        return True

if __name__ == "__main__":
    success = test_aggregator_loss()
    sys.exit(0 if success else 1)
