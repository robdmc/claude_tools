#!/usr/bin/env python3
"""Search all Claude Code sessions for a term.

Searches across all sessions-index.json files in ~/.claude/projects/,
looking in summary and firstPrompt fields.
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path


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


def search_sessions(query: str, limit: int = 5) -> dict:
    """Search all sessions for a term.

    Args:
        query: Search term (case-insensitive)
        limit: Maximum number of results to return

    Returns:
        Dict with total count and list of matching sessions
    """
    projects_dir = get_claude_projects_dir()
    if not projects_dir.exists():
        return {"total": 0, "results": []}

    pattern = re.compile(re.escape(query), re.IGNORECASE)
    all_matches = []

    # Find all sessions-index.json files
    for index_file in projects_dir.glob("*/sessions-index.json"):
        project_dir = index_file.parent
        encoded_path = project_dir.name
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

            # Search in summary and firstPrompt
            if pattern.search(summary) or pattern.search(first_prompt):
                # Get message count from JSONL file
                jsonl_path = project_dir / f"{session_id}.jsonl"
                message_count = session.get("messageCount", 0)
                if message_count == 0 and jsonl_path.exists():
                    try:
                        with open(jsonl_path, "r") as f:
                            message_count = sum(1 for _ in f)
                    except IOError:
                        pass

                # Get modified time from session entry or file
                modified = None
                if session.get("modified"):
                    try:
                        modified = datetime.fromisoformat(session["modified"].replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pass
                if modified is None and jsonl_path.exists():
                    modified = datetime.fromtimestamp(jsonl_path.stat().st_mtime)

                all_matches.append({
                    "session_id": session_id,
                    "project": session_project_path,
                    "project_encoded": encoded_path,
                    "summary": summary[:200] if summary else "",
                    "first_prompt": first_prompt[:200] if first_prompt else "",
                    "modified": modified.isoformat() if modified else None,
                    "message_count": message_count
                })

    # Sort by modified date (most recent first)
    all_matches.sort(key=lambda x: x["modified"] or "", reverse=True)

    return {
        "total": len(all_matches),
        "results": all_matches[:limit]
    }


def format_human_readable(results: dict) -> str:
    """Format results for human reading."""
    total = results["total"]
    matches = results["results"]

    if total == 0:
        return "No sessions found matching that query."

    lines = [f"Found {total} session(s) matching query:"]
    if total > len(matches):
        lines[0] += f" (showing top {len(matches)})"
    lines.append("")

    for i, match in enumerate(matches, 1):
        date_str = match["modified"][:10] if match["modified"] else "unknown"
        project_name = Path(match["project"]).name if match["project"] else "unknown"
        summary = match["summary"] or match["first_prompt"] or "(no summary)"
        if len(summary) > 80:
            summary = summary[:77] + "..."

        lines.append(f"{i}. [{date_str}] {match['session_id'][:8]}...")
        lines.append(f"   Project: {project_name}")
        lines.append(f"   Summary: {summary}")
        lines.append(f"   Messages: {match['message_count']}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Search Claude Code sessions")
    parser.add_argument("--query", "-q", required=True, help="Search term")
    parser.add_argument("--limit", "-l", type=int, default=5, help="Max results (default: 5)")
    parser.add_argument("--json", "-j", action="store_true", help="Output JSON")

    args = parser.parse_args()

    results = search_sessions(args.query, args.limit)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(format_human_readable(results))


if __name__ == "__main__":
    main()
