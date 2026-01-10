import json
import argparse
import os
import sys
import plotly.graph_objects as go
import plotly.express as px
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
    metadata = data.get("metadata", {})
    overall_status = data.get("overall_status", "UNKNOWN")
    modules = data.get("modules", {})

    # -----------------------------------
    # 1. Prepare Event Data for Timeline
    # -----------------------------------
    events_list = []

    # Color mapping for severity/types
    color_map = {
        "visual_defect": "red",
        "audio_signal_defect": "orange",
        "loudness_failure": "orange",
        "interlace_flagged": "yellow",
        "container_mismatch": "purple",
        "analog_artifact_vrep": "magenta",
        "compression_artifact": "pink"
    }

    # Iterate through all modules and collect events
    for module_name, module_data in modules.items():
        module_events = module_data.get("events", [])

        for event in module_events:
            e_type = event.get("type", "unknown")
            e_sub = event.get("subtype", e_type)
            start = event.get("start_time", 0.0)
            end = event.get("end_time", start + 1.0) # Default 1s duration if point event
            details = event.get("details", "")

            # If start/end are 0.0 and it's a file-level error (like container mismatch),
            # we might want to show it across the whole timeline or as a distinct marker.
            # For visualization, we'll cap it at 10s or logical duration if available.

            events_list.append({
                "Module": module_name,
                "Type": e_sub,
                "Start": start,
                "End": end,
                "Duration": end - start,
                "Details": details,
                "Color": color_map.get(e_type, "gray")
            })

    # -----------------------------------
    # 2. Build Dashboard (Plotly)
    # -----------------------------------

    # Create Subplots: 1. Timeline, 2. Metrics Table
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.6, 0.4],
        specs=[[{"type": "xy"}], [{"type": "table"}]],
        subplot_titles=("Defect Timeline", "QC Metrics Summary")
    )

    # --- A. Timeline Chart ---
    if events_list:
        df = pd.DataFrame(events_list)

        # We use a custom Gantt-like approach using Bar charts
        for i, row in df.iterrows():
            fig.add_trace(
                go.Bar(
                    x=[row["Duration"]],
                    y=[row["Module"]],
                    base=[row["Start"]],
                    orientation='h',
                    name=row["Type"],
                    marker=dict(color=row["Color"]),
                    hovertext=f"<b>{row['Type']}</b><br>Time: {format_time(row['Start'])} - {format_time(row['End'])}<br>{row['Details']}",
                    hoverinfo="text"
                ),
                row=1, col=1
            )
    else:
        # Placeholder if passed perfectly
        fig.add_annotation(
            text="No Defects Detected - Clean Asset",
            xref="paper", yref="paper",
            x=0.5, y=0.8, showarrow=False,
            font=dict(size=20, color="green")
        )

    # --- B. Metrics Table ---
    # Gather key metrics from modules
    metric_rows = []

    # Structure
    struc = modules.get("structure_qc", {}).get("metrics", {})
    if struc:
        metric_rows.append(["Structure", "Container", struc.get("container", "N/A")])
        metric_rows.append(["Structure", "Resolution", struc.get("resolution", "N/A")])
        metric_rows.append(["Structure", "Audio Channels", struc.get("channels", "N/A")])

    # Loudness
    aud = modules.get("audio_qc", {}).get("metrics", {})
    if aud:
        metric_rows.append(["Audio", "Integrated Loudness", f"{aud.get('integrated_lufs', 0):.2f} LUFS"])
        metric_rows.append(["Audio", "True Peak", f"{aud.get('true_peak_db', 0):.2f} dBTP"])

    # Artifacts
    art = modules.get("artifact_qc", {}).get("metrics", {})
    if art:
        metric_rows.append(["Video", "Avg Blockiness", f"{art.get('blockiness', {}).get('mean', 0):.4f}"])

    # Interlace
    intl = modules.get("interlace_qc", {}).get("metrics", {})
    if intl:
        metric_rows.append(["Video", "Field PSNR", f"{intl.get('field_psnr_avg', 0):.2f} dB"])

    if metric_rows:
        headers = ["Category", "Metric", "Value"]
        # Transpose for Plotly Table
        cell_values = list(map(list, zip(*metric_rows)))

        fig.add_trace(
            go.Table(
                header=dict(values=headers, fill_color='paleturquoise', align='left'),
                cells=dict(values=cell_values, fill_color='lavender', align='left')
            ),
            row=2, col=1
        )

    # -----------------------------------
    # 3. Layout Styling
    # -----------------------------------
    status_color = "green" if overall_status == "PASSED" else "red"

    fig.update_layout(
        title_text=f"AQC Master Report | Status: <span style='color:{status_color}'>{overall_status}</span> | Profile: {metadata.get('profile', 'N/A')}",
        height=800,
        showlegend=False, # Legend can be cluttered with many events
        xaxis=dict(title="Timeline (Seconds)", type="linear"),
        yaxis=dict(title="Module", type="category")
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