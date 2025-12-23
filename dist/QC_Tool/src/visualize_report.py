import plotly.express as px
import json
import pandas as pd
import argparse
import os
import sys
import webbrowser

sys.stdout.reconfigure(encoding='utf-8')

def create_dashboard(master_report_path, output_path):
    abs_master_path = os.path.abspath(master_report_path)
    abs_output_path = os.path.abspath(output_path)

    if not os.path.exists(abs_master_path):
        print(f"[ERROR] Master Report not found")
        return

    try:
        with open(abs_master_path, "r", encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERROR] JSON Load Failed: {e}")
        return

    timeline_data = []
    video_duration = data.get("metadata", {}).get("duration", 0)
    if video_duration == 0: video_duration = 100

    # --- 0. STRUCTURAL QC (Black/Grey) ---
    if "structure_qc" in data.get("modules", {}):
        module_data = data["modules"]["structure_qc"]
        status = module_data.get("status")
        if status == "REJECTED" or status == "CRITICAL_FAIL":
            error_msg = module_data.get("events", [{}])[0].get("error", "Unknown Error")
            timeline_data.append(dict(
                Module="Container Structure", Start=0, Duration=video_duration,
                Status="CRITICAL_FAIL", Details=f"CORRUPTION: {error_msg}"
            ))
        elif status == "PASSED":
            timeline_data.append(dict(
                Module="Container Structure", Start=0, Duration=video_duration,
                Status="PASSED", Details="Valid MP4 Container (Moov Atom OK)"
            ))

    # --- 1. AUDIO QC (Orange = Fail, Blue = Fixed) ---
    if "audio_qc" in data.get("modules", {}):
        module_data = data["modules"]["audio_qc"]
        # Check if correction happened
        correction = module_data.get("correction", {})
        is_fixed = correction.get("status") == "FIXED"

        for event in module_data.get("events", []):
            start = event.get("start_time", 0)
            end = event.get("end_time", video_duration)

            # If fixed, change color and text
            if is_fixed:
                status = "INFO" # Blue
                details = f"Loudness FIXED. (Was: {event['details'].get('measured_lufs')} LUFS)"
            else:
                status = "REJECTED" # Orange/Red
                details = f"Loudness Violation: {event['details'].get('measured_lufs', 'N/A')} LUFS"

            timeline_data.append(dict(
                Module="Audio QC", Start=start, Duration=(end - start),
                Status=status, Details=details
            ))

        # Add a "Healing Badge" event
        if is_fixed:
            timeline_data.append(dict(
                Module="System Status", Start=0, Duration=video_duration,
                Status="INFO",
                Details=f"Auto-Correction: {os.path.basename(correction.get('new_file', ''))}"
            ))

    # --- 1.5 AUDIO SIGNAL INTEGRITY (Pink) ---
    if "audio_signal_qc" in data.get("modules", {}):
        module_data = data["modules"]["audio_signal_qc"]
        status = module_data.get("status")

        if status == "REJECTED":
            for event in module_data.get("events", []):
                timeline_data.append(dict(
                    Module="Audio Integrity",
                    Start=0,
                    Duration=video_duration,
                    Status="REJECTED",
                    Details=f"{event.get('type')}: {event.get('details')}"
                ))
        elif status == "PASSED":
            timeline_data.append(dict(
                Module="Audio Integrity",
                Start=0,
                Duration=video_duration,
                Status="PASSED",
                Details="No Distortion or DC Offset"
            ))

    # --- 2. SIGNAL QC (Purple/Green) ---
    if "signal_qc" in data.get("modules", {}):
        module_data = data["modules"]["signal_qc"]
        status = module_data.get("status")
        if status == "REJECTED":
            timeline_data.append(dict(
                Module="Signal Integrity", Start=0, Duration=video_duration,
                Status="CRITICAL", Details=f"Broadcast Violation: {module_data.get('details', {}).get('note', 'Check Limits')}"
            ))
        elif status == "PASSED":
            timeline_data.append(dict(
                Module="Signal Integrity", Start=0, Duration=video_duration,
                Status="PASSED", Details="Broadcast Safe"
            ))

    # --- 3. OCR TEXT (Blue) ---
    if "ocr_extraction" in data.get("modules", {}):
        for event in data["modules"]["ocr_extraction"].get("events", []):
            start = event.get("start_time", 0)
            end = event.get("end_time", start + 2)
            text = event['details'].get('text', '')
            if len(text) > 40: text = text[:37] + "..."
            timeline_data.append(dict(
                Module="Vernacular Text", Start=start, Duration=(end - start),
                Status="INFO", Details=f"[{event['details'].get('language','?')}] {text}"
            ))

    # --- 4. VISUAL QC (Yellow) ---
    if "visual_qc" in data.get("modules", {}):
        for event in data["modules"]["visual_qc"].get("events", []):
            start = event.get("start_time", 0)
            end = event.get("end_time", start + 1)
            timeline_data.append(dict(
                Module="Visual QC", Start=start, Duration=(end - start),
                Status="WARNING", Details="Black Frame Detected"
            ))

    if not timeline_data:
        timeline_data.append(dict(
            Module="System Status", Start=0, Duration=video_duration, Status="PASSED", Details="Clean Video."
        ))

    # --- BUILD CHART ---
    df = pd.DataFrame(timeline_data)
    colors = {
        "REJECTED": "#EF553B",      # Red
        "CRITICAL": "#AB63FA",      # Purple
        "CRITICAL_FAIL": "#2A2A2A", # Black
        "WARNING": "#FFA15A",       # Orange
        "INFO": "#0078D7",          # Blue (Fixed/Text)
        "PASSED": "#00CC96"         # Green
    }

    fig = px.bar(
        df, base="Start", x="Duration", y="Module", color="Status",
        orientation='h', hover_data=["Details"],
        title=f"QC Analysis: {data.get('metadata',{}).get('filename', 'Video')}",
        color_discrete_map=colors
    )

    fig.update_layout(
        xaxis=dict(title="Timeline (Seconds)", type="linear"),
        yaxis=dict(autorange="reversed"),
        font=dict(family="Segoe UI", size=12)
    )

    try:
        os.makedirs(os.path.dirname(abs_output_path), exist_ok=True)
        fig.write_html(abs_output_path)
        print(f"[SUCCESS] Dashboard generated: {abs_output_path}")
    except Exception as e:
        print(f"[ERROR] Save failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    create_dashboard(args.input, args.output)