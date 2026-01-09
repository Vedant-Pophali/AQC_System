import json
import argparse
import os
import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from src.policy.policy_engine import (
    load_known_deviations,
    resolve_module_status,
    compute_ci
)

# -------------------------
# Utilities
# -------------------------
def _hash_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


# -------------------------
# Master Report + Policy
# -------------------------
def generate_master_report(input_reports, output_path, profile):
    """
    Industry-grade master aggregation:
    - loads raw validator reports
    - applies policy & deviations
    - computes effective status
    - returns authoritative CI exit code
    """

    modules = {}
    effective_statuses = {}

    # -------------------------
    # Load raw reports (STRICT + LEGACY SAFE)
    # -------------------------
    for path in input_reports:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # ---- module resolution ----
        module_name = data.get("module")
        if not module_name:
            module_name = Path(path).stem
            data["module"] = module_name
            data.setdefault("policy_notes", []).append(
                "Module name inferred from filename (legacy report)"
            )

        # ---- status enforcement ----
        status = data.get("status")
        if not status:
            # Missing status = validator/tooling failure
            data["status"] = "ERROR"
            data["error_code"] = "MISSING_STATUS_FIELD"
            data.setdefault("policy_notes", []).append(
                "Validator report missing 'status'; treated as ERROR"
            )

        modules[module_name] = data

    # -------------------------
    # Load known deviations
    # -------------------------
    root = Path(input_reports[0]).parents[1]
    deviations_path = root / "KNOWN_DEVIATIONS.md"
    deviations = load_known_deviations(deviations_path, profile)

    # -------------------------
    # Apply policy per module
    # -------------------------
    for module, report in modules.items():
        effective_status, notes = resolve_module_status(
            report,
            profile,
            deviations
        )

        effective_statuses[module] = effective_status
        report["effective_status"] = effective_status

        if notes:
            report.setdefault("policy_notes", []).extend(notes)

    # -------------------------
    # Compute CI decision
    # -------------------------
    overall_status, ci_exit_code = compute_ci(effective_statuses)

    # -------------------------
    # Final master report
    # -------------------------
    master_report = {
        "metadata": {
            "generated_on": datetime.now(timezone.utc).isoformat(),
            "profile": profile,
            "tool": "AQC",
            "report_hash": _hash_file(input_reports[0])
        },
        "overall_status": overall_status,
        "ci_exit_code": ci_exit_code,
        "modules": modules,
        "known_deviations": deviations
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(master_report, f, indent=4)

    return ci_exit_code


# -------------------------
# CLI
# -------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate QC Master Report")
    parser.add_argument("--inputs", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--profile", choices=["strict", "ott"], required=True)
    args = parser.parse_args()

    exit_code = generate_master_report(
        args.inputs,
        args.output,
        args.profile
    )

    sys.exit(exit_code)
