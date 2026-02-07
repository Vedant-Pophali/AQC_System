import argparse
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import logging

# Fix path to include src to find report_lib
sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.postprocess.report_lib import ReportStandardizer, TimecodeHelper

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("visualize_report")

def format_time(seconds):
    return TimecodeHelper.seconds_to_smpte(seconds, fps=24) # Defaulting to 24fps for display

def create_interactive_dashboard(report_path, output_path):
    logger.info(f"Generating dashboard from: {report_path}")
    
    standardizer = ReportStandardizer()
    data = standardizer.load_report(report_path)
    
    if not data:
        logger.error("No data found in report")
        return

    # Extract filename
    input_filename = "video.mp4" 
    try:
        if "modules" in data:
            for mod in data["modules"].values():
                if "video_file" in mod:
                    input_filename = Path(mod["video_file"]).name
                    break
    except: pass

    # Prepare DataFrame using Standardizer
    events = data.get("aggregated_events", [])
    std_events = []
    
    for evt in events:
        std = standardizer.normalize_event(evt)
        flat = {
            "start_time": evt.get("start_time", 0.0),
            "end_time": evt.get("end_time", 0.0),
            "original_type": evt.get("type", "unknown"),
            "details": evt.get("details", ""),
            "origin_module": evt.get("origin_module", evt.get("source_module", "")),
            **std
        }
        std_events.append(flat)

    df = pd.DataFrame(std_events)
    
    if df.empty:
        # Create empty DF with required columns
        df = pd.DataFrame(columns=["start_time", "end_time", "category", "human_name", "severity_score", "color", "details", "original_type"])

    # Duration Calculation
    df["duration"] = df["end_time"] - df["start_time"]
    # Viz duration: Ensure single-frame events are visible
    df["viz_duration"] = df["duration"].apply(lambda x: 0.5 if x <= 0 else x)

    # --- 1. GENERATE SMART SUMMARY HTML ---
    summary_html = ""
    if not df.empty:
        # Group by error type
        grouped = df.groupby("human_name")
        summary_items = []
        
        for name, group in grouped:
            count = len(group)
            severity_score = group["severity_score"].max()
            category = group["category"].iloc[0]
            
            # Formatting
            is_fail = severity_score >= 3 # Moderate or higher
            color_class = "text-danger" if is_fail else "text-warning"
            icon = "❌" if is_fail else "⚠️"
            if severity_score == 0:
                color_class = "text-success"
                icon = "✅"
            
            # Time stamps
            timestamps = []
            for _, row in group.sort_values("start_time").head(3).iterrows():
                start = format_time(row["start_time"])
                timestamps.append(start)
            
            time_str = ", ".join(timestamps)
            if count > 3: time_str += f" (+{count-3} more)"
            
            summary_items.append(
                f"""
                <li class="summary-item" data-category="{category}" data-severity="{severity_score}">
                    <div class="summary-header">
                        <span class="{color_class}"><strong>{icon} {name}</strong> ({count})</span>
                        <span class="timestamp-badge">{time_str}</span>
                    </div>
                </li>
                """
            )
        
        summary_html = f"""
        <div class="summary-box">
            <h3>Human Readable Summary</h3>
            <ul style="padding:0; margin:0;" id="summary-list">
                {"".join(summary_items)}
            </ul>
        </div>
        """
    else:
         summary_html = """
        <div class="summary-box" style="border-left: 5px solid #2ca02c;">
            <h3>✅ Perfect File</h3>
            <p>No defects were detected.</p>
        </div>
        """

    # --- 2. BUILD PLOTLY CHART ---
    # Define Subplots: Main Timeline, Severity Heatmap
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.1,
        row_heights=[0.7, 0.3],
        subplot_titles=("Defect Timeline (Click to Seek)", "Severity Heatmap")
    )

    # Stacked Bar Chart for Events
    categories = sorted(df["category"].unique()) if not df.empty else []
    
    for cat in categories:
        subset = df[df["category"] == cat]
        color = subset["color"].iloc[0] if not subset.empty else "#999999"
        
        fig.add_trace(go.Bar(
            base=subset["start_time"],
            x=subset["viz_duration"],
            y=[cat] * len(subset),
            orientation='h',
            name=cat,
            legendgroup=cat,
            marker=dict(color=color, line=dict(color='rgba(255,255,255,0.2)', width=1)),
            customdata=np.stack((subset['details'], subset['human_name']), axis=-1),
            hovertemplate=(
                "<b>%{customdata[1]}</b><br>" +
                "Start: %{base:.2f}s<br>" +
                "Dur: %{x:.2f}s<br>" +
                "Details: %{customdata[0]}<extra></extra>"
            )
        ), row=1, col=1)

    # Heatmap Calculation
    if not df.empty:
        max_time = df["end_time"].max()
        if max_time <= 0: max_time = 10
        bins = np.arange(0, int(max_time) + 2, 1)
        hist_y = np.zeros(len(bins)-1)
        
        for _, row in df.iterrows():
            s = int(row["start_time"])
            e = int(row["end_time"])
            score = row["severity_score"]
            
            s = max(0, min(s, len(hist_y)-1))
            e = max(0, min(e, len(hist_y)-1))
            
            val_to_set = max(1, score) # Ensure even mild errors show up
            
            if s == e:
                hist_y[s] = max(hist_y[s], val_to_set)
            else:
                for t in range(s, e + 1):
                    if t < len(hist_y):
                        hist_y[t] = max(hist_y[t], val_to_set)

        fig.add_trace(go.Heatmap(
            z=[hist_y], 
            x=bins[:-1], 
            y=["Risk Level"], 
            colorscale=[[0, "#1a1a1a"], [0.2, "#2ecc71"], [0.5, "#f1c40f"], [1.0, "#d32f2f"]],
            showscale=False, 
            name="Risk Level"
        ), row=2, col=1)

    # Update Layout
    fig.update_layout(
        template="plotly_dark",
        height=700,
        margin=dict(t=30, b=30, l=150), # More left margin for category labels
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="closest"
    )
    
    # Add Updatemenus for Filtering
    fig.update_layout(
        updatemenus=[
            dict(
                type="dropdown",
                direction="down",
                x=0.0,
                y=1.15,
                showactive=True,
                buttons=list([
                    dict(label="All Categories",
                         method="update",
                         args=[{"visible": [True] * len(fig.data)},
                               {"title": "All Events"}]),
                ] + [
                    dict(label=cat,
                         method="update",
                         args=[{"visible": [trace.name == cat or trace.name == "Risk Level" for trace in fig.data]},
                               {"title": f"{cat} Events"}])
                    for cat in categories
                ])
            )
        ]
    )

    plot_div = fig.to_html(full_html=False, include_plotlyjs='cdn')

    # --- 4. ASSEMBLE HTML ---
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>AQC Report: {input_filename}</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #121212; color: #e0e0e0; margin: 0; padding: 20px; }}
            .container {{ max_width: 1400px; margin: 0 auto; display: grid; grid-template-columns: 1fr 350px; gap: 20px; }}
            
            .header {{ grid-column: 1 / -1; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333; padding-bottom: 20px; margin-bottom: 20px; }}
            .status-badge {{ padding: 8px 20px; border-radius: 4px; font-weight: bold; font-size: 1.5em; text-transform: uppercase; color: white; }}
            
            .main-content {{ grid-column: 1; }}
            .sidebar {{ grid-column: 2; }}

            .summary-box {{ background-color: #1e1e1e; padding: 20px; margin-bottom: 20px; border-radius: 6px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); max-height: 800px; overflow-y: auto; }}
            .summary-item {{ list-style: none; border-bottom: 1px solid #333; padding: 10px 0; cursor: pointer; transition: background 0.2s; }}
            .summary-item:hover {{ background: #2a2a2a; }}
            
            .timestamp-badge {{ background: #333; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; color: #bbb; font-family: monospace; float: right; }}
            
            .text-danger {{ color: #ff5252; }}
            .text-warning {{ color: #ffb74d; }}
            .text-success {{ color: #2ecc71; }}

            .video-box {{ background: #000; margin-bottom: 20px; text-align: center; border: 1px solid #333; }}
            video {{ width: 100%; max-height: 500px; outline: none; }}
            
            .REJECTED {{ background-color: #d32f2f; }}
            .WARNING {{ background-color: #f57c00; }}
            .PASSED {{ background-color: #388e3c; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h1 style="margin:0">AQC Analysis Report</h1>
                    <h3 style="margin:5px 0; color: #aaa;">File: {input_filename}</h3>
                </div>
                <div class="status-badge {data.get('overall_status', 'UNKNOWN')}">
                    {data.get('overall_status', 'UNKNOWN')}
                </div>
            </div>

            <div class="main-content">
                <div class="video-box">
                    <video id="qc-player" controls>
                        <source src="video" type="video/mp4">
                        <p style="color:white; padding:20px;">Video not found.</p>
                    </video>
                </div>

                <div id="chart-container">
                    {plot_div}
                </div>
            </div>
            
            <div class="sidebar">
                {summary_html}
                
                <div class="summary-box">
                    <h3>Controls</h3>
                    <p>Click on the chart timeline to jump to that timestamp in the video.</p>
                    <button onclick="document.getElementById('qc-player').playbackRate = 1.0">1x Speed</button>
                    <button onclick="document.getElementById('qc-player').playbackRate = 2.0">2x Speed</button>
                </div>
            </div>
            
            <script>
                var checkPlotly = setInterval(function() {{
                    if (window.Plotly) {{
                        clearInterval(checkPlotly);
                        setupInteraction();
                    }}
                }}, 100);

                function setupInteraction() {{
                    var graphDiv = document.getElementsByClassName('plotly-graph-div')[0];
                    var video = document.getElementById('qc-player');
                    
                    if (graphDiv) {{
                        graphDiv.on('plotly_click', function(data){{
                            if(data.points.length > 0){{
                                var pt = data.points[0];
                                var clickTime = (pt.base !== undefined) ? pt.base : pt.x;
                                if (clickTime !== undefined) {{
                                    video.currentTime = clickTime;
                                    video.play();
                                }}
                            }}
                        }});
                    }}
                }}
            </script>
        </div>
    </body>
    </html>
    """
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    logger.info(f"Dashboard generated: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    create_interactive_dashboard(args.input, args.output)