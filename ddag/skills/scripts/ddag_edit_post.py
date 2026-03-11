#!/usr/bin/env python3
"""Post-edit workflow for ddag external code editing.

Runs inside iTerm2 after vim exits. Checks for changes, offers vimdiff
review, and commits back to the .ddag file.

Usage:
    ddag_edit_post.py <ddag_path> <name>
"""

import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import ddag_core


def files_differ(path_a, path_b):
    """Check if two files differ. Returns True if different."""
    result = subprocess.run(
        ["diff", "-q", path_a, path_b],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode != 0


def cleanup(code_path, ref_path, workspace):
    """Remove temp files and .ddag/ dir if empty."""
    for f in (code_path, ref_path):
        if os.path.exists(f):
            os.remove(f)
    try:
        os.rmdir(workspace)
    except OSError:
        pass  # Directory not empty or doesn't exist


def main():
    if len(sys.argv) != 3:
        print("Usage: ddag_edit_post.py <ddag_path> <name>", file=sys.stderr)
        sys.exit(1)

    ddag_path = sys.argv[1]
    name = sys.argv[2]

    workspace = ".ddag_work"
    code_path = os.path.join(workspace, f"{name}.code.py")
    ref_path = os.path.join(workspace, f"{name}.reference_code.py")

    # Check for changes
    if not files_differ(code_path, ref_path):
        print("No changes detected.")
        cleanup(code_path, ref_path, workspace)
        return

    # Changes found — open vimdiff for review
    print("Changes detected. Opening vimdiff for review...")
    print("Left pane: original  |  Right pane: your edits")
    print("Quit vimdiff with :qa when done reviewing.\n")
    subprocess.run(["vimdiff", ref_path, code_path])

    # Re-check after vimdiff (user may have reverted)
    if not files_differ(code_path, ref_path):
        print("No changes detected after review.")
        cleanup(code_path, ref_path, workspace)
        return

    # Prompt for action
    while True:
        choice = input("\n[c]ommit  [a]bandon: ").strip().lower()
        if choice in ("c", "a"):
            break
        print("Please enter 'c' or 'a'.")

    if choice == "a":
        print("Changes abandoned.")
        cleanup(code_path, ref_path, workspace)
        return

    # Commit: keep existing plan, load code back into node
    transform_plan = ddag_core.get_transform_plan(ddag_path)
    if not transform_plan or not transform_plan.strip():
        print("Error: node has no transform_plan. Update the plan in Claude Code first.")
        print(f"Temp files kept for retry: {code_path}")
        sys.exit(1)

    try:
        ddag_core.load_function(ddag_path, transform_plan, input_path=code_path)
        print(f"\nSuccess! Updated transform in {ddag_path}")
        cleanup(code_path, ref_path, workspace)
    except Exception as e:
        print(f"\nError committing changes: {e}")
        print(f"Temp files kept for retry: {code_path}")
        sys.exit(1)

    # Run single-node audit
    print(f"\nAuditing {ddag_path}...")
    audit_result = subprocess.run(
        [sys.executable, os.path.join(SCRIPT_DIR, "ddag_build.py"), "audit", "--node", ddag_path, "--root", "."],
        capture_output=False,
    )
    if audit_result.returncode != 0:
        print("Audit flagged issues — review above.")


if __name__ == "__main__":
    main()
