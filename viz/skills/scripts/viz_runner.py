#!/usr/bin/env python3
"""Thin runner for viz skill. Validates, executes, and polls for rendered output."""
import argparse, os, subprocess, sys, time
from pathlib import Path

VIZ_DIR = Path(".viz")

def existing_plots():
    return sorted(p.stem for p in VIZ_DIR.glob("*.png"))

def run(name, overwrite):
    VIZ_DIR.mkdir(exist_ok=True)
    script, png, err_file = VIZ_DIR / f"{name}.py", VIZ_DIR / f"{name}.png", VIZ_DIR / f"{name}.err"
    if not script.exists():
        sys.exit(f"ERROR: {script} not found")
    data_patterns = [f"{name}.parquet", f"{name}.csv", f"{name}_*.parquet", f"{name}_*.csv"]
    if not any(VIZ_DIR.glob(p) for p in data_patterns):
        sys.exit(f"ERROR: No data files matching {name}.parquet/csv or {name}_*.parquet/csv in .viz/")
    if png.exists() and not overwrite:
        sys.exit(f"ERROR: '{name}.png' already exists. Use --overwrite to update.\nExisting plots: {', '.join(existing_plots())}")
    if overwrite and png.exists():
        png.unlink()
    env = os.environ.copy()
    env["MPLBACKEND"] = "macosx" if sys.platform == "darwin" else "TkAgg"
    with open(err_file, "w") as ef:
        subprocess.Popen([sys.executable, script.name], cwd=str(VIZ_DIR),
                         env=env, start_new_session=True, stdout=subprocess.DEVNULL, stderr=ef)
    elapsed = 0.0
    while elapsed < 30.0:
        if png.exists():
            err_file.unlink(missing_ok=True)
            print(f"VIZ: {name} | {png}")
            return
        time.sleep(0.2)
        elapsed += 0.2
    stderr_content = err_file.read_text().strip() if err_file.exists() else ""
    if stderr_content:
        sys.exit(f"ERROR: PNG not created within timeout\n{stderr_content}")
    sys.exit("ERROR: Script timed out after 30s. No stderr output captured.")

def list_plots():
    if not VIZ_DIR.exists():
        return print("No .viz/ directory found.")
    plots = existing_plots()
    if not plots:
        return print("No visualizations found in .viz/")
    print("Visualizations in .viz/:")
    for p in plots:
        print(f"  {p:<20} {p}.png")

def main():
    ap = argparse.ArgumentParser(description="Viz runner")
    ap.add_argument("name", nargs="?", help="Visualization name")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing output")
    ap.add_argument("--list", action="store_true", help="List existing visualizations")
    args = ap.parse_args()
    if args.list:
        list_plots()
    elif args.name:
        run(args.name, args.overwrite)
    else:
        ap.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
