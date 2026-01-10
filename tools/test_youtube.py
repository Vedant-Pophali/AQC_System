import os
import sys
import subprocess
from pathlib import Path
try:
    import yt_dlp
except ImportError:
    print("Error: yt-dlp not installed. Run 'pip install yt-dlp'")
    sys.exit(1)

# -------------------------------------------------
# THE REAL-WORLD TEST SUITE
# -------------------------------------------------
TEST_VIDEOS = [
    {
        "name": "Reference_Clean_4K",
        "url": "https://www.youtube.com/watch?v=SYyvx6GE2UI",
        "desc": "High quality nature footage. Should PASS everything."
    },
    {
        "name": "Phase_Cancellation_Test",
        "url": "https://www.youtube.com/watch?v=w5oj06lMGM8",
        "desc": "Audio polarity test. Should trigger AUDIO PHASE REJECTION."
    },
    {
        "name": "Old_VHS_Footage",
        "url": "https://www.youtube.com/watch?v=iCz1VemKns4",
        "desc": "Noisy 1993 footage. Should trigger ARTIFACT/NOISE warnings."
    }
]

DOWNLOAD_DIR = Path("test_media/youtube")
REPORT_DIR = Path("reports/youtube_test")

def download_video(url, name):
    print(f"\n[DOWNLOADER] Fetching: {name}...")
    
    # Configure yt-dlp to download 720p/1080p mp4 with audio
    ydl_opts = {
        'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': str(DOWNLOAD_DIR / f"{name}.%(ext)s"),
        'quiet': True,
        'no_warnings': True,
        'overwrites': False  # Skip if already exists
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        return Path(filename)

def run_aqc(video_path):
    print(f"[AQC] Analyzing {video_path.name}...")
    
    # Create specific report folder
    video_report_dir = REPORT_DIR / video_path.stem
    
    cmd = [
        sys.executable, "src/main.py",
        "--input", str(video_path),
        "--outdir", str(video_report_dir),
        "--mode", "strict"
    ]
    
    subprocess.run(cmd)

def main():
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=== YOUTUBE REAL-WORLD STRESS TEST ===")
    
    for video in TEST_VIDEOS:
        print(f"\n--- Processing: {video['name']} ---")
        print(f"Goal: {video['desc']}")
        
        try:
            # 1. Download
            file_path = download_video(video['url'], video['name'])
            
            # 2. Run QC
            if file_path.exists():
                run_aqc(file_path)
            else:
                print("Download failed, skipping QC.")
                
        except Exception as e:
            print(f"Error processing {video['name']}: {e}")

    print("\n[DONE] All YouTube tests completed.")
    print(f"Check results in: {REPORT_DIR}")

if __name__ == "__main__":
    main()