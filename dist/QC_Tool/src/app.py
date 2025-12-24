import streamlit as st
import subprocess
import os
import shutil
import json
import time
from visualize_report import create_dashboard

# Page Config
st.set_page_config(page_title="Automated QC Tool", page_icon="🎬", layout="wide")

st.title("🎬 Automated Media QC System")
st.markdown("### Professional Broadcast Analysis Node")

# --- 1. INITIALIZE SESSION STATE ---
# This acts as the "Memory" to prevent wiping data when buttons are clicked
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'output_dir' not in st.session_state:
    st.session_state.output_dir = None
if 'temp_path' not in st.session_state:
    st.session_state.temp_path = None

# --- 2. FILE UPLOAD ---
uploaded_file = st.file_uploader("Upload Video File", type=["mp4", "mov", "mkv", "avi"])

if uploaded_file is not None:
    # Save file only if it's a new upload
    os.makedirs("temp_upload", exist_ok=True)
    temp_path = os.path.join("temp_upload", uploaded_file.name)

    # Write file to disk
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.session_state.temp_path = temp_path
    st.success(f"File Uploaded: {uploaded_file.name}")

    # --- 3. RUN BUTTON (TRIGGER ONLY) ---
    if st.button("🚀 Run QC Analysis"):
        st.session_state.analysis_complete = False  # Reset previous run

        with st.spinner("Initializing AI Models & Physics Engine..."):
            # Prepare Output Paths
            output_dir = "reports"
            os.makedirs(output_dir, exist_ok=True)

            # Execute Pipeline
            cmd = [
                "python", "src/main.py",
                "--input", st.session_state.temp_path,
                "--output", output_dir
            ]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8'
            )

            # Live Logs
            log_placeholder = st.empty()
            full_logs = ""
            for line in process.stdout:
                full_logs += line
                log_placeholder.code(full_logs[-1000:], language="bash")

            process.wait()

            if process.returncode == 0:
                # SUCCESS: Save state and refresh UI
                st.session_state.analysis_complete = True
                st.session_state.output_dir = output_dir
                st.session_state.log_history = full_logs # Optional: Remember logs
            else:
                st.error("Analysis Failed. Check logs above.")

# --- 4. PERSISTENT DISPLAY LOGIC ---
# This runs on every refresh (including when Download is clicked)
# checking if the analysis was previously completed.

if st.session_state.analysis_complete and st.session_state.output_dir:
    output_dir = st.session_state.output_dir
    master_json = os.path.join(output_dir, "Master_Report.json")
    dashboard_html = os.path.join(output_dir, "dashboard.html")

    st.success("Analysis Complete!")

    # A. DOWNLOAD CORRECTED VIDEO (Top Priority)
    try:
        if os.path.exists(master_json):
            # We must regenerate dashboard HTML here to ensure it exists for display
            create_dashboard(master_json, dashboard_html)

            with open(master_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
                correction = data.get("modules", {}).get("audio_qc", {}).get("correction", {})

                if correction.get("status") == "FIXED":
                    fixed_path = correction.get("new_file")
                    if os.path.exists(fixed_path):
                        st.markdown("### ✅ Automated Correction Available")
                        st.info("The system detected audio violations and generated a corrected version.")

                        # Load data into memory so Streamlit can serve it without file locking issues
                        with open(fixed_path, "rb") as video_file:
                            video_bytes = video_file.read()

                        st.download_button(
                            label="📥 Download Corrected Video (Fixed Audio)",
                            data=video_bytes,
                            file_name=os.path.basename(fixed_path),
                            mime="video/mp4",
                            key="download_video" # Unique key
                        )
                        st.markdown("---")
    except Exception as e:
        st.error(f"Error loading correction data: {e}")

    # B. DASHBOARD DISPLAY
    st.markdown("### 📊 Interactive Analysis Report")
    if os.path.exists(dashboard_html):
        with open(dashboard_html, 'r', encoding='utf-8') as f:
            html_content = f.read()
        st.components.v1.html(html_content, height=800, scrolling=True)

    # C. JSON DOWNLOAD (Bottom)
    if os.path.exists(master_json):
        with open(master_json, "r", encoding='utf-8') as f:
            st.download_button(
                "📥 Download JSON Report",
                f,
                file_name="QC_Report.json",
                key="download_json"
            )

# Cleanup Footer
st.markdown("---")
st.caption("v1.5 Session State Stable | Powered by Python, FFmpeg & Docker")