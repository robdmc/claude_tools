#!/usr/bin/env python3
"""Search all Claude Code sessions for a term.

Searches across all sessions-index.json files in ~/.claude/projects/,
looking in summary and firstPrompt fields. With --deep, also searches
inside JSONL message content.
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


def extract_jsonl_text(jsonl_path: Path) -> str:
    """Extract searchable text from a JSONL session file."""
    text_parts = []
    try:
        with open(jsonl_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg_type = msg.get("type")

                if msg_type == "user":
                    content = msg.get("message", {}).get("content", "")
                    if isinstance(content, str):
                        text_parts.append(content)
                    elif isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                text_parts.append(item.get("text", ""))

                elif msg_type == "assistant":
                    content = msg.get("message", {}).get("content", [])
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict):
                                if item.get("type") == "text":
                                    text_parts.append(item.get("text", ""))
                                elif item.get("type") == "tool_use":
                                    tool_input = item.get("input", {})
                                    if isinstance(tool_input, dict):
                                        for v in tool_input.values():
                                            if isinstance(v, str):
                                                text_parts.append(v)

    except IOError:
        pass

    return " ".join(text_parts)


def search_session_content(jsonl_path: Path, pattern: re.Pattern, context_chars: int = 60) -> list:
    """Search JSONL content and return match previews."""
    text = extract_jsonl_text(jsonl_path)
    matches = list(pattern.finditer(text))

    if not matches:
        return []

    previews = []
    for match in matches[:3]:  # Limit to 3 previews per session
        start = max(0, match.start() - context_chars)
        end = min(len(text), match.end() + context_chars)
        preview = text[start:end]
        # Clean up whitespace
        preview = " ".join(preview.split())
        # Highlight match
        match_text = match.group()
        preview = preview.replace(match_text, f"**{match_text}**", 1)
        previews.append(preview)

    return previews


def search_sessions(query: str, limit: int = 5, deep: bool = False) -> dict:
    """Search all sessions for a term.

    Args:
        query: Search term (case-insensitive)
        limit: Maximum number of results to return
        deep: If True, search inside JSONL message content

    Returns:
        Dict with total count and list of matching sessions
    """
    projects_dir = get_claude_projects_dir()
    if not projects_dir.exists():
        return {"total": 0, "results": [], "deep": deep}

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

            # Search in summary and firstPrompt first
            metadata_match = pattern.search(summary) or pattern.search(first_prompt)
            content_previews = []

            # If deep search, also check JSONL content
            jsonl_path = project_dir / f"{session_id}.jsonl"
            if deep and jsonl_path.exists() and not metadata_match:
                content_previews = search_session_content(jsonl_path, pattern)

            if metadata_match or content_previews:
                # Get message count from JSONL file
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

                result = {
                    "session_id": session_id,
                    "project": session_project_path,
                    "project_encoded": encoded_path,
                    "summary": summary[:200] if summary else "",
                    "first_prompt": first_prompt[:200] if first_prompt else "",
                    "modified": modified.isoformat() if modified else None,
                    "message_count": message_count,
                    "match_source": "metadata" if metadata_match else "content"
                }
                if content_previews:
                    result["match_previews"] = content_previews

                all_matches.append(result)

    # Sort by modified date (most recent first)
    all_matches.sort(key=lambda x: x["modified"] or "", reverse=True)

    return {
        "total": len(all_matches),
        "results": all_matches[:limit],
        "deep": deep
    }


def format_human_readable(results: dict) -> str:
    """Format results for human reading."""
    total = results["total"]
    matches = results["results"]
    deep = results.get("deep", False)

    if total == 0:
        msg = "No sessions found matching that query."
        if not deep:
            msg += "\nTry --deep to search inside message content."
        return msg

    header = f"Found {total} session(s) matching query"
    if deep:
        header += " (deep search)"
    header += ":"
    if total > len(matches):
        header += f" (showing top {len(matches)})"
    lines = [header]
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

        # Show match previews for deep search results
        if match.get("match_previews"):
            lines.append(f"   Match source: content")
            for preview in match["match_previews"]:
                lines.append(f"     ...{preview}...")

        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Search Claude Code sessions")
    parser.add_argument("--query", "-q", required=True, help="Search term")
    parser.add_argument("--limit", "-l", type=int, default=5, help="Max results (default: 5)")
    parser.add_argument("--deep", "-d", action="store_true", help="Search inside JSONL message content")
    parser.add_argument("--json", "-j", action="store_true", help="Output JSON")

    args = parser.parse_args()

    results = search_sessions(args.query, args.limit, args.deep)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(format_human_readable(results))


if __name__ == "__main__":
    main()
