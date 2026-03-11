#!/usr/bin/env python3
"""Open a ddag node's transform code in vim via iTerm2 for external editing.

Usage:
    ddag_edit.py <ddag_path> [--root <project_root>]
"""

import argparse
import os
import shutil
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import ddag_core


def derive_names(ddag_path):
    """Derive workspace filenames from the ddag path.

    Flattens path components with __ separator to avoid collisions.
    Returns (name, code_file, reference_file) relative to .ddag/ dir.
    """
    name = ddag_path.replace(os.sep, "__").removesuffix(".ddag")
    return name, f"{name}.code.py", f"{name}.reference_code.py"


def open_in_iterm(command, cwd):
    script = f'''
tell application "iTerm2"
    activate
    create window with default profile command "bash -lc 'cd \\"{cwd}\\" && {command}'"
end tell
'''
    subprocess.run(
        ["osascript", "-e", script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main():
    parser = argparse.ArgumentParser(description="Edit a ddag node's code in vim")
    parser.add_argument("ddag_path", help="Path to the .ddag file")
    parser.add_argument("--root", default=".", help="Project root directory")
    args = parser.parse_args()

    ddag_path = args.ddag_path
    root = args.root

    # Read node and validate
    try:
        node = ddag_core.read_node(ddag_path)
    except Exception as e:
        print(f"Error reading node: {e}", file=sys.stderr)
        sys.exit(1)

    if node["is_source_node"]:
        print(f"Error: {ddag_path} is a source node (no transform function to edit)", file=sys.stderr)
        sys.exit(1)

    if not node["transform_function"]:
        print(f"Error: {ddag_path} has no function_body", file=sys.stderr)
        sys.exit(1)

    # Set up workspace
    workspace = os.path.join(root, ".ddag_work")
    os.makedirs(workspace, exist_ok=True)

    name, code_filename, ref_filename = derive_names(ddag_path)
    code_path = os.path.join(workspace, code_filename)
    ref_path = os.path.join(workspace, ref_filename)

    # Clean up previous session files if they exist
    for f in (code_path, ref_path):
        if os.path.exists(f):
            print(f"Warning: removing leftover file from previous session: {f}")
            os.remove(f)

    # Write code and reference copy
    function_body = node["transform_function"]
    with open(code_path, "w") as f:
        f.write(function_body + "\n")
    shutil.copy2(code_path, ref_path)

    # Open iTerm2 with the wrapper script
    wrapper = os.path.join(SCRIPT_DIR, "ddag_edit_wrapper.sh")
    cmd = f'bash \\"{wrapper}\\" \\"{ddag_path}\\" \\"{name}\\"'
    open_in_iterm(cmd, os.path.abspath(root))

    print(f"Opened vim in new iTerm2 window for: {ddag_path}")
    print(f"Editing: {code_path}")
    print("Save and quit vim to continue. The terminal will guide you through review and commit.")


if __name__ == "__main__":
    main()
