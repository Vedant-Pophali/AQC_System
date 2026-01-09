import json
import argparse
import os
import sys
import pandas as pd
import plotly.express as px

# UTF-8 safety (Windows)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


STATUS_COLORS = {
    "PASSED": "#00CC96",
    "WARNING": "#FFA15A",
    "REJECTED": "#EF553B",
    "ERROR": "#636EFA"
}


def load_master_report(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Master report not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_timeline_rows(report):
    modules = report.get("modules")
    if not modules:
        raise ValueError("Master report missing modules")

    rows = []

    for module_name, module in modules.items():
        status = module["status"]
        events = module.get("events", [])

        label = module_name.replace("_qc", "").replace("_", " ").title()

        if events:
            for ev in events:
                if "start_time" not in ev or "end_time" not in ev:
                    raise ValueError(
                        f"Event missing time fields in module {module_name}"
                    )

                start = float(ev["start_time"])
                end = float(ev["end_time"])

                rows.append({
                    "Module": label,
                    "Start": start,
                    "Duration": max(end - start, 0.01),
                    "Status": status,
                    "Details": ev.get("details", ev.get("type", "Event"))
                })
        else:
            # Structural / whole-file module (already validated upstream)
            rows.append({
                "Module": label,
                "Start": 0.0,
                "Duration": 1.0,
                "Status": status,
                "Details": status
            })

    if not rows:
        raise ValueError("No events available for visualization")

    return pd.DataFrame(rows)


def render_dashboard(df, title, output_path):
    fig = px.bar(
        df,
        base="Start",
        x="Duration",
        y="Module",
        color="Status",
        orientation="h",
        hover_data=["Details"],
        color_discrete_map=STATUS_COLORS,
        title=title
    )

    fig.update_layout(
        xaxis=dict(title="Timeline (seconds)"),
        yaxis=dict(autorange="reversed", title=None),
        height=400 + (len(df["Module"].unique()) * 40),
        margin=dict(l=200, r=40, t=80, b=40)
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.write_html(output_path)


def main():
    parser = argparse.ArgumentParser(description="Visualize QC Master Report")
    parser.add_argument("--input", required=True, help="Master report JSON")
    parser.add_argument("--output", required=True, help="Output HTML dashboard")
    args = parser.parse_args()

    report = load_master_report(args.input)

    metadata = report.get("metadata", {})
    title = f"QC Timeline: {metadata.get('filename', 'Video')}"

    df = build_timeline_rows(report)
    render_dashboard(df, title, args.output)

    print(f"[OK] QC dashboard generated: {args.output}")


if __name__ == "__main__":
    main()
