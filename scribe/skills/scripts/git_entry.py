#!/usr/bin/env python3
"""Git entry utilities for scribe — create commits with entry text as message.

Requires Python 3.9+ (uses built-in generic types).
"""

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

from common import FRONTMATTER_PATTERN


def run_git(*args: str) -> tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def cmd_status(_args):
    """Show what would be staged (modified tracked files)."""
    # Get modified tracked files
    returncode, stdout, stderr = run_git("diff", "--name-only")
    if returncode != 0:
        print(f"Error: {stderr}", file=sys.stderr)
        sys.exit(1)

    if not stdout:
        print("No modified tracked files")
        return

    files = stdout.split("\n")
    print(f"Modified tracked files ({len(files)}):")
    for f in files:
        print(f"  {f}")


def cmd_commit(args):
    """Stage modified tracked files and create commit with entry text as message."""
    # Read entry file
    entry_path = Path(args.file)
    if not entry_path.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    entry_content = entry_path.read_text()

    # Extract title from frontmatter for commit subject
    frontmatter_match = FRONTMATTER_PATTERN.match(entry_content)
    if not frontmatter_match:
        print("Error: Entry must have YAML frontmatter", file=sys.stderr)
        sys.exit(1)

    frontmatter = yaml.safe_load(frontmatter_match.group(1)) or {}
    title = frontmatter.get("title")
    if not title:
        print("Error: Entry frontmatter must have 'title' field", file=sys.stderr)
        sys.exit(1)

    # Stage all modified tracked files (not untracked)
    returncode, stdout, stderr = run_git("add", "-u")
    if returncode != 0:
        print(f"Error staging files: {stderr}", file=sys.stderr)
        sys.exit(1)

    # Check if there's anything staged
    returncode, stdout, stderr = run_git("diff", "--cached", "--quiet")
    if returncode == 0:
        print("Nothing staged to commit")
        sys.exit(1)

    # Create commit with full entry as message
    # Subject line is the title, body is the full entry content
    commit_message = f"{title}\n\n{entry_content}"

    returncode, stdout, stderr = run_git("commit", "-m", commit_message)
    if returncode != 0:
        print(f"Error creating commit: {stderr}", file=sys.stderr)
        sys.exit(1)

    # Get the new commit hash
    returncode, commit_hash, stderr = run_git("rev-parse", "--short", "HEAD")
    if returncode != 0:
        print(f"Error getting commit hash: {stderr}", file=sys.stderr)
        sys.exit(1)

    print(f"Created commit: {commit_hash}")
    print(stdout)  # git commit output shows files


def main():
    parser = argparse.ArgumentParser(description="Git entry utilities for scribe")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status command
    status_parser = subparsers.add_parser("status", help="Show modified tracked files")
    status_parser.set_defaults(func=cmd_status)

    # commit command
    commit_parser = subparsers.add_parser("commit", help="Stage and commit with entry as message")
    commit_parser.add_argument("--file", required=True, help="Entry file with YAML frontmatter")
    commit_parser.set_defaults(func=cmd_commit)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
