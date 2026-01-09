import argparse
import json
from pathlib import Path

# -------------------------
# Utilities
# -------------------------
def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# -------------------------
# Collect segment masters
# -------------------------
def collect_segment_masters(base_dir: Path):
    """
    Collect segment-level Master_Report.json files.
    """
    masters = []
    for seg_dir in sorted(base_dir.glob("seg_*")):
        mr = seg_dir / "Master_Report.json"
        if mr.exists():
            masters.append(load_json(mr))
    return masters


# -------------------------
# Aggregate logic (Phase 2.2 compliant)
# -------------------------
def aggregate_segments(segment_masters):
    """
    FINAL aggregation logic.

    Rules:
    - No suppression
    - No reinterpretation of events
    - effective_status is authoritative
    - Always write final report (even on FAIL)
    """

    status_rank = {
        "PASSED": 0,
        "WARNING": 1,
        "REJECTED": 2,
        "ERROR": 3
    }

    worst_rank = 0
    aggregated_modules = {}

    for master in segment_masters:
        modules = master.get("modules", {})
        if not modules:
            raise ValueError("Segment master missing modules")

        for module, data in modules.items():
            # Effective status is authoritative
            effective_status = data.get(
                "effective_status",
                data.get("status", "PASSED")
            )

            worst_rank = max(
                worst_rank,
                status_rank.get(effective_status, 0)
            )

            if module not in aggregated_modules:
                aggregated_modules[module] = {
                    "module": module,
                    "effective_status": effective_status,
                    "segments_seen": 1
                }
            else:
                aggregated_modules[module]["segments_seen"] += 1

    overall_status = {
        0: "PASSED",
        1: "WARNING",
        2: "REJECTED",
        3: "ERROR"
    }[worst_rank]

    ci_exit_code = {
        "PASSED": 0,
        "WARNING": 0,
        "REJECTED": 2,
        "ERROR": 3
    }[overall_status]

    return {
        "overall_status": overall_status,
        "ci_exit_code": ci_exit_code,
        "modules": aggregated_modules
    }


# -------------------------
# CLI
# -------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Phase 2.2 Final Segment Master Aggregator"
    )
    parser.add_argument(
        "--segment-reports",
        required=True,
        help="Directory containing seg_XXX folders"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output Final_Master_Report.json path"
    )
    parser.add_argument(
        "--profile",
        choices=["strict", "ott"],
        required=True
    )

    args = parser.parse_args()

    base_dir = Path(args.segment_reports)
    segment_masters = collect_segment_masters(base_dir)

    if not segment_masters:
        print("[FATAL] No segment master reports found")
        raise SystemExit(1)

    aggregated = aggregate_segments(segment_masters)

    final_master = {
        "metadata": {
            "segments": len(segment_masters),
            "profile": args.profile,
            "reconstructed": True
        },
        "overall_status": aggregated["overall_status"],
        "ci_exit_code": aggregated["ci_exit_code"],
        "modules": aggregated["modules"]
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_master, f, indent=4)

    print(f"[OK] Final master report written: {output_path}")
    print(f"[CI] Exit code: {final_master['ci_exit_code']}")
