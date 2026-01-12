import subprocess
import argparse
import sys
from pathlib import Path

def run_ffmpeg(cmd):
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"[!] FFmpeg Failed: {' '.join(cmd)}")
        print(f"[!] Error: {e.stderr.decode()}")
        raise e

def generate_file(args):
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    duration = args.duration
    
    # Audio Source Logic
    # Beeps are good for human checking, Continuous is required for accurate short-term Loudness checks
    if args.continuous or args.loudness:
        audio_src = f"sine=frequency=1000:duration={duration}" # Continuous
    else:
        audio_src = f"sine=frequency=1000:duration={duration}:beep_factor=4" # Beeps

    inputs = [
        "-f", "lavfi", "-i", f"testsrc2=duration={duration}:size=1280x720:rate=24",
        "-f", "lavfi", "-i", audio_src
    ]
    
    vf_filters = []
    af_filters = []
    
    # Defects
    if args.black_video:
        vf_filters.append("drawbox=enable='between(t,1,4)':color=black:t=fill")
    if args.freeze:
        vf_filters.append("loop=60:1:24")
    if args.phase_cancel:
        af_filters.append("pan=stereo|c0=c0|c1=-1*c0")

    # LOUDNESS NORMALIZATION
    # If a target is set, we force it using loudnorm
    if args.loudness:
        try:
            target = float(args.loudness)
        except:
            target = -10.0
        # linear=true ensures better accuracy for synth tones
        af_filters.append(f"loudnorm=I={target}:TP=-1.5:LRA=11:linear=true")

    # Metadata & Encoding
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-metadata:s:v:0", "language=eng",
        "-metadata:s:a:0", "language=eng",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
        "-c:a", "aac", "-b:a", "128k"
    ]
    
    if vf_filters: cmd.extend(["-vf", ",".join(vf_filters)])
    if af_filters: cmd.extend(["-af", ",".join(af_filters)])
        
    cmd.append(str(output_path))
    run_ffmpeg(cmd)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--duration", type=int, default=10)
    parser.add_argument("--base")
    parser.add_argument("--black_video", action="store_true")
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--phase_cancel", action="store_true")
    parser.add_argument("--loudness", help="Target LUFS value")
    parser.add_argument("--continuous", action="store_true", help="Use continuous tone (no beeps)")
    
    args = parser.parse_args()
    try: generate_file(args)
    except: sys.exit(1)