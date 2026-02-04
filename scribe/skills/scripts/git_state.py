#!/usr/bin/env python3
"""Git state utilities for scribe — capture commit hash.

Requires Python 3.9+ (uses built-in generic types).
"""

import argparse
import subprocess
import sys


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


def main():
    parser = argparse.ArgumentParser(description="Git state utilities for scribe")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # hash command
    hash_parser = subparsers.add_parser("hash", help="Print current HEAD commit hash (short)")
    hash_parser.set_defaults(func=cmd_hash)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
