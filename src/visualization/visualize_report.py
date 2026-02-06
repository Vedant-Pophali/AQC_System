import argparse
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from pathlib import Path
import html
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("visualize_report")

# --- 1. INTELLIGENT REMEDIATION DICTIONARY ---
# Maps errors to: (Human Name, Actionable Advice)
ERROR_KNOWLEDGE_BASE = {
    # Archival (NEW)
    "broadcast_illegal": ("Broadcast Legal Violation", "Video levels exceed 16-235 range. Apply a 'Broadcast Safe' filter or color grade."),
    "saturation_warning": ("Oversaturation", "Chroma levels are too high. Desaturate or check gamut-limiting."),

    # Audio
    "loudness_check": ("Audio Loudness Violation", "Apply a transparent limiter or normalizer to hit target LUFS."),
    "loudness_compliance_failed": ("Loudness Standard Fail", "Re-mix audio to EBU R128 (-23 LUFS) or YouTube (-14 LUFS) standards."),
    "true_peak_violation": ("Audio Clipping", "Lower the master gain or use a True Peak Limiter to prevent distortion."),
    "phase_inversion_detected": ("Phase Cancellation", "Check stereo width plugins or flip the phase on one channel."),
    "audio_dropout": ("Audio Dropout", "Check source audio tracks for gaps or corrupt cross-fades."),
    "validate_phase": ("Audio Phase Compliance", "Detected out-of-phase audio. Check stereo width or flip phase on one channel."),
    # Video Errors
    "black_frame_detected": ("Unexpected Black Frames", "Remove the gap in your timeline or add a cross-dissolve."),
    "freeze_frame_detected": ("Frozen Video", "Check your export settings or replace the corrupt clip."),
    "letterbox_detected": ("Letterboxing", "Scale video to fill frame or check sequence settings."),
    "interlace_artifact": ("Interlacing Lines", "Apply a de-interlace filter or check field-order settings."),
    "high_noise_detected": ("Analog Noise", "Apply de-noising filters or check cable connections."),
    
    # ML Artifacts (NEW)
    "compression_artifact_ml": ("Compression Artifacts (ML)", "Re-encode at a higher bitrate or use a slower encoding preset (slow/veryslow)."),
    "bitrate_starvation": ("Critical Bitrate Low", "The file bitrate is too low for this resolution. Re-export at a higher Mbps."),

    # Metadata & Sync
    "missing_metadata": ("Missing Metadata", "Re-encode and ensure language tags/headers are set in export."),
    "avsync_error": ("Lip-Sync Drift", "Slip the audio track by the detected offset amount.")
}

def load_master_report(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load report: {e}")
        return {}

def format_time(seconds):
    """Converts seconds to MM:SS format"""
    m, s = divmod(seconds, 60)
    return f"{int(m):02d}:{int(s):02d}"

def create_interactive_dashboard(report_path, output_path):
    logger.info(f"Generating dashboard from: {report_path}")
    data = load_master_report(report_path)
    
    events = data.get("aggregated_events", [])
    
    # Extract filename
    input_filename = "video.mp4" 
    try:
        # Try to find the filename from the first module that has it
        if "modules" in data:
            for mod in data["modules"].values():
                if "video_file" in mod:
                    input_filename = Path(mod["video_file"]).name
                    break
    except: pass

    # DataFrame Setup
    df = pd.DataFrame(events)
    if df.empty:
        df = pd.DataFrame(columns=["start_time", "end_time", "type", "details", "severity", "origin_module"])

    # Sanitize Data
    for col in ["start_time", "end_time"]:
        if col not in df.columns: df[col] = 0.0
    
    df["start_time"] = df["start_time"].fillna(0.0)
    df["end_time"] = df["end_time"].fillna(0.0)
    df["severity"] = df["severity"].fillna("UNKNOWN")
    df["type"] = df["type"].fillna("general_error")

    # Categorize
    def get_category(row):
        mod = str(row.get("origin_module", "")).lower()
        evt = str(row.get("type", "")).lower()
        details = str(row.get("details", "")).lower()
        
        # ML Artifacts (NEW LOGIC)
        if "artifact" in evt or "bitrate" in evt or "block" in details: return "Video Quality"
        if "black" in evt or "freeze" in evt or "interlace" in evt: return "Video Error"
        
        # Archival Signal (NEW)
        if "broadcast" in evt or "saturation" in evt or "luma" in details: return "Archival"
        
        if "audio" in mod or "loudness" in mod or "silence" in evt: return "Audio"
        if "sync" in mod or "drift" in evt: return "Sync"
        if "structure" in mod: return "Structure"
        
        return "Video" # Fallback

    df["category"] = df.apply(get_category, axis=1)
    df["duration"] = df["end_time"] - df["start_time"]
    # Viz duration: Ensure single-frame events are visible (at least 0.5s width)
    df["viz_duration"] = df["duration"].apply(lambda x: 0.5 if x <= 0 else x)
    
    # Severity Mapping for Heatmap (Updated for ML severities)
    severity_map = {
        "CRITICAL": 5, 
        "REJECTED": 5, 
        "SEVERE": 5,    # New ML
        "MODERATE": 3,  # New ML
        "WARNING": 2, 
        "MILD": 1,      # New ML
        "PASSED": 0, 
        "UNKNOWN": 1
    }
    df["risk_score"] = df["severity"].map(severity_map).fillna(1)

    # --- 2. GENERATE SMART SUMMARY HTML ---
    summary_html = ""
    if not df.empty:
        # Group by error type to avoid duplicates in summary
        error_types = df["type"].unique()
        summary_items = []
        
        for err_type in error_types:
            subset = df[df["type"] == err_type]
            count = len(subset)
            severity = subset["severity"].iloc[0]
            
            # Get Knowledge Base Info
            default_name = err_type.replace("_", " ").title()
            human_name, fix_advice = ERROR_KNOWLEDGE_BASE.get(err_type, (default_name, "Review manual check required."))
            
            # Get Timestamps (First 3 occurrences)
            timestamps = []
            for _, row in subset.sort_values("start_time").head(3).iterrows():
                start = format_time(row["start_time"])
                end = format_time(row["end_time"])
                if row["duration"] < 1:
                    timestamps.append(f"@{start}")
                else:
                    timestamps.append(f"{start}-{end}")
            
            time_str = ", ".join(timestamps)
            if count > 3: time_str += f" (+{count-3} more)"
            
            # Styling
            is_fail = severity in ["CRITICAL", "REJECTED", "SEVERE"]
            color_class = "text-danger" if is_fail else "text-warning"
            icon = "❌" if is_fail else "⚠️"
            
            summary_items.append(
                f"""
                <li class="summary-item">
                    <div class="summary-header">
                        <span class="{color_class}"><strong>{icon} {human_name}</strong></span>
                        <span class="timestamp-badge">{time_str}</span>
                    </div>
                    <div class="fix-advice">💡 <strong>Fix:</strong> {fix_advice}</div>
                </li>
                """
            )
        
        summary_html = f"""
        <div class="summary-box">
            <h3>Human Readable Summary</h3>
            <ul style="padding:0; margin:0;">
                {"".join(summary_items)}
            </ul>
        </div>
        """
    else:
         summary_html = """
        <div class="summary-box" style="border-left: 5px solid #2ca02c;">
            <h3>✅ Perfect File</h3>
            <p>No defects were detected. This video is ready for broadcast.</p>
        </div>
        """

    # --- 3. BUILD PLOTLY CHART ---
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.1,
        row_heights=[0.75, 0.25],
        subplot_titles=("Defect Timeline (Click to Seek Video)", "Severity Heatmap")
    )

    # Define Colors
    colors = {
        "Audio": "#1f77b4",         # Blue
        "Video Error": "#d62728",   # Red
        "Video Quality": "#ff7f0e", # Orange (ML Artifacts)
        "Archival": "#00bcd4",      # Cyan (NEW)
        "Sync": "#2ca02c",          # Green
        "Structure": "#9467bd",     # Purple
        "Video": "#7f7f7f"          # Grey (Default)
    }
    
    # Stacked Bar Chart for Events
    for cat in df["category"].unique():
        subset = df[df["category"] == cat]
        fig.add_trace(go.Bar(
            base=subset["start_time"],
            x=subset["viz_duration"],
            y=[cat] * len(subset),
            orientation='h',
            name=cat,
            legendgroup=cat,
            marker=dict(color=colors.get(cat, "#999999")),
            customdata=np.stack((subset['details'], subset['severity']), axis=-1),
            hovertemplate="<b>%{y}</b><br>Start: %{base:.2f}s<br>Dur: %{x:.2f}s<br>Sev: %{customdata[1]}<br>Err: %{customdata[0]}<extra></extra>"
        ), row=1, col=1)

    # Heatmap Calculation
    if not df.empty:
        max_time = df["end_time"].max()
        if max_time <= 0: max_time = 10
        # Create bins every 1 second
        bins = np.arange(0, int(max_time) + 5, 1)
        hist_y = np.zeros(len(bins)-1)
        
        for _, row in df.iterrows():
            # Add risk score to all seconds covered by the event
            s = int(row["start_time"])
            e = int(row["end_time"])
            score = row["risk_score"]
            
            # Clamp to array bounds
            s = max(0, min(s, len(hist_y)-1))
            e = max(0, min(e, len(hist_y)-1))
            
            # For single frame events, mark at least one second
            if s == e:
                hist_y[s] = max(hist_y[s], score)
            else:
                for t in range(s, e + 1):
                    if t < len(hist_y):
                        hist_y[t] = max(hist_y[t], score)

        fig.add_trace(go.Heatmap(
            z=[hist_y], 
            x=bins[:-1], 
            y=["Risk Level"], 
            colorscale=[[0, "#1a1a1a"], [0.2, "#2ecc71"], [0.5, "#f1c40f"], [1.0, "#e74c3c"]],
            showscale=False, 
            name="Risk Level"
        ), row=2, col=1)

    fig.update_layout(
        title="", 
        template="plotly_dark", 
        height=650, 
        margin=dict(t=30, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    plot_div = fig.to_html(full_html=False, include_plotlyjs='cdn')

    # --- 4. TECHNICAL COMPLIANCE TABLE ---
    compliance_html = ""
    modules = data.get("modules", {})
    if modules:
        rows = []
        for mod_name, mod_data in modules.items():
            # Combine details and metrics for unified lookup
            all_data = {**mod_data.get("details", {}), **mod_data.get("metrics", {})}
            
            if "mean_phase_correlation" in all_data:
                mean_p = all_data["mean_phase_correlation"]
                min_p = all_data["min_phase_correlation"]
                status = mod_data.get("status", "PASSED")
                rows.append(f"""
                    <tr>
                        <td>Audio Phase Correlation</td>
                        <td>{mean_p} (Mean) / {min_p} (Min)</td>
                        <td class="{status}">{status}</td>
                    </tr>
                """)
            if "integrated_lufs" in all_data:
                loud = all_data["integrated_lufs"]
                tp = all_data.get("true_peak", "N/A")
                status = mod_data.get("status", "PASSED")
                rows.append(f"""
                    <tr>
                        <td>Loudness / True Peak</td>
                        <td>{loud} LUFS / {tp} dBTP</td>
                        <td class="{status}">{status}</td>
                    </tr>
                """)

        if rows:
            compliance_html = f"""
            <div class="summary-box" style="border-left: 5px solid #3498db;">
                <h3>Technical Compliance</h3>
                <table style="width:100%; text-align:left; border-collapse: collapse;">
                    <tr style="border-bottom: 1px solid #444;">
                        <th style="padding:10px;">Parameter</th>
                        <th style="padding:10px;">Value</th>
                        <th style="padding:10px;">Status</th>
                    </tr>
                    {"".join(rows)}
                </table>
            </div>
            """

    # --- 5. ASSEMBLE HTML ---
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>AQC Report: {input_filename}</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #121212; color: #e0e0e0; margin: 0; padding: 20px; }}
            .container {{ max_width: 1200px; margin: 0 auto; }}
            
            .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333; padding-bottom: 20px; margin-bottom: 20px; }}
            .status-badge {{ padding: 8px 20px; border-radius: 4px; font-weight: bold; font-size: 1.5em; text-transform: uppercase; color: white; }}
            .REJECTED {{ background-color: #d32f2f; box-shadow: 0 0 15px #d32f2f; }}
            .WARNING {{ background-color: #f57c00; }}
            .PASSED {{ background-color: #388e3c; }}

            .summary-box {{ background-color: #1e1e1e; border-left: 5px solid #d32f2f; padding: 20px; margin-bottom: 25px; border-radius: 6px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
            .summary-item {{ list-style: none; border-bottom: 1px solid #333; padding: 12px 0; }}
            .summary-item:last-child {{ border-bottom: none; }}
            
            .summary-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; }}
            .timestamp-badge {{ background: #333; padding: 2px 8px; border-radius: 10px; font-size: 0.9em; color: #bbb; font-family: monospace; }}
            .fix-advice {{ color: #aaa; font-style: italic; margin-left: 25px; font-size: 0.95em; }}
            
            .text-danger {{ color: #ff5252; font-size: 1.1em; }}
            .text-warning {{ color: #ffb74d; font-size: 1.1em; }}

            .video-box {{ background: #000; margin-bottom: 20px; text-align: center; border: 1px solid #333; }}
            video {{ width: 100%; max-height: 450px; outline: none; }}
            
            #chart-container {{ min-height: 650px; }}
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

            {summary_html}
            {compliance_html}

            <div class="video-box">
                <video id="qc-player" controls>
                    <source src="video" type="video/mp4">
                    <p style="color:white; padding:20px;">Video not found or incompatible format.</p>
                </video>
            </div>

            <div id="chart-container">
                {plot_div}
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