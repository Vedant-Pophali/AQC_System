import plotly.express as px
import json
import pandas as pd
import argparse
import os
import sys

# Force UTF-8
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

    # Get Duration (Fallback to 100s)
    video_duration = data.get("metadata", {}).get("duration", 0)
    if video_duration == 0: video_duration = 100

    modules = data.get("modules", {})

    # ================= MODULE VISUALIZATION LOGIC =================

    # 1. STRUCTURAL QC
    if "structure_qc" in modules:
        m = modules["structure_qc"]
        status = m.get("status")
        if status in ["REJECTED", "CRITICAL_FAIL"]:
            err = m.get("events", [{}])[0].get("error", "Corruption")
            timeline_data.append(dict(Module="Container Structure", Start=0, Duration=video_duration, Status="CRITICAL", Details=err))
        else:
            timeline_data.append(dict(Module="Container Structure", Start=0, Duration=video_duration, Status="PASSED", Details="Valid Structure"))
    # --- 1.10 ARTIFACTS (Gold) ---
    if "artifact_qc" in modules:
        m = modules["artifact_qc"]
        status = m.get("status")

        if status == "WARNING" or status == "REJECTED":
            # Extract first event detail
            detail = m.get("events", [{}])[0].get("details", "Quality Issues")
            timeline_data.append(dict(Module="Digital Quality", Start=0, Duration=video_duration, Status="WARNING", Details=detail))
        else:
            # Show the metrics in the success bar
            metrics = m.get("metrics", {})
            timeline_data.append(dict(
                Module="Digital Quality",
                Start=0,
                Duration=video_duration,
                Status="PASSED",
                Details=f"Crisp Image (Blur: {int(metrics.get('avg_blur',0))})"
            ))
    # 2. VISUAL QC
    if "visual_qc" in modules:
        m = modules["visual_qc"]
        events = m.get("events", [])
        if events:
            for e in events:
                timeline_data.append(dict(Module="Visual QC", Start=e.get("start_time", 0), Duration=e.get("end_time", 1)-e.get("start_time", 0), Status="WARNING", Details="Black Frame"))
        else:
            timeline_data.append(dict(Module="Visual QC", Start=0, Duration=video_duration, Status="PASSED", Details="No Visual Defects"))

    # 3. INTERLACE
    if "interlace_qc" in modules:
        m = modules["interlace_qc"]
        if m.get("status") == "REJECTED":
            ratio = m.get("metrics", {}).get("interlace_ratio", 0)
            timeline_data.append(dict(Module="Field Analysis", Start=0, Duration=video_duration, Status="WARNING", Details=f"Interlaced ({ratio*100:.1f}%)"))
        else:
            timeline_data.append(dict(Module="Field Analysis", Start=0, Duration=video_duration, Status="PASSED", Details="Progressive Scan"))

    # 4. AUDIO QC (Loudness) - UPDATED LOGIC
    if "audio_qc" in modules:
        m = modules["audio_qc"]
        correction = m.get("correction", {})
        is_fixed = correction.get("status") == "FIXED"
        events = m.get("events", [])

        # Logic: If REJECTED, show RED (even if fixed). Note the fix in the text.
        if m.get("status") == "REJECTED":
            for e in events:
                start = e.get("start_time", 0)
                end = e.get("end_time", video_duration)

                # Create detailed label
                details = f"{e['details'].get('measured_lufs')} LUFS"
                if is_fixed:
                    details += " (Auto-Fix Available)"

                timeline_data.append(dict(Module="Audio Loudness", Start=start, Duration=(end-start), Status="REJECTED", Details=details))
        else:
            timeline_data.append(dict(Module="Audio Loudness", Start=0, Duration=video_duration, Status="PASSED", Details="Loudness Compliant"))

    # 5. AUDIO SIGNAL
    if "audio_signal_qc" in modules:
        m = modules["audio_signal_qc"]
        if m.get("status") == "REJECTED":
            timeline_data.append(dict(Module="Audio Integrity", Start=0, Duration=video_duration, Status="REJECTED", Details="Distortion/Phase Error"))
        else:
            timeline_data.append(dict(Module="Audio Integrity", Start=0, Duration=video_duration, Status="PASSED", Details="Signal Clean"))

    # 6. QCTOOLS
    if "qctools_qc" in modules:
        m = modules["qctools_qc"]
        status = m.get("status")
        if status == "ERROR":
            timeline_data.append(dict(Module="Analog Artifacts", Start=0, Duration=video_duration, Status="CRITICAL", Details="Tool Failed (Binary Missing?)"))
        elif status == "WARNING" or status == "REJECTED":
            timeline_data.append(dict(Module="Analog Artifacts", Start=0, Duration=video_duration, Status="WARNING", Details=f"VREP Issues: {m.get('metrics',{}).get('bad_frames')} frames"))
        else:
            timeline_data.append(dict(Module="Analog Artifacts", Start=0, Duration=video_duration, Status="PASSED", Details="No Analog Artifacts"))

    # 7. SIGNAL QC
    if "signal_qc" in modules:
        m = modules["signal_qc"]
        if m.get("status") == "REJECTED":
            note = m.get("details", {}).get("note", "Limit Violation")
            timeline_data.append(dict(Module="Broadcast Safety", Start=0, Duration=video_duration, Status="CRITICAL", Details=note))
        else:
            timeline_data.append(dict(Module="Broadcast Safety", Start=0, Duration=video_duration, Status="PASSED", Details="Broadcast Safe"))

    # 8. OCR
    if "ocr_extraction" in modules:
        m = modules["ocr_extraction"]
        events = m.get("events", [])
        if events:
            for e in events:
                text = e['details'].get('text', '')[:30]
                timeline_data.append(dict(Module="Vernacular Text", Start=e.get("start_time"), Duration=2, Status="INFO", Details=f"Text: {text}..."))

    # ================= PLOTTING =================

    df = pd.DataFrame(timeline_data)

    # Define Colors
    colors = {
        "PASSED":   "#00CC96",  # Green
        "INFO":     "#636EFA",  # Blue (Text)
        "WARNING":  "#FFA15A",  # Orange
        "REJECTED": "#EF553B",  # Red (Now used for Audio Fail even if fixed)
        "CRITICAL": "#AB63FA",  # Purple
        "CRITICAL_FAIL": "#191919" # Black
    }

    if df.empty:
        df = pd.DataFrame([dict(Module="System", Start=0, Duration=video_duration, Status="INFO", Details="No Data")])

    fig = px.bar(
        df, base="Start", x="Duration", y="Module", color="Status",
        orientation='h', hover_data=["Details"],
        title=f"QC Analysis: {data.get('metadata',{}).get('filename', 'Video')}",
        color_discrete_map=colors
    )

    fig.update_layout(
        xaxis=dict(title="Timeline (Seconds)", type="linear"),
        yaxis=dict(
            autorange="reversed",
            automargin=True,
            title=None
        ),
        margin=dict(l=150),
        font=dict(family="Segoe UI", size=12),
        height=400 + (len(df['Module'].unique()) * 30)
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