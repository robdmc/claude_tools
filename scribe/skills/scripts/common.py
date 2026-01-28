#!/usr/bin/env python3
"""Shared utilities for scribe scripts.

Requires Python 3.9+ (uses built-in generic types like list[str], dict[str, Any]).
"""

import re
from pathlib import Path
from typing import Any

import yaml

# Entry ID pattern: YYYY-MM-DD-HH-MM with optional -NN suffix (zero-padded)
# Examples: 2026-01-23-14-35, 2026-01-23-14-35-02
ENTRY_ID_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}(-\d{2,})?$")

# Looser pattern for extracting IDs from HTML comments (captures the ID portion)
# Legacy format - kept for backwards compatibility
ENTRY_ID_COMMENT_PATTERN = re.compile(r"<!-- id: (\d{4}-\d{2}-\d{2}-\d{2}-\d{2}(?:-\d{2,})?) -->")

# YAML frontmatter pattern for new format
FRONTMATTER_PATTERN = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def parse_entry_frontmatter(entry: str) -> dict[str, Any]:
    """Extract frontmatter from entry. Returns dict with id, mode, git, diff, etc."""
    match = FRONTMATTER_PATTERN.match(entry)
    if match:
        return yaml.safe_load(match.group(1)) or {}
    return {}


def find_scribe_dir() -> Path | None:
    """Find the .scribe directory in the current working directory.

    Returns the Path to .scribe/ if it exists, otherwise None.
    """
    scribe_dir = Path.cwd() / ".scribe"
    if scribe_dir.exists():
        return scribe_dir
    return None


def require_scribe_dir() -> Path:
    """Find .scribe directory or exit with error.

    Use this in commands that require the directory to exist.
    """
    import sys

    scribe_dir = find_scribe_dir()
    if not scribe_dir:
        print("Error: .scribe directory not found", file=sys.stderr)
        sys.exit(1)
    return scribe_dir
