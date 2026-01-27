#!/usr/bin/env python3
"""Import a Claude Code session to the current project.

Copies session files to make them available for /resume in a different project.

Safety features:
- Backs up sessions-index.json before modifying
- Validates JSON structure before and after writing
- Uses atomic writes (temp file + rename)
- Dry-run mode to preview changes
- Finds existing project directory instead of creating new ones
- Tracks imports in .claude_history_imports.json for easy cleanup
"""

import argparse
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

MANIFEST_FILENAME = ".claude_history_imports.json"


def get_claude_projects_dir() -> Path:
    """Get the Claude projects directory."""
    return Path.home() / ".claude" / "projects"


def load_manifest(project_path: str) -> dict:
    """Load the imports manifest from a project directory."""
    manifest_path = Path(project_path) / MANIFEST_FILENAME
    if manifest_path.exists():
        try:
            with open(manifest_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"imports": []}


def save_manifest(project_path: str, manifest: dict) -> None:
    """Save the imports manifest to a project directory."""
    manifest_path = Path(project_path) / MANIFEST_FILENAME
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)


def add_to_manifest(project_path: str, import_record: dict) -> None:
    """Add an import record to the manifest."""
    manifest = load_manifest(project_path)
    manifest["imports"].append(import_record)
    save_manifest(project_path, manifest)


def remove_from_manifest(project_path: str, session_id: str) -> Optional[dict]:
    """Remove an import record from the manifest.

    Returns the removed record, or None if not found.
    """
    manifest = load_manifest(project_path)
    for i, record in enumerate(manifest["imports"]):
        if record.get("session_id", "").startswith(session_id):
            removed = manifest["imports"].pop(i)
            save_manifest(project_path, manifest)
            return removed
    return None


def find_existing_project_dir(target_path: str) -> Optional[Path]:
    """Find an existing Claude project directory for the given path.

    Claude Code creates directories with path encoding, but the exact encoding
    can vary. This finds an existing directory that matches the target path
    by checking the originalPath in sessions-index.json.
    """
    projects_dir = get_claude_projects_dir()
    if not projects_dir.exists():
        return None

    target_resolved = str(Path(target_path).resolve())

    for index_file in projects_dir.glob("*/sessions-index.json"):
        try:
            with open(index_file, "r") as f:
                data = json.load(f)

            # Check if originalPath matches our target
            original_path = data.get("originalPath", "")
            if original_path and str(Path(original_path).resolve()) == target_resolved:
                return index_file.parent
        except (json.JSONDecodeError, IOError):
            continue

    return None


def encode_project_path(path: str) -> str:
    """Encode project path to directory name.

    /Users/rob/project -> -Users-rob-project
    """
    abs_path = str(Path(path).resolve())
    return abs_path.replace("/", "-")


def find_session(session_id: str) -> Optional[Tuple[Path, dict, Path]]:
    """Find a session by ID.

    Returns:
        Tuple of (project_dir, session_entry, jsonl_path) or None
    """
    projects_dir = get_claude_projects_dir()
    if not projects_dir.exists():
        return None

    for index_file in projects_dir.glob("*/sessions-index.json"):
        project_dir = index_file.parent

        try:
            with open(index_file, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    sessions = data.get("entries", [])
                else:
                    sessions = data
        except (json.JSONDecodeError, IOError):
            continue

        for session in sessions:
            sid = session.get("sessionId", "")
            if sid == session_id or sid.startswith(session_id):
                jsonl_path = project_dir / f"{sid}.jsonl"
                if jsonl_path.exists():
                    return (project_dir, session, jsonl_path)

    return None


def validate_session_entry(entry: dict) -> list[str]:
    """Validate a session entry has required fields.

    Returns list of error messages (empty if valid).
    """
    errors = []
    required = ["sessionId"]
    for field in required:
        if not entry.get(field):
            errors.append(f"Missing required field: {field}")

    # Validate sessionId format (UUID-like)
    sid = entry.get("sessionId", "")
    if sid and len(sid) < 8:
        errors.append(f"sessionId too short: {sid}")

    return errors


def validate_index_structure(data: dict) -> list[str]:
    """Validate sessions-index.json structure.

    Returns list of error messages (empty if valid).
    """
    errors = []

    if not isinstance(data, dict):
        errors.append("Index must be a dict")
        return errors

    if "entries" not in data:
        errors.append("Index missing 'entries' field")
        return errors

    if not isinstance(data["entries"], list):
        errors.append("'entries' must be a list")
        return errors

    for i, entry in enumerate(data["entries"]):
        if not isinstance(entry, dict):
            errors.append(f"Entry {i} is not a dict")
            continue
        entry_errors = validate_session_entry(entry)
        for err in entry_errors:
            errors.append(f"Entry {i}: {err}")

    return errors


def atomic_write_json(path: Path, data: dict) -> None:
    """Write JSON atomically using temp file + rename."""
    # Write to temp file in same directory (for atomic rename)
    fd, tmp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=".sessions-index-",
        suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)

        # Validate what we just wrote
        with open(tmp_path, "r") as f:
            reloaded = json.load(f)

        errors = validate_index_structure(reloaded)
        if errors:
            raise ValueError(f"Validation failed after write: {errors}")

        # Atomic rename
        os.rename(tmp_path, path)
    except:
        # Clean up temp file on error
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def backup_index(index_path: Path) -> Optional[Path]:
    """Create a backup of sessions-index.json.

    Returns backup path, or None if source doesn't exist.
    """
    if not index_path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = index_path.parent / f".sessions-index.backup.{timestamp}.json"
    shutil.copy2(index_path, backup_path)
    return backup_path


def import_session(session_id: str, target_path: str, dry_run: bool = False) -> dict:
    """Import a session to the target project.

    Args:
        session_id: The session ID to import
        target_path: The target project path
        dry_run: If True, show what would happen without making changes

    Returns:
        Dict with success status and message
    """
    # Find the source session
    result = find_session(session_id)
    if not result:
        return {
            "success": False,
            "error": f"Could not find session {session_id}"
        }

    source_dir, session_entry, source_jsonl = result
    full_session_id: str = session_entry.get("sessionId", "")

    # Validate source session entry
    entry_errors = validate_session_entry(session_entry)
    if entry_errors:
        return {
            "success": False,
            "error": f"Source session has invalid structure: {entry_errors}"
        }

    # Find existing target directory or determine where to create one
    projects_dir = get_claude_projects_dir()
    target_dir = find_existing_project_dir(target_path)
    creating_new_dir = False

    if target_dir is None:
        # No existing directory - we'll need to create one
        target_encoded = encode_project_path(target_path)
        target_dir = projects_dir / target_encoded
        creating_new_dir = True

    # Check if source and target are the same
    if source_dir.resolve() == target_dir.resolve():
        return {
            "success": False,
            "error": "Session is already in the target project"
        }

    target_index = target_dir / "sessions-index.json"

    # Prepare the new entry
    new_entry = session_entry.copy()
    new_entry["fullPath"] = str(target_dir / f"{full_session_id}.jsonl")
    new_entry["projectPath"] = target_path

    # Validate new entry
    entry_errors = validate_session_entry(new_entry)
    if entry_errors:
        return {
            "success": False,
            "error": f"New entry would be invalid: {entry_errors}"
        }

    source_project = session_entry.get("projectPath", str(source_dir))

    # Dry run - just report what would happen
    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "session_id": full_session_id,
            "source": str(source_jsonl),
            "source_project": source_project,
            "target": str(target_dir / f"{full_session_id}.jsonl"),
            "target_index_dir": str(target_dir),
            "would_create_dir": creating_new_dir,
            "replaces_existing": target_index.exists(),
            "message": f"Would import session {full_session_id[:8]}... to {target_path} (replaces existing history)"
        }

    # Create target directory if needed
    target_dir.mkdir(parents=True, exist_ok=True)

    # Copy JSONL file
    target_jsonl = target_dir / f"{full_session_id}.jsonl"
    shutil.copy2(source_jsonl, target_jsonl)

    # Copy subagent directory if exists
    source_subagent_dir = source_dir / full_session_id
    target_subagent_dir = None
    if source_subagent_dir.exists() and source_subagent_dir.is_dir():
        target_subagent_dir = target_dir / full_session_id
        if target_subagent_dir.exists():
            shutil.rmtree(target_subagent_dir)
        shutil.copytree(source_subagent_dir, target_subagent_dir)

    # Update sessions-index.json with backup and atomic write
    backup_path = backup_index(target_index)

    # Replace sessions-index.json with only the imported session
    # (existing JSONL files stay on disk, just not in the index)
    target_data: dict = {
        "version": 1,
        "entries": [new_entry],  # Only the imported session
        "originalPath": target_path
    }

    # Validate before writing
    errors = validate_index_structure(target_data)
    if errors:
        # Clean up copied files
        if target_jsonl.exists():
            target_jsonl.unlink()
        return {
            "success": False,
            "error": f"Would create invalid index: {errors}"
        }

    # Atomic write
    try:
        atomic_write_json(target_index, target_data)
    except Exception as e:
        # Clean up copied files
        if target_jsonl.exists():
            target_jsonl.unlink()
        return {
            "success": False,
            "error": f"Failed to write index: {e}",
            "backup": str(backup_path) if backup_path else None
        }

    # Record in manifest for later cleanup
    import_record = {
        "session_id": full_session_id,
        "source_project": source_project,
        "imported_at": datetime.now().isoformat(),
        "target_jsonl": str(target_jsonl),
        "target_subagent_dir": str(target_subagent_dir) if target_subagent_dir else None,
        "target_index_dir": str(target_dir),
        "summary": session_entry.get("summary", "")
    }
    add_to_manifest(target_path, import_record)

    return {
        "success": True,
        "session_id": full_session_id,
        "source_project": source_project,
        "target_project": target_path,
        "summary": session_entry.get("summary", ""),
        "backup": str(backup_path) if backup_path else None,
        "message": f"Imported session {full_session_id[:8]}... to {target_path}. Use /resume to continue."
    }


def unimport_session(session_id: str, target_path: str, dry_run: bool = False) -> dict:
    """Remove an imported session from the target project.

    Args:
        session_id: The session ID to remove (or prefix)
        target_path: The target project path
        dry_run: If True, show what would happen without making changes

    Returns:
        Dict with success status and message
    """
    manifest = load_manifest(target_path)

    # Find the import record
    record = None
    for r in manifest["imports"]:
        if r.get("session_id", "").startswith(session_id):
            record = r
            break

    if not record:
        return {
            "success": False,
            "error": f"No import record found for session {session_id}. Use --list-imports to see imported sessions."
        }

    full_session_id = record["session_id"]
    target_jsonl = Path(record["target_jsonl"])
    target_subagent_dir = Path(record["target_subagent_dir"]) if record.get("target_subagent_dir") else None
    target_index_dir = Path(record["target_index_dir"])
    target_index = target_index_dir / "sessions-index.json"

    if dry_run:
        files_to_delete = [str(target_jsonl)]
        if target_subagent_dir:
            files_to_delete.append(str(target_subagent_dir) + "/")
        return {
            "success": True,
            "dry_run": True,
            "session_id": full_session_id,
            "files_to_delete": files_to_delete,
            "message": f"Would remove imported session {full_session_id[:8]}..."
        }

    # Backup index before modifying
    backup_path = backup_index(target_index)

    # Remove from sessions-index.json
    if target_index.exists():
        try:
            with open(target_index, "r") as f:
                data = json.load(f)

            if isinstance(data, dict) and "entries" in data:
                data["entries"] = [
                    e for e in data["entries"]
                    if e.get("sessionId") != full_session_id
                ]
                atomic_write_json(target_index, data)
        except (json.JSONDecodeError, IOError) as e:
            return {
                "success": False,
                "error": f"Failed to update sessions-index.json: {e}",
                "backup": str(backup_path) if backup_path else None
            }

    # Delete JSONL file
    if target_jsonl.exists():
        target_jsonl.unlink()

    # Delete subagent directory
    if target_subagent_dir and target_subagent_dir.exists():
        shutil.rmtree(target_subagent_dir)

    # Remove from manifest
    remove_from_manifest(target_path, session_id)

    return {
        "success": True,
        "session_id": full_session_id,
        "backup": str(backup_path) if backup_path else None,
        "message": f"Removed imported session {full_session_id[:8]}..."
    }


def list_imports(target_path: str) -> dict:
    """List all imported sessions in a project.

    Returns:
        Dict with list of imports
    """
    manifest = load_manifest(target_path)
    return {
        "success": True,
        "imports": manifest["imports"],
        "total": len(manifest["imports"])
    }


def main():
    parser = argparse.ArgumentParser(description="Import/manage Claude Code sessions")
    parser.add_argument("session_id", nargs="?", help="Session ID to import or unimport")
    parser.add_argument("--target", "-t", default=os.getcwd(),
                        help="Target project path (default: current directory)")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Show what would happen without making changes")
    parser.add_argument("--unimport", "-u", action="store_true",
                        help="Remove an imported session")
    parser.add_argument("--list-imports", "-l", action="store_true",
                        help="List all imported sessions")
    parser.add_argument("--json", "-j", action="store_true", help="Output JSON")

    args = parser.parse_args()

    # Handle --list-imports
    if args.list_imports:
        result = list_imports(args.target)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            imports = result["imports"]
            if not imports:
                print("No imported sessions.")
            else:
                print(f"Imported sessions ({len(imports)}):\n")
                for imp in imports:
                    sid = imp["session_id"][:8]
                    source = Path(imp["source_project"]).name
                    date = imp["imported_at"][:10]
                    summary = imp.get("summary", "")[:60]
                    print(f"  {sid}...  from {source}  [{date}]")
                    if summary:
                        print(f"    {summary}")
                    print()
        return 0

    # Require session_id for import/unimport
    if not args.session_id:
        parser.error("session_id is required for import/unimport")

    # Handle --unimport
    if args.unimport:
        result = unimport_session(args.session_id, args.target, dry_run=args.dry_run)
    else:
        result = import_session(args.session_id, args.target, dry_run=args.dry_run)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            if result.get("dry_run"):
                print(f"[DRY RUN] {result['message']}")
                if "source" in result:
                    print(f"  Source: {result.get('source')}")
                    print(f"  Target: {result.get('target')}")
                    if result.get("would_create_dir"):
                        print("  Note: Would create new project directory")
                if "files_to_delete" in result:
                    print("  Would delete:")
                    for f in result["files_to_delete"]:
                        print(f"    - {f}")
            else:
                print(result["message"])
                if result.get("summary"):
                    print(f"Summary: {result['summary']}")
                if result.get("backup"):
                    print(f"Backup: {result['backup']}")
        else:
            print(f"Error: {result['error']}")
            return 1

    return 0


if __name__ == "__main__":
    exit(main())
