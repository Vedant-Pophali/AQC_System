import json
from pathlib import Path

class MasterAggregator:
    """
    Stitches segment-level results into a unified master report.
    Handles timecode and frame number offsets.
    """
    def __init__(self, segments_results, profile_mode):
        self.segments_results = sorted(segments_results, key=lambda x: x['segment_id'])
        self.profile_mode = profile_mode
        self.master_report = {
            "version": "2.0.0-spark",
            "profile": profile_mode,
            "status": "UNKNOWN",
            "summary": {
                "total_segments": len(self.segments_results),
                "total_errors": 0,
                "total_warnings": 0
            },
            "modules": {}
        }

    def aggregate(self):
        for segment in self.segments_results:
            offset_sec = segment['start_time']
            # We need to know FPS to calculate frame offset, 
            # but most validators provide time-based details.
            
            for report in segment['reports']:
                module_name = report.get('module', 'unknown')
                if module_name not in self.master_report['modules']:
                    self.master_report['modules'][module_name] = {
                        "status": "PASSED",
                        "details": {}
                    }
                
                module_master = self.master_report['modules'][module_name]
                
                # Update Status (Escalation logic)
                status = report.get('effective_status', report.get('status', 'PASSED'))
                if status == "REJECTED":
                    module_master["status"] = "REJECTED"
                elif status == "WARNING" and module_master["status"] != "REJECTED":
                    module_master["status"] = "WARNING"
                
                # Merge Details with Offsets
                details = report.get('details', {})
                self._merge_details(module_name, module_master['details'], details, offset_sec)

        # Final Master Status
        self.master_report["status"] = self._calculate_overall_status()
        return self.master_report

    def _merge_details(self, module, master_details, segment_details, offset_sec):
        """
        Custom merging logic per validator type.
        """
        # Generic list merging
        for key, value in segment_details.items():
            if isinstance(value, list):
                if key not in master_details:
                    master_details[key] = []
                
                # Adjust time-based values in lists
                adjusted_list = []
                for item in value:
                    if isinstance(item, dict):
                        new_item = item.copy()
                        if 'timestamp' in new_item:
                            new_item['timestamp'] = round(new_item['timestamp'] + offset_sec, 3)
                        if 'start_sec' in new_item:
                            new_item['start_sec'] = round(new_item['start_sec'] + offset_sec, 3)
                        if 'end_sec' in new_item:
                            new_item['end_sec'] = round(new_item['end_sec'] + offset_sec, 3)
                        # Support for new validator keys
                        if 'start_time' in new_item:
                            new_item['start_time'] = round(new_item['start_time'] + offset_sec, 3)
                        if 'end_time' in new_item:
                            new_item['end_time'] = round(new_item['end_time'] + offset_sec, 3)
                        adjusted_list.append(new_item)
                    else:
                        adjusted_list.append(item)
                
                master_details[key].extend(adjusted_list)
            else:
                # For non-list metrics (like integrated loudness), 
                # we might need averaging or max logic, but for now we'll just keep the last or max
                if key not in master_details:
                    master_details[key] = value
                else:
                    # Update max/worst case if single value
                    if isinstance(value, (int, float)):
                        if "mean_phase" in key:
                            # Simple running average for now, could be weighted by duration
                            master_details[key] = (master_details[key] + value) / 2
                        elif "min_phase" in key:
                            master_details[key] = min(master_details[key], value)
                        elif "offset" in key.lower() or "error" in key.lower():
                            master_details[key] = max(master_details[key], value)

    def _calculate_overall_status(self):
        statuses = [m['status'] for m in self.master_report['modules'].values()]
        if "REJECTED" in statuses: return "REJECTED"
        if "WARNING" in statuses: return "WARNING"
        return "PASSED"

    def _stitch_events(self, events, tolerance=0.1):
        """
        Merges overlapping or adjacent events of the same type.
        """
        if not events: return []
        
        # Sort by Type, then Start Time
        sorted_events = sorted(events, key=lambda x: (x.get("type", "unknown"), x.get("start_time", 0)))
        
        stitched = []
        if not sorted_events: return []
        
        current = sorted_events[0]
        
        for next_evt in sorted_events[1:]:
            # Check if same type
            if current.get("type") == next_evt.get("type"):
                # Check overlap or adjacency
                curr_end = current.get("end_time", 0)
                next_start = next_evt.get("start_time", 0)
                
                if next_start <= (curr_end + tolerance):
                    # Merge: Extend current end time
                    current["end_time"] = max(curr_end, next_evt.get("end_time", 0))
                    # Append details if unique
                    if next_evt.get("details") not in current.get("details", ""):
                        current["details"] += f" | {next_evt.get('details')}"
                    continue
            
            # No merge, push current and move on
            stitched.append(current)
            current = next_evt
        
        stitched.append(current)
        return sorted(stitched, key=lambda x: x.get("start_time", 0))

    def aggregate(self):
        # ... (Existing aggregation logic)
        for segment in self.segments_results:
            offset_sec = segment['start_time']
            for report in segment['reports']:
                module_name = report.get('module', 'unknown')
                if module_name not in self.master_report['modules']:
                    self.master_report['modules'][module_name] = {
                        "status": "PASSED",
                        "details": {}
                    }
                
                module_master = self.master_report['modules'][module_name]
                
                # Update Status
                status = report.get('effective_status', report.get('status', 'PASSED'))
                if status == "REJECTED":
                    module_master["status"] = "REJECTED"
                elif status == "WARNING" and module_master["status"] != "REJECTED":
                    module_master["status"] = "WARNING"
                
                # Merge Details with Offsets
                details = report.get('details', {})
                self._merge_details(module_name, module_master['details'], details, offset_sec)

        # Final Master Status
        self.master_report["status"] = self._calculate_overall_status()
        
        # --- NEW: Generate Aggregated Events for Dashboard ---
        all_raw_events = []
        for module_name, module_data in self.master_report['modules'].items():
            # Get events from details (preferred) or top-level (legacy)
            details = module_data.get("details", {})
            events = details.get("events", [])
            
            # If not in details, check top-level (though _merge_details puts them in details usually)
            if not events:
                events = module_data.get("events", [])

            for e in events:
                # Add source module if missing
                if "source_module" not in e:
                    e["source_module"] = module_name
                all_raw_events.append(e)

        self.master_report["aggregated_events"] = self._stitch_events(all_raw_events)
        
        return self.master_report

    def save(self, output_path):
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.master_report, f, indent=4)
