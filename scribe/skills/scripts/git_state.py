#!/usr/bin/env python3
"""Git state utilities for scribe — capture commit hash and save diffs.

Requires Python 3.9+ (uses built-in generic types).
"""

import argparse
import subprocess
import sys

from common import require_scribe_dir


def run_git(*args: str) -> tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def cmd_hash(_args):
    """Print the current HEAD commit hash (short form)."""
    returncode, stdout, stderr = run_git("rev-parse", "--short", "HEAD")
    if returncode != 0:
        print(f"Error: {stderr or 'Not a git repository'}", file=sys.stderr)
        sys.exit(1)
    print(stdout)


def cmd_save_diff(args):
    """Save diff to .scribe/diffs/{id}.diff."""
    scribe_dir = require_scribe_dir()
    diffs_dir = scribe_dir / "diffs"
    diffs_dir.mkdir(exist_ok=True)

    entry_id = args.id
    diff_path = diffs_dir / f"{entry_id}.diff"

    # Build git diff command with file extensions
    extensions = args.ext.split(",") if args.ext else ["py"]
    pathspecs = [f"*.{ext.strip()}" for ext in extensions]

    # Get diff for specified extensions
    git_args = ["diff", "--no-ext-diff", "--"] + pathspecs
    returncode, stdout, stderr = run_git(*git_args)

    if returncode != 0:
        print(f"Error: {stderr}", file=sys.stderr)
        sys.exit(1)

    if not stdout:
        print(f"No changes in {', '.join(pathspecs)}")
        return

    # Write diff to file
    diff_path.write_text(stdout)

    # Calculate stats
    lines = stdout.split("\n")
    additions = sum(1 for line in lines if line.startswith("+") and not line.startswith("+++"))
    deletions = sum(1 for line in lines if line.startswith("-") and not line.startswith("---"))

    # Count files changed
    files_changed = sum(1 for line in lines if line.startswith("diff --git"))

    print(f"Saved: diffs/{entry_id}.diff")
    print(f"  {files_changed} file(s), +{additions}/-{deletions} lines")


def main():
    parser = argparse.ArgumentParser(description="Git state utilities for scribe")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # hash command
    hash_parser = subparsers.add_parser("hash", help="Print current HEAD commit hash (short)")
    hash_parser.set_defaults(func=cmd_hash)

    # save-diff command
    diff_parser = subparsers.add_parser("save-diff", help="Save diff to .scribe/diffs/")
    diff_parser.add_argument("id", help="Entry ID for the diff filename")
    diff_parser.add_argument(
        "--ext",
        default="py",
        help="Comma-separated file extensions to include (default: py)"
    )
    diff_parser.set_defaults(func=cmd_save_diff)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
