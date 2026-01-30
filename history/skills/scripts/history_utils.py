#!/usr/bin/env python3
"""Shared utilities for Claude Code history scripts.

This module provides common functionality used across history-related scripts:
- Path handling for Claude projects directory
- Session discovery and lookup
- JSONL parsing utilities
- Index file handling
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Union


def get_claude_projects_dir() -> Path:
    """Get the Claude projects directory.

    Returns:
        Path to ~/.claude/projects
    """
    return Path.home() / ".claude" / "projects"


def decode_project_path(encoded: str) -> str:
    """Decode project path from directory name.

    Claude Code encodes paths by replacing / with -.

    Args:
        encoded: Directory name like "-Users-rob-project"

    Returns:
        Decoded path like "/Users/rob/project"

    Examples:
        >>> decode_project_path("-Users-rob-project")
        '/Users/rob/project'
        >>> decode_project_path("relative-path")
        'relative-path'
    """
    if encoded.startswith("-"):
        return encoded.replace("-", "/", 1).replace("-", "/")
    return encoded


def encode_project_path(path: str) -> str:
    """Encode project path to directory name.

    Args:
        path: Filesystem path like "/Users/rob/project"

    Returns:
        Encoded name like "-Users-rob-project"

    Examples:
        >>> encode_project_path("/Users/rob/project")
        '-Users-rob-project'
    """
    abs_path = str(Path(path).resolve())
    return abs_path.replace("/", "-")


def parse_jsonl(path: Path) -> list:
    """Parse a JSONL file into a list of messages.

    Args:
        path: Path to the JSONL file

    Returns:
        List of parsed JSON objects (one per line)

    Note:
        Invalid JSON lines are silently skipped.
    """
    messages = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return messages


def load_sessions_index(index_file: Path) -> Tuple[list, str]:
    """Load and normalize a sessions-index.json file.

    Handles both old format (list) and new format (dict with entries).

    Args:
        index_file: Path to the sessions-index.json file

    Returns:
        Tuple of (list of session entries, originalPath string)

    Raises:
        IOError: If file cannot be read
        json.JSONDecodeError: If file is not valid JSON
    """
    with open(index_file, "r") as f:
        data = json.load(f)

    if isinstance(data, dict):
        sessions = data.get("entries", [])
        original_path = data.get("originalPath", "")
    else:
        # Old format: just a list of sessions
        sessions = data
        original_path = ""

    return sessions, original_path


def find_session_file(session_id: str) -> Optional[Path]:
    """Find the JSONL file for a session ID.

    Searches all project directories for the session.
    Supports partial (prefix) matching.

    Args:
        session_id: Full or partial session ID

    Returns:
        Path to the JSONL file, or None if not found
    """
    projects_dir = get_claude_projects_dir()
    if not projects_dir.exists():
        return None

    # Try exact match first
    for jsonl_file in projects_dir.glob(f"*/{session_id}.jsonl"):
        return jsonl_file

    # Also try partial match
    for jsonl_file in projects_dir.glob(f"*/{session_id}*.jsonl"):
        return jsonl_file

    return None


def find_session(session_id: str) -> Optional[Tuple[Path, dict, Path]]:
    """Find a session by ID with its metadata.

    Args:
        session_id: Full or partial session ID

    Returns:
        Tuple of (project_dir, session_entry, jsonl_path) or None if not found
    """
    projects_dir = get_claude_projects_dir()
    if not projects_dir.exists():
        return None

    for index_file in projects_dir.glob("*/sessions-index.json"):
        project_dir = index_file.parent

        try:
            sessions, _ = load_sessions_index(index_file)
        except (json.JSONDecodeError, IOError):
            continue

        for session in sessions:
            sid = session.get("sessionId", "")
            if sid == session_id or sid.startswith(session_id):
                jsonl_path = project_dir / f"{sid}.jsonl"
                if jsonl_path.exists():
                    return (project_dir, session, jsonl_path)

    return None


def find_existing_project_dir(target_path: str) -> Optional[Path]:
    """Find an existing Claude project directory for the given path.

    Claude Code creates directories with path encoding, but the exact encoding
    can vary. This finds an existing directory that matches the target path
    by checking the originalPath in sessions-index.json.

    Args:
        target_path: The filesystem path to look for

    Returns:
        Path to the existing project directory, or None if not found
    """
    projects_dir = get_claude_projects_dir()
    if not projects_dir.exists():
        return None

    target_resolved = str(Path(target_path).resolve())

    for index_file in projects_dir.glob("*/sessions-index.json"):
        try:
            with open(index_file, "r") as f:
                data = json.load(f)

            original_path = data.get("originalPath", "")
            if original_path and str(Path(original_path).resolve()) == target_resolved:
                return index_file.parent
        except (json.JSONDecodeError, IOError):
            continue

    return None


def get_message_count(jsonl_path: Path) -> int:
    """Count the number of messages in a JSONL file.

    Args:
        jsonl_path: Path to the JSONL file

    Returns:
        Number of lines (messages) in the file
    """
    try:
        with open(jsonl_path, "r") as f:
            return sum(1 for _ in f)
    except IOError:
        return 0


def get_session_modified_time(
    session: dict,
    jsonl_path: Optional[Path] = None
) -> Optional[datetime]:
    """Get the modified time for a session.

    Tries to get the time from the session entry first,
    falls back to file modification time.

    Args:
        session: Session entry dict (may contain 'modified' field)
        jsonl_path: Optional path to JSONL file for fallback

    Returns:
        datetime object or None if not available
    """
    # Try session entry first
    if session.get("modified"):
        try:
            return datetime.fromisoformat(
                session["modified"].replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            pass

    # Fall back to file stats
    if jsonl_path and jsonl_path.exists():
        return datetime.fromtimestamp(jsonl_path.stat().st_mtime)

    return None


def get_session_summaries(session_ids: list[str]) -> dict[str, dict]:
    """Get summaries for multiple sessions efficiently.

    Scans all session indexes once and returns metadata for requested sessions.

    Args:
        session_ids: List of session IDs (can be partial prefixes)

    Returns:
        Dict mapping session_id to session metadata dict with keys:
        - summary: The session summary text
        - project_path: Decoded project path
        - lastModified: Timestamp in ms
    """
    projects_dir = get_claude_projects_dir()
    if not projects_dir.exists():
        return {}

    results = {}
    remaining = set(session_ids)

    for index_file in projects_dir.glob("*/sessions-index.json"):
        if not remaining:
            break

        project_dir = index_file.parent
        project_path = decode_project_path(project_dir.name)

        try:
            sessions, original_path = load_sessions_index(index_file)
        except (json.JSONDecodeError, IOError):
            continue

        for session in sessions:
            sid = session.get("sessionId", "")

            # Check if this session matches any we're looking for
            matched_id = None
            for wanted_id in list(remaining):
                if sid == wanted_id or sid.startswith(wanted_id):
                    matched_id = wanted_id
                    break

            if matched_id:
                results[sid] = {
                    "summary": session.get("summary", ""),
                    "project_path": original_path or project_path,
                    "lastModified": session.get("lastModified", 0),
                }
                remaining.discard(matched_id)

    return results


def extract_text_from_content(content: Union[str, list]) -> str:
    """Extract plain text from message content.

    Handles both string content and list-of-blocks format.

    Args:
        content: Message content (str or list of content blocks)

    Returns:
        Concatenated text content
    """
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))
        return " ".join(text_parts)

    return ""
