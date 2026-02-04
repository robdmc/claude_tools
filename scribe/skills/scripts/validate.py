#!/usr/bin/env python3
"""Validate scribe entries for consistency.

Requires Python 3.9+ (uses built-in generic types).
"""

import argparse
import re
import sys
from pathlib import Path

import yaml

from common import ENTRY_ID_PATTERN, FRONTMATTER_PATTERN, find_scribe_dir

# Pre-compiled regex patterns for performance
HEADER_PATTERN = re.compile(r"^## (\d{2}:\d{2}) — (.+)$", re.MULTILINE)
ID_PATTERN = re.compile(r"<!-- id: ([\d-]+) -->")
ARCHIVE_PATTERN = re.compile(r"\[`([^`]+)`\]\(assets/([^)]+)\)")
RELATED_SECTION_PATTERN = re.compile(r"\*\*Related:\*\*(.+?)(?=\n\n|\n\*\*|\n---|\Z)", re.DOTALL)
RELATED_ID_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}(?:-\d{2,})?)")
LOG_FILE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")


def extract_entries(log_file: Path) -> list[dict]:
    """Extract entries from a daily log file (both legacy and frontmatter formats)."""
    content = log_file.read_text()
    entries = []

    # Find all entry start positions
    # Frontmatter: ---\n followed by id: within ~200 chars (not a closing ---)
    # Legacy: ## HH:MM — Title

    entry_starts: list[tuple[str, int]] = []  # (format, position)

    # Find frontmatter entry starts
    # Must have valid YAML frontmatter with id: field
    frontmatter_ranges: list[tuple[int, int]] = []  # (start, end) of frontmatter blocks
    for match in re.finditer(r"^---\n", content, re.MULTILINE):
        pos = match.start()
        snippet = content[pos:pos + 500]
        # Check if this is valid frontmatter (has closing --- and id: field)
        fm_match = FRONTMATTER_PATTERN.match(snippet)
        if fm_match:
            fm_yaml = fm_match.group(1)
            # YAML content shouldn't start with --- (that would mean we matched wrong)
            if fm_yaml.startswith("---"):
                continue
            if re.search(r"^id:\s*\d{4}-\d{2}-\d{2}", fm_yaml, re.MULTILINE):
                entry_starts.append(("frontmatter", pos))
                # Track where frontmatter ends (after closing ---)
                frontmatter_ranges.append((pos, pos + fm_match.end()))

    # Find legacy entry starts (but not if they're inside a frontmatter block)
    for match in HEADER_PATTERN.finditer(content):
        pos = match.start()
        # Skip if this header is inside/immediately after a frontmatter entry
        inside_frontmatter = any(start <= pos <= end for start, end in frontmatter_ranges)
        if not inside_frontmatter:
            entry_starts.append(("legacy", pos))

    # Sort by position
    entry_starts.sort(key=lambda x: x[1])

    # Extract each entry
    for i, (fmt, start_pos) in enumerate(entry_starts):
        # Entry ends at next entry start or end of file
        if i + 1 < len(entry_starts):
            end_pos = entry_starts[i + 1][1]
        else:
            end_pos = len(content)

        entry_content = content[start_pos:end_pos]

        if fmt == "frontmatter":
            fm_match = FRONTMATTER_PATTERN.match(entry_content)
            if fm_match:
                fm_data = yaml.safe_load(fm_match.group(1)) or {}
                entry_id = fm_data.get("id")
                title = fm_data.get("title", "")
                time = fm_data.get("timestamp", "")
                git_hash = fm_data.get("git")
                git_mode = fm_data.get("mode")
                body = entry_content[fm_match.end():]

                archived = ARCHIVE_PATTERN.findall(body)
                related = []
                related_section_match = RELATED_SECTION_PATTERN.search(body)
                if related_section_match:
                    related = RELATED_ID_PATTERN.findall(related_section_match.group(1))

                entries.append({
                    "file": log_file.name,
                    "time": time,
                    "title": title,
                    "id": entry_id,
                    "archived": archived,
                    "related": related,
                    "git": git_hash,
                    "mode": git_mode,
                    "format": "frontmatter",
                })
        else:
            # Legacy format
            header_match = HEADER_PATTERN.match(entry_content)
            if header_match:
                time = header_match.group(1)
                title = header_match.group(2)
                body = entry_content[header_match.end():]

                id_match = ID_PATTERN.search(body)
                entry_id = id_match.group(1) if id_match else None

                archived = ARCHIVE_PATTERN.findall(body)
                related = []
                related_section_match = RELATED_SECTION_PATTERN.search(body)
                if related_section_match:
                    related = RELATED_ID_PATTERN.findall(related_section_match.group(1))

                entries.append({
                    "file": log_file.name,
                    "time": time,
                    "title": title,
                    "id": entry_id,
                    "archived": archived,
                    "related": related,
                    "git": None,
                    "mode": None,
                    "format": "legacy",
                })

    return entries


def validate(scribe_dir: Path, since_id: str | None = None) -> tuple[list[str], int]:
    """Validate entries and return (errors, entry_count).

    If since_id is provided, only validate entries after that ID (incremental).
    """
    errors = []
    assets_dir = scribe_dir / "assets"

    log_files = [f for f in scribe_dir.iterdir() if LOG_FILE_PATTERN.match(f.name)]

    # For incremental validation, filter to relevant files
    if since_id:
        since_date = since_id[:10]  # YYYY-MM-DD portion
        log_files = [f for f in log_files if f.stem >= since_date]

    all_entries = []

    for log_file in sorted(log_files):
        entries = extract_entries(log_file)

        # For incremental, filter entries
        if since_id:
            entries = [e for e in entries if e["id"] and e["id"] > since_id]

        all_entries.extend(entries)

        for entry in entries:
            # Check entry ID
            if not entry["id"]:
                errors.append(
                    f"✗ {log_file.name} [{entry['time']}] \"{entry['title']}\" — missing entry ID"
                )
            elif not ENTRY_ID_PATTERN.match(entry["id"]):
                errors.append(
                    f"✗ {log_file.name} [{entry['time']}] — invalid entry ID format: {entry['id']}"
                )

            # Check archived assets exist
            for _, asset_path in entry["archived"]:
                asset_file = assets_dir / asset_path
                if not asset_file.exists():
                    errors.append(
                        f"✗ {log_file.name} [{entry['time']}] — references {asset_path} but file not found"
                    )

            # Check git-entry has commit hash
            if entry["mode"] == "git-entry" and not entry["git"]:
                errors.append(
                    f"✗ {log_file.name} [{entry['time']}] — git-entry mode but no git commit hash"
                )

    # For full validation, also check Related references and orphaned assets
    if not since_id:
        all_entry_ids = {entry["id"] for entry in all_entries if entry["id"]}

        for entry in all_entries:
            for related_id in entry.get("related", []):
                if related_id not in all_entry_ids:
                    errors.append(
                        f"✗ {entry['file']} [{entry['time']}] — Related references {related_id} but entry not found"
                    )

        # Check for orphaned assets
        if assets_dir.exists():
            referenced_assets = set()
            for entry in all_entries:
                for _, asset_path in entry["archived"]:
                    referenced_assets.add(asset_path)

            for asset_file in assets_dir.iterdir():
                if asset_file.name not in referenced_assets:
                    errors.append(
                        f"✗ Orphaned asset: {asset_file.name} — no entry references it"
                    )

    return errors, len(all_entries)


def main():
    parser = argparse.ArgumentParser(description="Validate scribe entries")
    parser.add_argument("--since", help="Only validate entries after this ID (incremental)")
    parser.add_argument("--quiet", "-q", action="store_true", help="Only output errors")
    args = parser.parse_args()

    scribe_dir = find_scribe_dir()

    if not scribe_dir or not scribe_dir.exists():
        print("Error: .scribe directory not found", file=sys.stderr)
        sys.exit(1)

    errors, entry_count = validate(scribe_dir, since_id=args.since)

    if errors:
        for error in errors:
            print(error)
        sys.exit(1)
    elif not args.quiet:
        if args.since:
            print(f"✓ {entry_count} new entries validated (since {args.since})")
        else:
            print(f"✓ {entry_count} entries validated")
    sys.exit(0)


if __name__ == "__main__":
    main()
