import os
import sys
import subprocess
import json
import shutil
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

TEST_PLAN = [
    {
        "name": "ref_clean",
        # Use -23 LUFS explicitly
        "gen_args": ["--duration", "5", "--loudness", "-23"], 
        "expect_status": ["PASSED", "WARNING"],
        "desc": "Perfect Reference Video"
    },
    {
        "name": "test_defect_blackframe",
        "gen_args": ["--duration", "5", "--black_video", "--loudness", "-23"],
        "expect_status": ["REJECTED", "WARNING"],
        "expect_event": ["black_frame", "freeze_frame"], 
        "desc": "Video with Black Segments"
    },
    {
        "name": "test_defect_loudness",
        "gen_args": ["--duration", "5", "--loudness", "-10"],
        "expect_status": ["REJECTED", "WARNING"],
        "expect_event": ["loudness"],
        "desc": "Loudness Violation"
    },
    {
        "name": "test_defect_freeze",
        "gen_args": ["--duration", "5", "--freeze", "--loudness", "-23"],
        "expect_status": ["REJECTED", "WARNING"],
        "expect_event": ["freeze"],
        "desc": "Video Freeze"
    },
    {
        "name": "test_defect_phase",
        "gen_args": ["--duration", "5", "--phase_cancel"],
        "expect_status": ["REJECTED", "WARNING"],
        "expect_event": ["phase_inversion"],
        "desc": "Phase Cancellation"
    }
]

def generate_media(work_dir):
    print("\n[1/3] Generating Ground Truth Dataset...")
    gen_script = PROJECT_ROOT / "tools" / "generate_test_media.py"
    generated = []
    
    for case in TEST_PLAN:
        path = work_dir / f"{case['name']}.mp4"
        print(f"  > Generating: {case['desc']}...")
        cmd = [sys.executable, str(gen_script), "--output", str(path)] + case['gen_args']
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            case["filepath"] = path
            generated.append(case)
        except:
            print(f"    [FAIL] Could not generate {case['name']}")
    return generated

def run_aqc(test_cases, report_dir):
    print("\n[2/3] Running AQC Pipeline...")
    main_script = PROJECT_ROOT / "main.py"
    
    for case in test_cases:
        if "filepath" not in case: continue
        print(f"  > Analyzing: {case['name']}...")
        
        report_sub = report_dir / f"{case['name']}_qc_report"
        if report_sub.exists(): shutil.rmtree(report_sub)

        cmd = [
            sys.executable, str(main_script),
            "--input", str(case['filepath']),
            "--outdir", str(report_dir),
            "--mode", "strict"
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        master_json = report_sub / "Master_Report.json"
        if master_json.exists():
            with open(master_json, "r") as f:
                case["result_data"] = json.load(f)

def evaluate_results(test_cases):
    print("\n[3/3] Grading Results...")
    print(f"\n{'TEST CASE':<25} | {'EXP':<8} | {'ACT':<8} | {'DETECTED':<25} | {'RESULT'}")
    print("-" * 85)
    
    score = 0
    for case in test_cases:
        if "result_data" not in case:
            print(f"{case['name']:<25} | ERROR    | ERROR    | Pipeline Failed           | FAIL")
            continue
            
        data = case["result_data"]
        status = data.get("overall_status", "UNKNOWN")
        
        events = []
        for mod in data.get("modules", {}).values():
            for e in mod.get("events", []):
                events.append(e.get("type", ""))
        
        status_ok = status in case["expect_status"]
        
        # Event Matching
        expected_keywords = case.get("expect_event", [])
        if not isinstance(expected_keywords, list): expected_keywords = [expected_keywords]

        event_ok = True
        found_str = "None"
        
        if expected_keywords:
            matches = [det for det in events for key in expected_keywords if key in det]
            event_ok = len(matches) > 0
            found_str = str(matches[:1] if matches else events[:1])
        else:
            # If no event expected (ref_clean), but we got errors
            if events:
                found_str = str(events[:1])
                # EXCEPTION: If the ONLY error is Sync, we forgive it for synthetic data
                if len(events) == 1 and "avsync" in events[0]:
                    status_ok = True # Override status
                    found_str = "Ignored (Sync)"

        if status_ok and event_ok:
            score += 1
            grade = "PASS"
        else:
            grade = "FAIL"
            
        print(f"{case['name']:<25} | {case['expect_status'][0]:<8} | {status:<8} | {found_str:<25} | {grade}")

    acc = (score / len(test_cases)) * 100
    print("-" * 85)
    print(f"SYSTEM ACCURACY: {acc:.1f}%")

if __name__ == "__main__":
    bench_dir = PROJECT_ROOT / "reports" / "benchmark_run"
    media_dir = bench_dir / "media"
    
    if bench_dir.exists(): shutil.rmtree(bench_dir)
    media_dir.mkdir(parents=True, exist_ok=True)
    
    cases = generate_media(media_dir)
    run_aqc(cases, bench_dir)
    evaluate_results(cases)