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

# --- FILE UPLOAD ---
uploaded_file = st.file_uploader("Upload Video File", type=["mp4", "mov", "mkv", "avi"])

if uploaded_file is not None:
    # 1. Save the file temporarily
    os.makedirs("temp_upload", exist_ok=True)
    temp_path = os.path.join("temp_upload", uploaded_file.name)

    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.success(f"File Uploaded: {uploaded_file.name}")

    # 2. The "Start" Button
    if st.button("🚀 Run QC Analysis"):
        with st.spinner("Initializing AI Models & Physics Engine..."):
            # Prepare Output Paths
            output_dir = "reports"
            os.makedirs(output_dir, exist_ok=True)

            # --- EXECUTE THE PIPELINE ---
            # We call main.py as a subprocess (just like the old batch file)
            cmd = [
                "python", "src/main.py",
                "--input", temp_path,
                "--output", output_dir
            ]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8' # Force UTF-8 for logs
            )

            # Live Log Viewer
            log_placeholder = st.empty()
            full_logs = ""

            for line in process.stdout:
                full_logs += line
                log_placeholder.code(full_logs[-1000:], language="bash") # Show last 1000 chars

            process.wait()

            if process.returncode == 0:
                st.success("Analysis Complete!")

                # --- DISPLAY RESULTS ---
                # 1. Generate Dashboard HTML
                master_json = os.path.join(output_dir, "Master_Report.json")
                dashboard_html = os.path.join(output_dir, "dashboard.html")

                # Run visualization manually to ensure it's fresh
                create_dashboard(master_json, dashboard_html)

                # 2. Show the HTML Dashboard inside the Web App
                with open(dashboard_html, 'r', encoding='utf-8') as f:
                    html_content = f.read()

                st.components.v1.html(html_content, height=800, scrolling=True)

                # 3. Download Button for JSON
                with open(master_json, "r") as f:
                    st.download_button("📥 Download JSON Report", f, file_name="QC_Report.json")

            else:
                st.error("Analysis Failed. Check logs above.")

# Cleanup Footer
st.markdown("---")
st.caption("v1.1 Containerized Build | Powered by Python, FFmpeg & Docker")