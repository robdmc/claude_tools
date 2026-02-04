#!/usr/bin/env python3
"""Manage scribe log entries — prepare, finalize, and edit entries.

Requires Python 3.9+ (uses built-in generic types).
"""

import argparse
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

from common import (
    ENTRY_ID_PATTERN,
    ENTRY_ID_COMMENT_PATTERN,
    FRONTMATTER_PATTERN,
    find_scribe_dir,
)

# Pre-compiled regex patterns for performance
HEADER_WITH_TIME_PATTERN = re.compile(r"^## (\d{2}:\d{2}) — .+$", re.MULTILINE)
HEADER_SIMPLE_PATTERN = re.compile(r"^## (.+)$", re.MULTILINE)
LOG_FILE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")
TIME_FORMAT_PATTERN = re.compile(r"^\d{2}:\d{2}$")
STAGING_FILE_PATTERN = re.compile(r"^__(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}(?:-\d{2,})?)__\.md$")

# Pattern for extracting ID from YAML frontmatter
FRONTMATTER_ID_PATTERN = re.compile(r"^id:\s*(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}(?:-\d{2,})?)\s*$", re.MULTILINE)

# Placeholders
TITLE_PLACEHOLDER = "__TITLE__"
BODY_PLACEHOLDER = "__BODY__"


def run_git(*args: str) -> tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def get_git_hash() -> str | None:
    """Get the current HEAD commit hash (short form)."""
    returncode, stdout, _ = run_git("rev-parse", "--short", "HEAD")
    if returncode != 0:
        return None
    return stdout


def ensure_scribe_dir() -> Path:
    """Ensure .scribe directory exists with proper structure and .gitignore."""
    scribe_dir = Path.cwd() / ".scribe"

    # Create directories
    scribe_dir.mkdir(exist_ok=True)
    (scribe_dir / "assets").mkdir(exist_ok=True)
    # Keep diffs dir for backwards compatibility (legacy files)
    (scribe_dir / "diffs").mkdir(exist_ok=True)

    # Update .gitignore
    gitignore_path = Path.cwd() / ".gitignore"
    patterns_needed = [
        ".scribe/diffs/",
        ".scribe/assets/",
        ".scribe/__*__.md",
        "_20*-*",
    ]

    existing_patterns = set()
    if gitignore_path.exists():
        existing_patterns = set(gitignore_path.read_text().splitlines())

    patterns_to_add = [p for p in patterns_needed if p not in existing_patterns]

    if patterns_to_add:
        with open(gitignore_path, "a") as f:
            if existing_patterns and not gitignore_path.read_text().endswith("\n"):
                f.write("\n")
            for pattern in patterns_to_add:
                f.write(f"{pattern}\n")

    return scribe_dir


def get_existing_ids(log_file: Path) -> set[str]:
    """Extract all entry IDs from a log file (both legacy and frontmatter formats)."""
    if not log_file.exists():
        return set()
    content = log_file.read_text()
    # Get IDs from both legacy HTML comments and YAML frontmatter
    legacy_ids = set(ENTRY_ID_COMMENT_PATTERN.findall(content))
    frontmatter_ids = set(FRONTMATTER_ID_PATTERN.findall(content))
    return legacy_ids | frontmatter_ids


def generate_entry_id(log_file: Path, time_str: str) -> str:
    """Generate a unique entry ID for the given time."""
    today = datetime.now().strftime("%Y-%m-%d")
    base_id = f"{today}-{time_str.replace(':', '-')}"

    existing_ids = get_existing_ids(log_file)

    if base_id not in existing_ids:
        return base_id

    # Handle collisions with zero-padded suffix
    suffix = 2
    while f"{base_id}-{suffix:02d}" in existing_ids:
        suffix += 1

    return f"{base_id}-{suffix:02d}"


def find_staging_file(scribe_dir: Path) -> Path | None:
    """Find the staging file in .scribe/ directory."""
    for f in scribe_dir.iterdir():
        if STAGING_FILE_PATTERN.match(f.name):
            return f
    return None


def lookup_entry_title(scribe_dir: Path, entry_id: str) -> str | None:
    """Look up the title for an entry ID."""
    # Extract date from ID
    date_part = entry_id[:10]  # YYYY-MM-DD
    log_file = scribe_dir / f"{date_part}.md"

    if not log_file.exists():
        return None

    content = log_file.read_text()

    # Try frontmatter format
    pattern = re.compile(rf"id:\s*{re.escape(entry_id)}\s*\n.*?title:\s*(.+?)\s*\n", re.DOTALL)
    match = pattern.search(content)
    if match:
        return match.group(1).strip()

    # Try legacy format
    legacy_pattern = re.compile(rf"^## (\d{{2}}:\d{{2}}) — (.+)$\n<!-- id: {re.escape(entry_id)} -->", re.MULTILINE)
    match = legacy_pattern.search(content)
    if match:
        return match.group(2).strip()

    return None


def find_latest_entry(scribe_dir: Path) -> tuple[Path, str | None, str, int, int] | None:
    """Find the latest entry across all log files.

    Returns (log_file, entry_id, entry_content, start_pos, end_pos) or None.
    Handles both legacy (HTML comment) and new (YAML frontmatter) formats.
    """
    log_files = sorted(
        [f for f in scribe_dir.iterdir() if LOG_FILE_PATTERN.match(f.name)],
        reverse=True
    )

    if not log_files:
        return None

    for log_file in log_files:
        content = log_file.read_text()

        # Find all entry start positions (both formats)
        # New format: entries start with ---\n (frontmatter)
        # Legacy format: entries start with ## HH:MM
        entry_starts = []

        # Find frontmatter entries
        for match in re.finditer(r"^---\n", content, re.MULTILINE):
            # Make sure this is an entry frontmatter, not just any ---
            pos = match.start()
            # Check if there's an id: field in the next few lines
            snippet = content[pos:pos + 200]
            if FRONTMATTER_ID_PATTERN.search(snippet):
                entry_starts.append(("frontmatter", pos))

        # Find legacy entries
        for match in HEADER_WITH_TIME_PATTERN.finditer(content):
            entry_starts.append(("legacy", match.start()))

        if not entry_starts:
            continue

        # Sort by position and get the last one
        entry_starts.sort(key=lambda x: x[1])
        entry_type, start_pos = entry_starts[-1]
        end_pos = len(content)
        entry_content = content[start_pos:end_pos]

        # Extract entry ID based on format
        if entry_type == "frontmatter":
            fm_match = FRONTMATTER_PATTERN.match(entry_content)
            if fm_match:
                fm_data = yaml.safe_load(fm_match.group(1)) or {}
                entry_id = fm_data.get("id")
            else:
                entry_id = None
        else:
            id_match = ENTRY_ID_COMMENT_PATTERN.search(entry_content)
            entry_id = id_match.group(1) if id_match else None

        return (log_file, entry_id, entry_content, start_pos, end_pos)

    return None


def delete_assets_for_entry(scribe_dir: Path, entry_id: str) -> list[str]:
    """Delete all assets associated with an entry ID."""
    assets_dir = scribe_dir / "assets"
    if not assets_dir.exists():
        return []

    deleted = []
    for asset in assets_dir.iterdir():
        if asset.name.startswith(f"{entry_id}-"):
            asset.unlink()
            deleted.append(asset.name)

    return deleted


def delete_diff_for_entry(scribe_dir: Path, entry_id: str) -> str | None:
    """Delete the diff file associated with an entry ID."""
    diffs_dir = scribe_dir / "diffs"
    if not diffs_dir.exists():
        return None

    diff_file = diffs_dir / f"{entry_id}.diff"
    if diff_file.exists():
        diff_file.unlink()
        return diff_file.name

    return None


def quick_validate(_scribe_dir: Path, entry_id: str) -> list[str]:
    """Quick validation for a single entry. Returns list of errors."""
    errors = []

    # Validate ID format
    if not ENTRY_ID_PATTERN.match(entry_id):
        errors.append(f"Invalid entry ID format: {entry_id}")

    return errors


def cmd_prepare(args):
    """Create a staging file for a new entry."""
    scribe_dir = ensure_scribe_dir()

    # Check for existing staging file
    existing = find_staging_file(scribe_dir)
    if existing:
        print(f"Error: Pending entry exists: {existing.name}", file=sys.stderr)
        print("Run 'finalize' to complete it or 'abort' to discard it.", file=sys.stderr)
        sys.exit(1)

    # Get current time and generate entry ID
    time_str = datetime.now().strftime("%H:%M")
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = scribe_dir / f"{today}.md"
    entry_id = generate_entry_id(log_file, time_str)

    # Get git hash
    git_hash = get_git_hash()

    # Build pending metadata
    pending = {
        "git_entry": args.git_entry,
    }

    # Process archives
    archives = []
    if args.archive:
        for file_desc in args.archive:
            if ":" in file_desc:
                file_path, desc = file_desc.split(":", 1)
            else:
                file_path = file_desc
                desc = ""
            archives.append([file_path.strip(), desc.strip()])
    if archives:
        pending["archives"] = archives

    # Build frontmatter
    frontmatter_data = {
        "id": entry_id,
        "timestamp": time_str,
        "title": TITLE_PLACEHOLDER,
    }
    if git_hash:
        frontmatter_data["git"] = git_hash
    frontmatter_data["_pending"] = pending  # type: ignore[assignment]

    frontmatter = yaml.dump(frontmatter_data, default_flow_style=False, sort_keys=False, allow_unicode=True)

    # Build entry body sections
    sections = []

    # Files touched section
    if args.touched:
        touched_lines = []
        for file_desc in args.touched:
            if ":" in file_desc:
                file_path, desc = file_desc.split(":", 1)
                touched_lines.append(f"- `{file_path.strip()}` — {desc.strip()}")
            else:
                touched_lines.append(f"- `{file_desc.strip()}`")
        sections.append("**Files touched:**\n" + "\n".join(touched_lines))

    # Archived section
    if archives:
        archive_lines = []
        for file_path, desc in archives:
            filename = Path(file_path).name
            asset_name = f"{entry_id}-{filename}"
            line = f"- `{file_path}` → [`{asset_name}`](assets/{asset_name})"
            if desc:
                line += f" — {desc}"
            archive_lines.append(line)
        sections.append("**Archived:**\n" + "\n".join(archive_lines))

    # Related section
    if args.related:
        related_lines = []
        for related_id in args.related:
            title = lookup_entry_title(scribe_dir, related_id)
            if title:
                related_lines.append(f"{related_id} — {title}")
            else:
                related_lines.append(related_id)
        sections.append("**Related:** " + ", ".join(related_lines))

    # Build full entry
    sections_text = "\n\n".join(sections) if sections else ""

    entry_content = f"""---
{frontmatter}---
## {time_str} — {TITLE_PLACEHOLDER}

{BODY_PLACEHOLDER}

{sections_text}

---
"""

    # Write staging file
    staging_file = scribe_dir / f"__{entry_id}__.md"
    staging_file.write_text(entry_content)

    print(staging_file)


def cmd_finalize(_args):
    """Finalize a pending entry: validate, archive, append to daily log, optionally commit."""
    scribe_dir = find_scribe_dir()
    if not scribe_dir:
        print("Error: .scribe directory not found", file=sys.stderr)
        sys.exit(1)

    # Find staging file
    staging_file = find_staging_file(scribe_dir)
    if not staging_file:
        print("Error: No pending entry. Run 'prepare' first.", file=sys.stderr)
        sys.exit(1)

    content = staging_file.read_text()

    # Check for placeholders
    if TITLE_PLACEHOLDER in content:
        print(f"Error: Title placeholder ({TITLE_PLACEHOLDER}) not replaced", file=sys.stderr)
        sys.exit(1)
    if BODY_PLACEHOLDER in content:
        print(f"Error: Body placeholder ({BODY_PLACEHOLDER}) not replaced", file=sys.stderr)
        sys.exit(1)

    # Parse frontmatter
    fm_match = FRONTMATTER_PATTERN.match(content)
    if not fm_match:
        print("Error: Invalid staging file (no frontmatter)", file=sys.stderr)
        sys.exit(1)

    fm_data = yaml.safe_load(fm_match.group(1)) or {}
    entry_id = fm_data.get("id")
    pending = fm_data.pop("_pending", {})

    git_entry_mode = pending.get("git_entry", False)
    archives = pending.get("archives", [])

    # If git-entry mode, create commit first
    if git_entry_mode:
        # Stage modified tracked files
        returncode, _, stderr = run_git("add", "-u")
        if returncode != 0:
            print(f"Error staging files: {stderr}", file=sys.stderr)
            sys.exit(1)

        # Check if there's anything staged
        returncode, _, _ = run_git("diff", "--cached", "--quiet")
        if returncode == 0:
            print("Error: No changes staged for git-entry mode", file=sys.stderr)
            sys.exit(1)

        # Get title for commit message
        title = fm_data.get("title", "Scribe entry")

        # Create commit
        commit_message = f"{title}\n\n{content}"
        returncode, stdout, stderr = run_git("commit", "-m", commit_message)
        if returncode != 0:
            print(f"Error creating commit: {stderr}", file=sys.stderr)
            sys.exit(1)

        # Get new commit hash
        new_hash = get_git_hash()
        if new_hash:
            fm_data["git"] = new_hash
        fm_data["mode"] = "git-entry"

        print(f"Created commit: {new_hash}")

    # Archive files
    if archives:
        assets_dir = scribe_dir / "assets"
        assets_dir.mkdir(exist_ok=True)

        for file_path, _desc in archives:
            src = Path(file_path)
            if not src.exists():
                print(f"Warning: File not found for archive: {file_path}", file=sys.stderr)
                continue

            filename = src.name
            asset_name = f"{entry_id}-{filename}"
            dest = assets_dir / asset_name

            if dest.exists():
                print(f"Warning: Asset already exists: {asset_name}", file=sys.stderr)
                continue

            shutil.copy(src, dest)
            print(f"Archived: {asset_name}")

    # Rebuild frontmatter without _pending
    new_frontmatter = yaml.dump(fm_data, default_flow_style=False, sort_keys=False, allow_unicode=True)

    # Replace frontmatter in content
    body_after_frontmatter = content[fm_match.end():]
    final_content = f"---\n{new_frontmatter}---\n{body_after_frontmatter}"

    # Append to daily log
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = scribe_dir / f"{today}.md"

    if not log_file.exists():
        log_file.write_text(f"# {today}\n\n---\n\n")

    with open(log_file, "a") as f:
        f.write(final_content)
        if not final_content.endswith("\n"):
            f.write("\n")

    # Validate
    if entry_id:
        errors = quick_validate(scribe_dir, entry_id)
    else:
        errors = ["Entry has no ID"]
    if errors:
        for error in errors:
            print(f"Warning: {error}", file=sys.stderr)

    # Delete staging file
    staging_file.unlink()

    print(f"Entry finalized: {entry_id}")


def cmd_abort(_args):
    """Abort a pending entry by deleting the staging file."""
    scribe_dir = find_scribe_dir()
    if not scribe_dir:
        print("Error: .scribe directory not found", file=sys.stderr)
        sys.exit(1)

    staging_file = find_staging_file(scribe_dir)
    if not staging_file:
        print("No pending entry to abort.")
        return

    # Parse to get entry ID for message
    content = staging_file.read_text()
    fm_match = FRONTMATTER_PATTERN.match(content)
    entry_id = None
    if fm_match:
        fm_data = yaml.safe_load(fm_match.group(1)) or {}
        entry_id = fm_data.get("id")

    staging_file.unlink()

    if entry_id:
        print(f"Aborted pending entry: {entry_id}")
    else:
        print("Aborted pending entry")


def cmd_status(_args):
    """Show the status of any pending entry."""
    scribe_dir = find_scribe_dir()
    if not scribe_dir:
        print("No .scribe directory")
        return

    staging_file = find_staging_file(scribe_dir)
    if not staging_file:
        print("No pending entry")
        return

    content = staging_file.read_text()
    fm_match = FRONTMATTER_PATTERN.match(content)

    if fm_match:
        fm_data = yaml.safe_load(fm_match.group(1)) or {}
        entry_id = fm_data.get("id", "unknown")
        pending = fm_data.get("_pending", {})

        print(f"Pending entry: {entry_id}")
        print(f"Staging file: {staging_file.name}")

        # Check placeholder status
        has_title = TITLE_PLACEHOLDER not in content
        has_body = BODY_PLACEHOLDER not in content
        print(f"Title filled: {'yes' if has_title else 'no'}")
        print(f"Body filled: {'yes' if has_body else 'no'}")

        if pending.get("git_entry"):
            print("Mode: git-entry")
        if pending.get("archives"):
            print(f"Archives: {len(pending['archives'])} file(s)")
    else:
        print(f"Pending staging file: {staging_file.name} (invalid format)")


def cmd_last(args):
    """Show the last entry ID from today's log."""
    scribe_dir = find_scribe_dir()
    if not scribe_dir:
        print("Error: .scribe directory not found", file=sys.stderr)
        sys.exit(1)

    today = datetime.now().strftime("%Y-%m-%d")
    log_file = scribe_dir / f"{today}.md"

    existing_ids = get_existing_ids(log_file)
    if not existing_ids:
        print("No entries today")
        return

    last_id = sorted(existing_ids)[-1]

    if args.with_title:
        title = lookup_entry_title(scribe_dir, last_id)
        if title:
            print(f"{last_id} — {title}")
        else:
            print(last_id)
    else:
        print(last_id)


def cmd_edit_latest_show(_args):
    """Display the latest entry."""
    scribe_dir = find_scribe_dir()
    if not scribe_dir:
        print("Error: .scribe directory not found", file=sys.stderr)
        sys.exit(1)

    result = find_latest_entry(scribe_dir)
    if not result:
        print("No entries found")
        return

    log_file, entry_id, entry_content, _, _ = result
    print(f"Latest entry from {log_file.name} (ID: {entry_id}):\n")
    print(entry_content)


def cmd_edit_latest_delete(_args):
    """Delete the latest entry and its associated assets and diffs."""
    scribe_dir = find_scribe_dir()
    if not scribe_dir:
        print("Error: .scribe directory not found", file=sys.stderr)
        sys.exit(1)

    result = find_latest_entry(scribe_dir)
    if not result:
        print("No entries found")
        return

    log_file, entry_id, _, start_pos, _ = result

    if entry_id:
        # Delete associated assets
        deleted_assets = delete_assets_for_entry(scribe_dir, entry_id)
        for asset in deleted_assets:
            print(f"Deleted asset: {asset}")

        # Delete associated diff file
        deleted_diff = delete_diff_for_entry(scribe_dir, entry_id)
        if deleted_diff:
            print(f"Deleted diff: {deleted_diff}")

    content = log_file.read_text()
    new_content = content[:start_pos].rstrip()

    if new_content and not new_content.endswith("\n"):
        new_content += "\n"

    log_file.write_text(new_content)
    print(f"Deleted entry: {entry_id}")


def cmd_edit_latest_replace(args):
    """Replace the latest entry with new content from file or stdin."""
    scribe_dir = find_scribe_dir()
    if not scribe_dir:
        print("Error: .scribe directory not found", file=sys.stderr)
        sys.exit(1)

    result = find_latest_entry(scribe_dir)
    if not result:
        print("No entries found")
        return

    log_file, old_entry_id, _, start_pos, _ = result

    if not old_entry_id:
        print("Error: Latest entry has no ID, cannot replace", file=sys.stderr)
        sys.exit(1)

    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        new_entry = file_path.read_text().strip()
    else:
        new_entry = sys.stdin.read().strip()

    if not new_entry:
        print("Error: No entry provided (use --file or pipe via stdin)", file=sys.stderr)
        sys.exit(1)

    time_str = datetime.now().strftime("%H:%M")

    legacy_match = HEADER_WITH_TIME_PATTERN.search(new_entry)
    if legacy_match:
        time_str = legacy_match.group(1)
        full_header = legacy_match.group(0)
        title = full_header.split(" — ", 1)[1] if " — " in full_header else "Untitled"
    else:
        header_match = HEADER_SIMPLE_PATTERN.search(new_entry)
        if not header_match:
            print("Error: Entry must start with '## Title'", file=sys.stderr)
            sys.exit(1)

        title = header_match.group(1)
        new_entry = re.sub(r"^## .+$", f"## {time_str} — {title}", new_entry, count=1, flags=re.MULTILINE)

    # Build frontmatter
    fm_data = {
        "id": old_entry_id,
        "timestamp": time_str,
        "title": title,
    }
    frontmatter = yaml.dump(fm_data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    new_entry_with_frontmatter = f"---\n{frontmatter}---\n{new_entry}"

    content = log_file.read_text()
    new_content = content[:start_pos] + new_entry_with_frontmatter
    if not new_content.endswith("\n"):
        new_content += "\n"

    log_file.write_text(new_content)
    print(f"Replaced entry: {old_entry_id}")


def cmd_edit_latest_rearchive(args):
    """Re-archive a file using the latest entry's ID."""
    scribe_dir = find_scribe_dir()
    if not scribe_dir:
        print("Error: .scribe directory not found", file=sys.stderr)
        sys.exit(1)

    result = find_latest_entry(scribe_dir)
    if not result:
        print("No entries found")
        return

    _, entry_id, _, _, _ = result
    if not entry_id:
        print("Error: Latest entry has no ID", file=sys.stderr)
        sys.exit(1)

    src = Path(args.file)
    if not src.exists():
        print(f"Error: {args.file} not found", file=sys.stderr)
        sys.exit(1)

    assets_dir = scribe_dir / "assets"
    assets_dir.mkdir(exist_ok=True)

    dest_name = f"{entry_id}-{src.name}"
    dest = assets_dir / dest_name

    if dest.exists():
        print(f"Error: {dest_name} already exists", file=sys.stderr)
        sys.exit(1)

    shutil.copy(src, dest)
    print(f"Archived: {dest_name}")


def cmd_edit_latest_unarchive(_args):
    """Delete all assets associated with the latest entry (but keep the entry)."""
    scribe_dir = find_scribe_dir()
    if not scribe_dir:
        print("Error: .scribe directory not found", file=sys.stderr)
        sys.exit(1)

    result = find_latest_entry(scribe_dir)
    if not result:
        print("No entries found")
        return

    _, entry_id, _, _, _ = result
    if not entry_id:
        print("Error: Latest entry has no ID", file=sys.stderr)
        sys.exit(1)

    deleted_assets = delete_assets_for_entry(scribe_dir, entry_id)

    if deleted_assets:
        for asset in deleted_assets:
            print(f"Deleted asset: {asset}")
    else:
        print(f"No assets found for entry {entry_id}")


def main():
    parser = argparse.ArgumentParser(description="Manage scribe log entries")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # prepare command
    prepare_parser = subparsers.add_parser("prepare", help="Create a staging file for a new entry")
    prepare_parser.add_argument("--git-entry", action="store_true", help="Create a git commit when finalizing")
    prepare_parser.add_argument("--touched", action="append", metavar="FILE:DESC",
                                help="File touched (repeatable). Format: 'file.py:description' or just 'file.py'")
    prepare_parser.add_argument("--archive", action="append", metavar="FILE:DESC",
                                help="File to archive (repeatable). Format: 'file.py:description' or just 'file.py'")
    prepare_parser.add_argument("--related", action="append", metavar="ID",
                                help="Related entry ID (repeatable). Title is looked up automatically.")
    prepare_parser.set_defaults(func=cmd_prepare)

    # finalize command
    finalize_parser = subparsers.add_parser("finalize", help="Finalize the pending entry")
    finalize_parser.set_defaults(func=cmd_finalize)

    # abort command
    abort_parser = subparsers.add_parser("abort", help="Abort the pending entry")
    abort_parser.set_defaults(func=cmd_abort)

    # status command
    status_parser = subparsers.add_parser("status", help="Show pending entry status")
    status_parser.set_defaults(func=cmd_status)

    # last command
    last_parser = subparsers.add_parser("last", help="Show the last entry ID from today")
    last_parser.add_argument("--with-title", action="store_true", help="Include entry title in output")
    last_parser.set_defaults(func=cmd_last)

    # edit-latest command with subcommands
    edit_parser = subparsers.add_parser("edit-latest", help="Edit the latest entry")
    edit_subparsers = edit_parser.add_subparsers(dest="edit_command", required=True)

    edit_show = edit_subparsers.add_parser("show", help="Display the latest entry")
    edit_show.set_defaults(func=cmd_edit_latest_show)

    edit_delete = edit_subparsers.add_parser("delete", help="Delete the latest entry and its assets/diffs")
    edit_delete.set_defaults(func=cmd_edit_latest_delete)

    edit_replace = edit_subparsers.add_parser("replace", help="Replace the latest entry (from file or stdin)")
    edit_replace.add_argument("--file", help="Read entry from file instead of stdin")
    edit_replace.set_defaults(func=cmd_edit_latest_replace)

    edit_rearchive = edit_subparsers.add_parser("rearchive", help="Re-archive a file for the latest entry")
    edit_rearchive.add_argument("file", help="File to archive")
    edit_rearchive.set_defaults(func=cmd_edit_latest_rearchive)

    edit_unarchive = edit_subparsers.add_parser("unarchive", help="Delete assets for the latest entry")
    edit_unarchive.set_defaults(func=cmd_edit_latest_unarchive)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
