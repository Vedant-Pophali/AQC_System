import json
from pathlib import Path

class TimecodeHelper:
    @staticmethod
    def seconds_to_smpte(seconds, fps=24):
        """Converts seconds to SMPTE HH:MM:SS:FF format"""
        if seconds is None:
            seconds = 0
            
        total_frames = int(seconds * fps)
        
        hours = total_frames // (3600 * fps)
        minutes = (total_frames % (3600 * fps)) // (60 * fps)
        secs = (total_frames % (60 * fps)) // fps
        frames = total_frames % fps
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"

    @staticmethod
    def smpte_to_seconds(smpte, fps=24):
        """Converts SMPTE HH:MM:SS:FF to seconds"""
        if not smpte: return 0.0
        parts = list(map(int, smpte.split(":")))
        if len(parts) != 4: return 0.0
        
        h, m, s, f = parts
        return (h * 3600) + (m * 60) + s + (f / fps)

class ReportStandardizer:
    
    SEVERITY_MAP = {
        "CRITICAL": 5,
        "REJECTED": 5,
        "SEVERE": 5,
        "MODERATE": 3,
        "WARNING": 2,
        "MILD": 1,
        "PASSED": 0,
        "UNKNOWN": 1
    }

    COLOR_MAP = {
        "Audio": "#1f77b4",         # Blue
        "Audio Quality": "#1f77b4", 
        "Video Error": "#d62728",   # Red
        "Video Quality": "#ff7f0e", # Orange
        "Archival": "#00bcd4",      # Cyan
        "Sync": "#2ca02c",          # Green
        "Structure": "#9467bd",     # Purple
        "Metadata": "#8c564b",      # Brown
        "Other": "#7f7f7f"          # Grey
    }

    def __init__(self, fps=24):
        self.fps = fps

    def load_report(self, path):
        """Loads JSON report and ensures access to aggregated events."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return self._ensure_aggregated_events(data)
        except Exception as e:
            print(f"[ERROR] Failed to load report {path}: {e}")
            return {}

    def _ensure_aggregated_events(self, data):
        """If aggregated_events is missing, collect them from modules."""
        if "aggregated_events" in data and data["aggregated_events"]:
            return data
        
        events = []
        modules = data.get("modules", {})
        for mod_name, mod_data in modules.items():
            if "events" in mod_data:
                for evt in mod_data["events"]:
                    # Create a copy to not mutate original
                    e = evt.copy() 
                    e["origin_module"] = mod_name
                    # Normalize time
                    if "start_time" not in e:
                        e["start_time"] = e.get("timestamp", 0.0)
                        # Some incomplete events might lack end_time
                    if "end_time" not in e:
                         # Default to 1 sec duration if missing
                        e["end_time"] = e["start_time"] + 1.0  
                    
                    events.append(e)
        
        data["aggregated_events"] = events
        return data

    def normalize_event(self, event):
        """
        Returns a standardized dict with:
        - category (for UI/Datavyu grouping)
        - human_name
        - severity_score
        - datavyu_code
        """
        evt_type = str(event.get("type", "unknown")).lower()
        mod_name = str(event.get("origin_module", event.get("source_module", ""))).lower()
        details = str(event.get("details", "")).lower()
        severity = str(event.get("severity", "UNKNOWN")).upper()
        
        # Categorization Logic
        category = "Other"
        datavyu_code = "GEN"
        
        if "audio" in mod_name or "loudness" in mod_name or "silence" in evt_type:
            category = "Audio"
            datavyu_code = "AUD"
        elif "sync" in mod_name or "drift" in evt_type:
            category = "Sync"
            datavyu_code = "SYN"
        elif "structure" in mod_name or "metadata" in evt_type:
            category = "Structure"
            datavyu_code = "STR"
        elif "broadcast" in evt_type or "saturation" in evt_type:
            category = "Archival"
            datavyu_code = "ARC"
        elif "artifact" in evt_type or "bitrate" in evt_type or "block" in details:
            category = "Video Quality"
            datavyu_code = "VQUAL"
        elif "black" in evt_type or "freeze" in evt_type or "interlace" in evt_type:
            category = "Video Error"
            datavyu_code = "VERR"
            
        human_name = evt_type.replace("_", " ").title()
        
        return {
            "category": category,
            "human_name": human_name,
            "severity_score": self.SEVERITY_MAP.get(severity, 1),
            "datavyu_code": datavyu_code,
            "original_severity": severity,
            "color": self.COLOR_MAP.get(category, self.COLOR_MAP["Other"])
        }

    def get_datavyu_rows(self, events):
        """Generates rows for Datavyu CSV import."""
        rows = []
        for evt in events:
            std = self.normalize_event(evt)
            
            start = evt.get("start_time", 0.0)
            end = evt.get("end_time", 0.0)
            
            # Datavyu format requires specific columns often interact with scripts
            # We will adhere to: onset (ms), offset (ms), code01, code02, comment
            
            rows.append({
                "onset": int(start * 1000),
                "offset": int(end * 1000),
                "code01": std["datavyu_code"],
                "code02": std["original_severity"],
                "comment": f"{std['human_name']}: {evt.get('details', '')}"
            })
        return rows
