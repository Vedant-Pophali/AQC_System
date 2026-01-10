import json
import argparse
import os
import sys
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import timedelta

# UTF-8 safety (Windows)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

def load_report(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def format_time(seconds):
    return str(timedelta(seconds=round(seconds)))

def visualize_report(input_path, output_path):
    data = load_report(input_path)

    # Extract Metadata
    overall_status = data.get("overall_status", "UNKNOWN")
    modules = data.get("modules", {})
    
    print(f"Generating Dashboard for: {overall_status}")

    # -----------------------------------
    # 1. Prepare Data for Visualization
    # -----------------------------------
    
    # METRICS TABLE DATA
    metric_rows = []
    
    # A. Structure
    struct = modules.get("validate_structure", {}).get("details", {})
    if struct:
        metric_rows.append(["Structure", "Container", struct.get("container", "N/A")])
        metric_rows.append(["Structure", "Duration", f"{struct.get('duration', 0)}s"])
        
        # Video Stream Details
        v_streams = struct.get("video_streams", [])
        if v_streams:
            v = v_streams[0]
            metric_rows.append(["Video", "Codec", v.get("codec", "N/A")])
            metric_rows.append(["Video", "Resolution", f"{v.get('width')}x{v.get('height')}"])
    
    # B. Loudness
    loud = modules.get("validate_loudness", {}).get("details", {})
    if loud:
        status = modules.get("validate_loudness", {}).get("effective_status", "")
        val = f"{loud.get('integrated_lufs', 0)} LUFS"
        if status != "PASSED": val += " ❌"
        metric_rows.append(["Audio", "Integrated Loudness", val])
        metric_rows.append(["Audio", "True Peak", f"{loud.get('true_peak', 0)} dBTP"])

    # C. AV Sync
    sync = modules.get("validate_avsync", {}).get("details", {})
    sync_offset = 0
    if sync:
        sync_offset = sync.get("offset_ms", 0)
        status = modules.get("validate_avsync", {}).get("effective_status", "")
        val = f"{sync_offset} ms"
        if status != "PASSED": val += " ⚠️"
        metric_rows.append(["Sync", "AV Offset", val])
        metric_rows.append(["Sync", "Confidence", sync.get("confidence_score", "N/A")])

    # -----------------------------------
    # 2. Build Dashboard (Plotly)
    # -----------------------------------

    # Create Subplots: 1. Sync Gauge/Timeline, 2. Metrics Table
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.3, 0.7],
        specs=[[{"type": "xy"}], [{"type": "table"}]],
        subplot_titles=("A/V Sync Offset Visualization", "QC Metrics Summary")
    )

    # --- A. Sync Visualization (Bar Chart) ---
    # We visualize the offset relative to "0" (Perfect Sync)
    color = "green" if abs(sync_offset) <= 40 else "red"
    
    fig.add_trace(
        go.Bar(
            x=[sync_offset],
            y=["A/V Sync"],
            orientation='h',
            marker=dict(color=color),
            text=[f"{sync_offset} ms"],
            textposition='auto',
            name="Sync Offset"
        ),
        row=1, col=1
    )
    
    # Add tolerance lines (+/- 40ms)
    fig.add_vline(x=40, line_width=1, line_dash="dash", line_color="gray", row=1, col=1)
    fig.add_vline(x=-40, line_width=1, line_dash="dash", line_color="gray", row=1, col=1)
    fig.update_xaxes(title_text="Offset (milliseconds) - Positive = Video Ahead", row=1, col=1)

    # --- B. Metrics Table ---
    if metric_rows:
        headers = ["Category", "Metric", "Value"]
        cell_values = list(map(list, zip(*metric_rows))) # Transpose

        fig.add_trace(
            go.Table(
                header=dict(values=headers, fill_color='paleturquoise', align='left', font=dict(size=14, color='black')),
                cells=dict(values=cell_values, fill_color='lavender', align='left', font=dict(size=12, color='black'), height=30)
            ),
            row=2, col=1
        )

    # -----------------------------------
    # 3. Layout Styling
    # -----------------------------------
    status_color = "green" if overall_status == "PASSED" else "red"
    if overall_status == "WARNING": status_color = "orange"

    fig.update_layout(
        title_text=f"<b>AQC Master Report</b> | Status: <span style='color:{status_color}'>{overall_status}</span>",
        height=800,
        showlegend=False,
        template="plotly_white"
    )

    # -----------------------------------
    # 4. Save to HTML
    # -----------------------------------
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.write_html(output_path)
    print(f" [INFO] Dashboard generated: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Interactive QC Dashboard")
    parser.add_argument("--input", required=True, help="Path to Master_Report.json")
    parser.add_argument("--output", required=True, help="Path to dashboard.html")
    args = parser.parse_args()

    visualize_report(args.input, args.output)