import argparse
import subprocess
import sys
from pathlib import Path

from pyspark.sql import SparkSession


# -----------------------------------
# WORKER FUNCTION
# -----------------------------------
def run_qc(file_path, mode, outdir, aqc_path):
    """
    Runs the existing Windows CLI (aqc) for a single file.
    Spark treats this as an isolated task.
    """

    cmd = [
        aqc_path,
        "--input", file_path,
        "--mode", mode,
        "--outdir", outdir
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        return {
            "file": file_path,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }

    except Exception as e:
        return {
            "file": file_path,
            "exit_code": -1,
            "stdout": "",
            "stderr": str(e)
        }


# -----------------------------------
# ENTRY POINT
# -----------------------------------
def main():
    parser = argparse.ArgumentParser(description="Distributed QC Runner (Spark)")
    parser.add_argument(
        "--input-list",
        required=True,
        help="Text file with one video path per line"
    )
    parser.add_argument(
        "--mode",
        choices=["strict", "ott"],
        default="strict",
        help="QC mode"
    )
    parser.add_argument(
        "--outdir",
        default="reports",
        help="Base output directory"
    )
    parser.add_argument(
        "--aqc-path",
        default=str(Path(__file__).parent.parent / "aqc"),
        help="Path to aqc CLI (default: project root)"
    )
    args = parser.parse_args()

    input_list = Path(args.input_list)
    if not input_list.exists():
        print(f"[FATAL] Input list not found: {input_list}")
        sys.exit(1)

    with open(input_list, "r", encoding="utf-8") as f:
        files = [line.strip() for line in f if line.strip()]

    if not files:
        print("[FATAL] Input list is empty")
        sys.exit(1)

    aqc_path = str(Path(args.aqc_path).resolve())

    print("\n>>> SPARK QC RUNNER")
    print(f"    Files     : {len(files)}")
    print(f"    Mode      : {args.mode}")
    print(f"    OutputDir : {args.outdir}")
    print(f"    AQC CLI   : {aqc_path}\n")

    spark = (
        SparkSession.builder
        .appName("AQC_Distributed_QC")
        .getOrCreate()
    )

    sc = spark.sparkContext

    # Parallelize by FILE (not by frame)
    rdd = sc.parallelize(files, len(files))

    results = rdd.map(
        lambda f: run_qc(f, args.mode, args.outdir, aqc_path)
    ).collect()

    spark.stop()

    # -----------------------------------
    # SUMMARY
    # -----------------------------------
    failures = [r for r in results if r["exit_code"] != 0]

    print("\n>>> SPARK QC SUMMARY")
    print(f"    Total files : {len(results)}")
    print(f"    Success     : {len(results) - len(failures)}")
    print(f"    Failed      : {len(failures)}\n")

    if failures:
        print("Failed files:")
        for f in failures:
            print(f" - {f['file']} (exit {f['exit_code']})")

        sys.exit(1)

    print("[OK] Distributed QC completed successfully")
    sys.exit(0)


if __name__ == "__main__":
    main()
