#!/usr/bin/env python3
"""Probe a data file and print a compact structural summary."""

import argparse
import csv
import os
import sys


def is_numeric(val: str) -> bool:
    """Check if a string looks numeric (after stripping formatting)."""
    cleaned = val.replace(",", "").replace("$", "").replace("%", "").strip()
    if not cleaned:
        return False
    try:
        float(cleaned)
        return True
    except ValueError:
        return False


def probe_csv(path: str, show_rows: int = 10) -> None:
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        print("(empty file)")
        return

    n_rows = len(rows)
    n_cols = max(len(r) for r in rows)

    # Pad short rows
    for r in rows:
        while len(r) < n_cols:
            r.append("")

    fname = os.path.basename(path)
    print(f"=== {fname} ===")
    print(f"{n_rows} rows \u00d7 {n_cols} columns")

    # Row structure
    print(f"\nRow structure (first {min(show_rows, n_rows)}):")
    for i, row in enumerate(rows[:show_rows]):
        filled = sum(1 for c in row if c.strip())
        vals = [c.strip() for c in row if c.strip()]
        preview = " | ".join(vals)
        if len(preview) > 80:
            preview = preview[:77] + "..."
        print(f"  [{i + 1}] {filled:>2}/{n_cols} filled  | {preview}")
    if n_rows > show_rows:
        print(f"  ... ({n_rows - show_rows} more rows)")

    # Header detection: among first 5 rows, pick the one with most non-empty
    # cells that aren't predominantly numeric
    best_row, best_score = 0, -1
    for i in range(min(5, n_rows)):
        cells = [c.strip() for c in rows[i] if c.strip()]
        if not cells:
            continue
        numeric_frac = sum(1 for c in cells if is_numeric(c)) / len(cells)
        if numeric_frac > 0.5:
            continue
        score = len(cells)
        if score > best_score:
            best_score = score
            best_row = i

    header_row = rows[best_row]
    header_filled = sum(1 for c in header_row if c.strip())
    data_start = best_row + 1

    print(f"\nHeader: row {best_row + 1} ({header_filled}/{n_cols} filled), "
          f"data starts: row {data_start + 1}")

    # Column groups: split on empty columns in the header row
    groups = []
    current_group = []
    for ci in range(n_cols):
        if header_row[ci].strip():
            current_group.append(ci)
        else:
            if current_group:
                groups.append(current_group)
                current_group = []
    if current_group:
        groups.append(current_group)

    if len(groups) > 1:
        print(f"\nColumn groups ({len(groups)} groups, separated by empty columns):")
        for g in groups:
            start, end = g[0], g[-1]
            names = [header_row[ci].strip().replace("\n", " ") for ci in g]
            preview = ", ".join(names)
            if len(preview) > 70:
                preview = preview[:67] + "..."
            print(f"  [{start}-{end}]  ({len(g)} cols) {preview}")

    # All columns
    print("\nAll columns:")
    for g in groups:
        entries = []
        for ci in g:
            name = header_row[ci].strip().replace("\n", " ")
            if name:
                label = f"[{ci}] {name}"
                if len(label) > 40:
                    label = label[:37] + "..."
                entries.append(label)
        if entries:
            line = "  " + "  ".join(entries)
            if len(line) > 120:
                # Wrap long lines
                line = "  "
                for e in entries:
                    if len(line) + len(e) + 2 > 120:
                        print(line)
                        line = "  " + e
                    else:
                        line += "  " + e if line != "  " else e
            print(line)


def probe_structured(path: str, show_rows: int = 10) -> None:
    """Probe Parquet, JSON, or other structured files via polars."""
    import polars as pl

    ext = os.path.splitext(path)[1].lower()
    if ext == ".parquet":
        df = pl.read_parquet(path)
    elif ext in (".json", ".ndjson"):
        try:
            df = pl.read_ndjson(path)
        except Exception:
            df = pl.read_json(path)
    else:
        print(f"Unsupported format: {ext}", file=sys.stderr)
        sys.exit(1)

    fname = os.path.basename(path)
    print(f"=== {fname} ===")
    print(f"{df.height} rows \u00d7 {df.width} columns\n")
    print("Schema:")
    for name, dtype in zip(df.columns, df.dtypes):
        print(f"  {name}: {dtype}")
    print(f"\nFirst {min(show_rows, df.height)} rows:")
    print(df.head(show_rows))


def main():
    parser = argparse.ArgumentParser(description="Probe a data file structure")
    parser.add_argument("file", help="Path to the data file")
    parser.add_argument("--rows", type=int, default=10,
                        help="Number of row summaries to show (default: 10)")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    ext = os.path.splitext(args.file)[1].lower()
    if ext in (".csv", ".tsv", ".txt"):
        probe_csv(args.file, args.rows)
    else:
        probe_structured(args.file, args.rows)


if __name__ == "__main__":
    main()
