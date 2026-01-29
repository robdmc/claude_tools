#!/usr/bin/env python3
"""Export a Claude Code session to a portable format.

Exports session data to Markdown or JSON for sharing, archiving, or analysis.

Features:
- Export to Markdown (human-readable transcript)
- Export to JSON (machine-readable, preserves all data)
- Optional: include tool results, filter message types
- Works with session ID prefix matching
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from history_utils import (
    find_session,
    parse_jsonl,
    extract_text_from_content,
    decode_project_path,
)


def format_timestamp(ts: str) -> str:
    """Format an ISO timestamp to a readable string.

    Args:
        ts: ISO format timestamp string

    Returns:
        Human-readable timestamp (e.g., "2026-01-29 14:30")
    """
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return ts[:16] if len(ts) >= 16 else ts


def extract_user_content(msg: dict) -> str:
    """Extract text content from a user message.

    Args:
        msg: Message dict with 'message' containing 'content'

    Returns:
        Extracted text content
    """
    content = msg.get("message", {}).get("content", "")
    return extract_text_from_content(content)


def extract_assistant_content(msg: dict, include_tool_calls: bool = True) -> dict:
    """Extract content from an assistant message.

    Args:
        msg: Message dict with 'message' containing 'content'
        include_tool_calls: Whether to include tool call information

    Returns:
        Dict with 'text' and optionally 'tool_calls' keys
    """
    content = msg.get("message", {}).get("content", [])
    result = {"text": "", "tool_calls": []}

    if isinstance(content, str):
        result["text"] = content
        return result

    if not isinstance(content, list):
        return result

    text_parts = []
    tool_calls = []

    for item in content:
        if not isinstance(item, dict):
            continue

        item_type = item.get("type")

        if item_type == "text":
            text = item.get("text", "")
            # Skip thinking blocks (start with <)
            if text and not text.startswith("<"):
                text_parts.append(text)

        elif item_type == "tool_use" and include_tool_calls:
            tool_name = item.get("name", "unknown")
            tool_input = item.get("input", {})

            # Summarize tool call
            summary = summarize_tool_call(tool_name, tool_input)
            tool_calls.append({
                "name": tool_name,
                "summary": summary,
                "input": tool_input if tool_name in ("Write", "Edit") else None
            })

    result["text"] = "\n\n".join(text_parts)
    result["tool_calls"] = tool_calls

    return result


def summarize_tool_call(tool_name: str, tool_input: dict) -> str:
    """Create a human-readable summary of a tool call.

    Args:
        tool_name: Name of the tool
        tool_input: Tool input parameters

    Returns:
        Summary string
    """
    if tool_name == "Write":
        path = tool_input.get("file_path", "")
        filename = Path(path).name if path else "file"
        return f"Created {filename}"
    elif tool_name == "Edit":
        path = tool_input.get("file_path", "")
        filename = Path(path).name if path else "file"
        return f"Edited {filename}"
    elif tool_name == "Read":
        path = tool_input.get("file_path", "")
        filename = Path(path).name if path else "file"
        return f"Read {filename}"
    elif tool_name == "Bash":
        cmd = tool_input.get("command", "")
        if len(cmd) > 50:
            cmd = cmd[:50] + "..."
        return f"Ran: {cmd}"
    elif tool_name == "Grep":
        pattern = tool_input.get("pattern", "")
        return f"Searched for '{pattern}'"
    elif tool_name == "Glob":
        pattern = tool_input.get("pattern", "")
        return f"Found files matching {pattern}"
    elif tool_name == "Task":
        desc = tool_input.get("description", "")[:50]
        return f"Spawned task: {desc}"
    else:
        return tool_name


def is_system_message(content: str) -> bool:
    """Check if a user message is actually a system injection.

    Args:
        content: Message content string

    Returns:
        True if this appears to be a system message
    """
    system_patterns = [
        "<local-command",
        "<command-name>/",
        "Base directory for this skill",
        "<command-message>",
        "<tool_result>",
        "<system-reminder>",
        "You are in plan mode",
    ]
    for pattern in system_patterns:
        if pattern in content:
            return True
    return False


def export_to_markdown(
    messages: list,
    session_entry: dict,
    project_path: str,
    include_tools: bool = True,
    include_tool_results: bool = False,
) -> str:
    """Export session to Markdown format.

    Args:
        messages: List of parsed JSONL messages
        session_entry: Session metadata from index
        project_path: Original project path
        include_tools: Include tool call summaries
        include_tool_results: Include tool result content

    Returns:
        Markdown formatted string
    """
    lines = []

    # Header
    session_id = session_entry.get("sessionId", "unknown")
    summary = session_entry.get("summary", "Untitled Session")
    modified = session_entry.get("modified", "")

    lines.append(f"# {summary}")
    lines.append("")
    lines.append(f"**Session ID:** `{session_id}`")
    lines.append(f"**Project:** {project_path}")
    if modified:
        lines.append(f"**Date:** {format_timestamp(modified)}")
    lines.append(f"**Messages:** {len(messages)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Messages
    turn = 0
    for msg in messages:
        msg_type = msg.get("type")
        timestamp = msg.get("timestamp", "")

        if msg_type == "user":
            content = extract_user_content(msg)

            # Skip system messages
            if is_system_message(content):
                continue

            turn += 1
            time_str = f" ({format_timestamp(timestamp)})" if timestamp else ""
            lines.append(f"## Turn {turn}{time_str}")
            lines.append("")
            lines.append("### User")
            lines.append("")
            lines.append(content)
            lines.append("")

        elif msg_type == "assistant":
            extracted = extract_assistant_content(msg, include_tool_calls=include_tools)

            lines.append("### Claude")
            lines.append("")

            if extracted["text"]:
                lines.append(extracted["text"])
                lines.append("")

            if include_tools and extracted["tool_calls"]:
                lines.append("**Tools used:**")
                for tc in extracted["tool_calls"]:
                    lines.append(f"- {tc['summary']}")
                lines.append("")

        elif msg_type == "tool_result" and include_tool_results:
            tool_name = msg.get("tool_name", "unknown")
            result = msg.get("result", "")

            # Truncate very long results
            if isinstance(result, str) and len(result) > 500:
                result = result[:500] + "\n... (truncated)"

            lines.append(f"<details>")
            lines.append(f"<summary>Tool result: {tool_name}</summary>")
            lines.append("")
            lines.append("```")
            lines.append(str(result))
            lines.append("```")
            lines.append("")
            lines.append("</details>")
            lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append(f"*Exported from Claude Code session `{session_id[:8]}...`*")

    return "\n".join(lines)


def export_to_json(
    messages: list,
    session_entry: dict,
    project_path: str,
    include_tool_results: bool = True,
) -> dict:
    """Export session to JSON format.

    Args:
        messages: List of parsed JSONL messages
        session_entry: Session metadata from index
        project_path: Original project path
        include_tool_results: Include full tool results

    Returns:
        Dict suitable for JSON serialization
    """
    session_id = session_entry.get("sessionId", "unknown")

    # Extract conversation turns
    turns = []
    current_turn = None

    for msg in messages:
        msg_type = msg.get("type")
        timestamp = msg.get("timestamp", "")

        if msg_type == "user":
            content = extract_user_content(msg)

            # Skip system messages
            if is_system_message(content):
                continue

            # Start new turn
            if current_turn:
                turns.append(current_turn)

            current_turn = {
                "turn": len(turns) + 1,
                "timestamp": timestamp,
                "user": content,
                "assistant": None,
                "tool_calls": [],
                "tool_results": [] if include_tool_results else None,
            }

        elif msg_type == "assistant" and current_turn:
            extracted = extract_assistant_content(msg, include_tool_calls=True)
            current_turn["assistant"] = extracted["text"]
            current_turn["tool_calls"] = [
                {"name": tc["name"], "summary": tc["summary"]}
                for tc in extracted["tool_calls"]
            ]

        elif msg_type == "tool_result" and current_turn and include_tool_results:
            tool_name = msg.get("tool_name", "unknown")
            result = msg.get("result", "")

            # Truncate very long results
            if isinstance(result, str) and len(result) > 2000:
                result = result[:2000] + "... (truncated)"

            current_turn["tool_results"].append({
                "tool": tool_name,
                "result": result
            })

    # Add final turn
    if current_turn:
        turns.append(current_turn)

    return {
        "session_id": session_id,
        "summary": session_entry.get("summary", ""),
        "project_path": project_path,
        "modified": session_entry.get("modified", ""),
        "first_prompt": session_entry.get("firstPrompt", ""),
        "total_messages": len(messages),
        "turns": turns,
        "exported_at": datetime.now().isoformat(),
    }


def export_session(
    session_id: str,
    output_format: str = "markdown",
    output_path: Optional[str] = None,
    include_tools: bool = True,
    include_tool_results: bool = False,
) -> dict:
    """Export a session to the specified format.

    Args:
        session_id: Session ID to export (prefix match supported)
        output_format: "markdown" or "json"
        output_path: Optional output file path (prints to stdout if None)
        include_tools: Include tool call summaries (markdown only)
        include_tool_results: Include full tool results

    Returns:
        Dict with success status and output info
    """
    # Find the session
    result = find_session(session_id)
    if not result:
        return {
            "success": False,
            "error": f"Could not find session {session_id}"
        }

    project_dir, session_entry, jsonl_path = result
    full_session_id = session_entry.get("sessionId", "")
    project_path = session_entry.get("projectPath", decode_project_path(project_dir.name))

    # Parse messages
    messages = parse_jsonl(jsonl_path)
    if not messages:
        return {
            "success": False,
            "error": f"Session {session_id} has no messages"
        }

    # Generate export
    if output_format == "json":
        exported = export_to_json(
            messages,
            session_entry,
            project_path,
            include_tool_results=include_tool_results,
        )
        output_content = json.dumps(exported, indent=2)
    else:
        output_content = export_to_markdown(
            messages,
            session_entry,
            project_path,
            include_tools=include_tools,
            include_tool_results=include_tool_results,
        )
        exported = {"turns": len([m for m in messages if m.get("type") == "user"])}

    # Write to file or return content
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            f.write(output_content)

        return {
            "success": True,
            "session_id": full_session_id,
            "format": output_format,
            "output_path": str(output_file),
            "turns": exported.get("turns", 0) if isinstance(exported, dict) else 0,
            "message": f"Exported session {full_session_id[:8]}... to {output_file}"
        }
    else:
        return {
            "success": True,
            "session_id": full_session_id,
            "format": output_format,
            "content": output_content,
        }


def main():
    parser = argparse.ArgumentParser(
        description="Export a Claude Code session to Markdown or JSON"
    )
    parser.add_argument(
        "session_id",
        help="Session ID to export (prefix match supported)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (prints to stdout if not specified)"
    )
    parser.add_argument(
        "--no-tools",
        action="store_true",
        help="Exclude tool call summaries (markdown only)"
    )
    parser.add_argument(
        "--include-results",
        action="store_true",
        help="Include full tool results"
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output result metadata as JSON (for --output mode)"
    )

    args = parser.parse_args()

    result = export_session(
        args.session_id,
        output_format=args.format,
        output_path=args.output,
        include_tools=not args.no_tools,
        include_tool_results=args.include_results,
    )

    if args.output:
        # Writing to file - report status
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result["success"]:
                print(result["message"])
            else:
                print(f"Error: {result['error']}")
                return 1
    else:
        # Printing to stdout
        if result["success"]:
            print(result["content"])
        else:
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Error: {result['error']}")
            return 1

    return 0


if __name__ == "__main__":
    exit(main())
