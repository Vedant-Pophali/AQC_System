import streamlit as st
import subprocess
import sys
import os
import shutil
import json
import time
from pathlib import Path

# Page Config
st.set_page_config(page_title="AQC System", layout="wide", page_icon="🎬")

# Title & Header
st.title("🎬 Automated Quality Control (AQC)")
st.markdown("### Open-Source Video Analysis System")

# Sidebar settings
with st.sidebar:
    st.header("Settings")
    mode = st.radio("QC Profile", ["strict", "ott"], help="Strict = Broadcast TV specs. OTT = Web specs.")
    fix_audio = st.checkbox("Auto-Fix Loudness", value=False, help="Attempt to repair audio levels automatically.")
    
    st.divider()
    st.info("System Ready")

# -------------------------------------------------
# 1. DRAG & DROP AREA
# -------------------------------------------------
uploaded_file = st.file_uploader("Drop a video file here to analyze", type=['mp4', 'mov', 'mkv', 'avi'])

if uploaded_file is not None:
    # -------------------------------------------------
    # 2. SAVE FILE TEMPORARILY
    # -------------------------------------------------
    temp_dir = Path("temp_upload")
    temp_dir.mkdir(exist_ok=True)
    
    file_path = temp_dir / uploaded_file.name
    
    # Write the uploaded bytes to disk so ffmpeg can read it
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
        
    st.success(f"File uploaded: {uploaded_file.name}")
    
    # -------------------------------------------------
    # 3. RUN AQC BUTTON
    # -------------------------------------------------
    if st.button("🚀 Run Quality Control"):
        output_dir = Path("reports") / f"gui_{int(time.time())}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Display a progress spinner
        with st.spinner('Running AI Analysis... (This may take a moment)'):
            
            # Construct command to run src/main.py
            cmd = [
                sys.executable, "src/main.py",
                "--input", str(file_path),
                "--outdir", str(output_dir),
                "--mode", mode
            ]
            if fix_audio:
                cmd.append("--fix")
            
            # Run the actual pipeline
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            
        # -------------------------------------------------
        # 4. DISPLAY RESULTS
        # -------------------------------------------------
        if process.returncode == 0:
            st.success("Analysis Complete!")
            
            # Tabs for different views
            tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📝 Raw Report", "⚙️ Logs"])
            
            # TAB 1: The Graphical Dashboard
            dashboard_path = output_dir / "dashboard.html"
            if dashboard_path.exists():
                with tab1:
                    st.header("Interactive QC Timeline")
                    with open(dashboard_path, 'r', encoding='utf-8') as f:
                        html_data = f.read()
                    st.components.v1.html(html_data, height=800, scrolling=True)
            
            # TAB 2: The JSON Data
            report_path = output_dir / "Master_Report.json"
            if report_path.exists():
                with tab2:
                    st.header("Master QC Report")
                    with open(report_path, 'r') as f:
                        json_data = json.load(f)
                    st.json(json_data)
                    
                    # Highlight Status
                    status = json_data.get("overall_status", "UNKNOWN")
                    if status == "PASSED":
                        st.balloons()
                    elif status == "REJECTED":
                        st.error("QC FAILED: File Rejected")
                    else:
                        st.warning(f"QC Completed with {status}")

            # TAB 3: System Logs
            with tab3:
                st.text_area("Console Output", process.stdout, height=300)

        else:
            st.error("Analysis Failed!")
            st.text_area("Error Log", process.stderr, height=300)

    # Cleanup Button
    if st.button("Clear Temp Files"):
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        st.experimental_rerun()