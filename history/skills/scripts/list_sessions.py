#!/usr/bin/env python3
"""List recent Claude Code sessions across all projects.

Lists sessions from all sessions-index.json files, sorted by most recent.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional


def get_claude_projects_dir() -> Path:
    """Get the Claude projects directory."""
    return Path.home() / ".claude" / "projects"


def decode_project_path(encoded: str) -> str:
    """Decode project path from directory name.

    -Users-rob-project -> /Users/rob/project
    """
    if encoded.startswith("-"):
        return encoded.replace("-", "/", 1).replace("-", "/")
    return encoded


def encode_project_path(path: str) -> str:
    """Encode project path to directory name.

    /Users/rob/project -> -Users-rob-project
    """
    return path.replace("/", "-")


def list_sessions(limit: int = 5, project_filter: Optional[str] = None) -> dict:
    """List recent sessions across all projects.

    Args:
        limit: Maximum number of results to return
        project_filter: Optional project path to filter by

    Returns:
        Dict with total count and list of sessions
    """
    projects_dir = get_claude_projects_dir()
    if not projects_dir.exists():
        return {"total": 0, "results": []}

    # If project filter specified, encode it
    encoded_filter = None
    if project_filter:
        encoded_filter = encode_project_path(project_filter)

    all_sessions = []

    # Find all sessions-index.json files
    for index_file in projects_dir.glob("*/sessions-index.json"):
        project_dir = index_file.parent
        encoded_path = project_dir.name

        # Apply project filter if specified
        if encoded_filter and encoded_path != encoded_filter:
            continue

        project_path = decode_project_path(encoded_path)

        try:
            with open(index_file, "r") as f:
                data = json.load(f)
                # Handle both old format (list) and new format (dict with entries)
                if isinstance(data, dict):
                    sessions = data.get("entries", [])
                    # Get originalPath from index file for accurate project path
                    index_project_path = data.get("originalPath", project_path)
                else:
                    sessions = data
                    index_project_path = project_path
        except (json.JSONDecodeError, IOError):
            continue

        for session in sessions:
            session_id = session.get("sessionId", "")
            summary = session.get("summary", "")
            first_prompt = session.get("firstPrompt", "")
            # Prefer projectPath from session entry, fall back to index originalPath
            session_project_path = session.get("projectPath", index_project_path)

            # Get message count and modified time from session entry or JSONL file
            jsonl_path = project_dir / f"{session_id}.jsonl"
            message_count = session.get("messageCount", 0)
            modified = None

            # Try to get modified from session entry first
            if session.get("modified"):
                try:
                    modified = datetime.fromisoformat(session["modified"].replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass

            # Fall back to file stats if needed
            if jsonl_path.exists():
                if message_count == 0:
                    try:
                        with open(jsonl_path, "r") as f:
                            message_count = sum(1 for _ in f)
                    except IOError:
                        pass
                if modified is None:
                    modified = datetime.fromtimestamp(jsonl_path.stat().st_mtime)

            all_sessions.append({
                "session_id": session_id,
                "project": session_project_path,
                "project_encoded": encoded_path,
                "summary": summary[:200] if summary else "",
                "first_prompt": first_prompt[:200] if first_prompt else "",
                "modified": modified.isoformat() if modified else None,
                "message_count": message_count
            })

    # Sort by modified date (most recent first)
    all_sessions.sort(key=lambda x: x["modified"] or "", reverse=True)

    return {
        "total": len(all_sessions),
        "results": all_sessions[:limit]
    }


def format_human_readable(results: dict) -> str:
    """Format results for human reading."""
    total = results["total"]
    sessions = results["results"]

    if total == 0:
        return "No sessions found."

    lines = [f"Found {total} session(s):"]
    if total > len(sessions):
        lines[0] += f" (showing {len(sessions)} most recent)"
    lines.append("")

    for i, session in enumerate(sessions, 1):
        date_str = session["modified"][:10] if session["modified"] else "unknown"
        project_name = Path(session["project"]).name if session["project"] else "unknown"
        summary = session["summary"] or session["first_prompt"] or "(no summary)"
        if len(summary) > 80:
            summary = summary[:77] + "..."

        lines.append(f"{i}. [{date_str}] {session['session_id'][:8]}...")
        lines.append(f"   Project: {project_name}")
        lines.append(f"   Summary: {summary}")
        lines.append(f"   Messages: {session['message_count']}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="List recent Claude Code sessions")
    parser.add_argument("--limit", "-l", type=int, default=5, help="Max results (default: 5)")
    parser.add_argument("--project", "-p", help="Filter to specific project path")
    parser.add_argument("--json", "-j", action="store_true", help="Output JSON")

    args = parser.parse_args()

    results = list_sessions(args.limit, args.project)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(format_human_readable(results))


if __name__ == "__main__":
    main()
