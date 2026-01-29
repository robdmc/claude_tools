#!/usr/bin/env python3
"""Explore a specific Claude Code session.

Provides targeted queries within a single session's JSONL file:
- Summary of message flow
- Grep for patterns
- List files created/edited
- Show specific messages
"""

import argparse
import json
import re
from pathlib import Path
from typing import Optional


def get_claude_projects_dir() -> Path:
    """Get the Claude projects directory."""
    return Path.home() / ".claude" / "projects"


def find_session_file(session_id: str) -> Optional[Path]:
    """Find the JSONL file for a session ID.

    Searches all project directories for the session.
    """
    projects_dir = get_claude_projects_dir()
    if not projects_dir.exists():
        return None

    for jsonl_file in projects_dir.glob(f"*/{session_id}.jsonl"):
        return jsonl_file

    # Also try partial match
    for jsonl_file in projects_dir.glob(f"*/{session_id}*.jsonl"):
        return jsonl_file

    return None


def parse_jsonl(path: Path) -> list:
    """Parse a JSONL file into a list of messages."""
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


def extract_tool_summary(content: list) -> str:
    """Extract a summary of tool calls from assistant message content."""
    tools = []
    text_parts = []

    for item in content:
        if isinstance(item, dict):
            if item.get("type") == "tool_use":
                tool_name = item.get("name", "unknown")
                tool_input = item.get("input", {})

                # Summarize based on tool type
                if tool_name == "Write":
                    path = tool_input.get("file_path", "")
                    filename = Path(path).name if path else "file"
                    tools.append(f"Created {filename}")
                elif tool_name == "Edit":
                    path = tool_input.get("file_path", "")
                    filename = Path(path).name if path else "file"
                    tools.append(f"Edited {filename}")
                elif tool_name == "Read":
                    path = tool_input.get("file_path", "")
                    filename = Path(path).name if path else "file"
                    tools.append(f"Read {filename}")
                elif tool_name == "Bash":
                    cmd = tool_input.get("command", "")[:40]
                    tools.append(f"Ran: {cmd}...")
                elif tool_name == "Grep":
                    pattern = tool_input.get("pattern", "")
                    tools.append(f"Searched for '{pattern}'")
                elif tool_name == "Glob":
                    pattern = tool_input.get("pattern", "")
                    tools.append(f"Found files: {pattern}")
                elif tool_name == "Task":
                    desc = tool_input.get("description", "")
                    tools.append(f"Task: {desc}")
                else:
                    tools.append(tool_name)
            elif item.get("type") == "text":
                text = item.get("text", "")
                if text and not text.startswith("<"):  # Skip thinking blocks
                    text_parts.append(text[:100])

    if tools:
        return "[" + ", ".join(tools) + "]"
    elif text_parts:
        return text_parts[0][:100] + "..." if len(text_parts[0]) > 100 else text_parts[0]
    return ""


def get_summary(messages: list) -> list:
    """Generate a message flow summary."""
    summary = []
    turn = 0

    for msg in messages:
        msg_type = msg.get("type")

        if msg_type == "user":
            turn += 1
            content = msg.get("message", {}).get("content", "")
            if isinstance(content, list):
                # Extract text from content array
                text_parts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
                content = " ".join(text_parts)
            if isinstance(content, str):
                content = content[:150]
                if len(content) == 150:
                    content += "..."
            summary.append({
                "turn": turn,
                "role": "USER",
                "content": content
            })
        elif msg_type == "assistant":
            content = msg.get("message", {}).get("content", [])
            if isinstance(content, list):
                tool_summary = extract_tool_summary(content)
            else:
                tool_summary = str(content)[:100]

            if tool_summary:
                summary.append({
                    "turn": turn,
                    "role": "CLAUDE",
                    "content": tool_summary
                })

    return summary


def get_files(messages: list) -> list:
    """Extract all files created/edited from the session."""
    files = []

    for msg in messages:
        if msg.get("type") != "assistant":
            continue

        content = msg.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue

        for item in content:
            if not isinstance(item, dict) or item.get("type") != "tool_use":
                continue

            tool_name = item.get("name", "")
            tool_input = item.get("input", {})

            if tool_name == "Write":
                path = tool_input.get("file_path", "")
                if path:
                    files.append({"action": "created", "path": path})
            elif tool_name == "Edit":
                path = tool_input.get("file_path", "")
                if path:
                    files.append({"action": "edited", "path": path})

    # Deduplicate while preserving order
    seen = set()
    unique_files = []
    for f in files:
        key = (f["action"], f["path"])
        if key not in seen:
            seen.add(key)
            unique_files.append(f)

    return unique_files


def extract_message_text(msg: dict) -> str:
    """Extract searchable text content from a message."""
    msg_type = msg.get("type")
    text_parts = []

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
                        # Include tool inputs for searchability
                        tool_input = item.get("input", {})
                        if isinstance(tool_input, dict):
                            for v in tool_input.values():
                                if isinstance(v, str):
                                    text_parts.append(v)
    elif msg_type == "tool_result":
        result = msg.get("result", "")
        if isinstance(result, str):
            text_parts.append(result)

    return " ".join(text_parts)


def grep_session(messages: list, pattern: str, context: int = 2) -> list:
    """Search for a pattern within the session, returning match previews."""
    matches = []
    regex = re.compile(pattern, re.IGNORECASE)
    context_chars = 40  # Characters of context around each match

    for i, msg in enumerate(messages):
        text = extract_message_text(msg)
        found_matches = list(regex.finditer(text))

        if found_matches:
            # Extract previews with context
            previews = []
            for match in found_matches[:5]:  # Limit to 5 matches per message
                start = max(0, match.start() - context_chars)
                end = min(len(text), match.end() + context_chars)
                preview = text[start:end]
                # Highlight the match
                match_text = match.group()
                preview = preview.replace(match_text, f"**{match_text}**", 1)
                previews.append(preview)

            # Get context message indices
            context_start = max(0, i - context)
            context_end = min(len(messages), i + context + 1)

            matches.append({
                "message_index": i,
                "type": msg.get("type"),
                "context_start": context_start,
                "context_end": context_end,
                "match_previews": previews
            })

    return matches


def get_message(messages: list, index: int) -> Optional[dict]:
    """Get a specific message by index."""
    if 0 <= index < len(messages):
        return messages[index]
    return None


def is_system_injection(content: str) -> bool:
    """Check if a user message is a system injection rather than a real user prompt."""
    system_patterns = [
        "<local-command",
        "<command-name>/clear",
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


def get_user_prompts(messages: list, limit: Optional[int] = None) -> list:
    """Extract clean user prompts from messages, filtering out system injections."""
    prompts = []

    for i, msg in enumerate(messages):
        if msg.get("type") != "user":
            continue

        content = msg.get("message", {}).get("content", "")
        if isinstance(content, list):
            text_parts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
            content = " ".join(text_parts)

        if not isinstance(content, str) or not content.strip():
            continue

        # Filter out system injections
        if is_system_injection(content):
            continue

        timestamp = msg.get("timestamp", "")

        prompts.append({
            "index": i,
            "timestamp": timestamp,
            "content": content.strip()
        })

        if limit and len(prompts) >= limit:
            break

    return prompts


def format_user_prompts_human(prompts: list) -> str:
    """Format user prompts for human reading."""
    if not prompts:
        return "No user prompts found in session."

    lines = [f"Found {len(prompts)} user prompt(s):"]
    lines.append("")

    for prompt in prompts:
        timestamp = prompt["timestamp"]
        if timestamp:
            # Format timestamp more readably
            time_str = timestamp[:19] if len(timestamp) >= 19 else timestamp
            lines.append(f"[{prompt['index']}] ({time_str})")
        else:
            lines.append(f"[{prompt['index']}]")

        # Indent the content
        content = prompt["content"]
        # Truncate very long prompts
        if len(content) > 500:
            content = content[:500] + "..."
        lines.append(f"    {content}")
        lines.append("")

    return "\n".join(lines)


def format_summary_human(summary: list) -> str:
    """Format summary for human reading."""
    if not summary:
        return "No messages in session."

    lines = []
    current_turn = None

    for item in summary:
        if item["turn"] != current_turn:
            if current_turn is not None:
                lines.append("")
            current_turn = item["turn"]

        lines.append(f"[{item['turn']}] {item['role']}: {item['content']}")

    return "\n".join(lines)


def format_files_human(files: list) -> str:
    """Format files list for human reading."""
    if not files:
        return "No files created or edited in this session."

    lines = ["Files created/edited:"]
    for f in files:
        lines.append(f"  {f['action']}: {f['path']}")

    return "\n".join(lines)


def format_grep_human(matches: list, messages: list) -> str:
    """Format grep results for human reading."""
    if not matches:
        return "No matches found."

    lines = [f"Found {len(matches)} matching message(s):"]

    for match in matches:
        idx = match["message_index"]
        msg = messages[idx]
        msg_type = msg.get("type", "unknown")

        lines.append(f"\n[Message {idx}] Type: {msg_type}")

        # Show relevant content based on type
        if msg_type == "user":
            content = msg.get("message", {}).get("content", "")
            if isinstance(content, list):
                text_parts = [c.get("text", "") for c in content if isinstance(c, dict)]
                content = " ".join(text_parts)
            lines.append(f"  Content: {str(content)[:200]}")
        elif msg_type == "assistant":
            content = msg.get("message", {}).get("content", [])
            if isinstance(content, list):
                lines.append(f"  Summary: {extract_tool_summary(content)}")

        # Show match previews if available
        if match.get("match_previews"):
            lines.append("  Matches:")
            for preview in match["match_previews"][:3]:  # Limit to 3 previews per message
                lines.append(f"    ...{preview}...")

    return "\n".join(lines)


def format_message_human(msg: dict, index: int) -> str:
    """Format a single message for human reading."""
    msg_type = msg.get("type", "unknown")
    timestamp = msg.get("timestamp", "")

    # Skip file-history-snapshot types
    if msg_type == "file-history-snapshot":
        return f"[Message {index}] file-history-snapshot (skipped)"

    lines = [f"[Message {index}] {msg_type}"]
    if timestamp:
        lines[0] += f" at {timestamp}"

    if msg_type == "user":
        content = msg.get("message", {}).get("content", "")
        if isinstance(content, list):
            text_parts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
            content = " ".join(text_parts)
        if content:
            lines.append("")
            lines.append(content)

    elif msg_type == "assistant":
        content = msg.get("message", {}).get("content", [])
        if isinstance(content, list):
            # Extract text parts
            text_parts = []
            tool_calls = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        text = item.get("text", "")
                        if text and not text.startswith("<"):
                            text_parts.append(text)
                    elif item.get("type") == "tool_use":
                        tool_name = item.get("name", "unknown")
                        tool_input = item.get("input", {})
                        if tool_name in ("Write", "Edit", "Read"):
                            path = tool_input.get("file_path", "")
                            filename = Path(path).name if path else "file"
                            tool_calls.append(f"{tool_name}({filename})")
                        elif tool_name == "Bash":
                            cmd = tool_input.get("command", "")[:50]
                            tool_calls.append(f"Bash({cmd}...)")
                        else:
                            tool_calls.append(tool_name)

            if text_parts:
                lines.append("")
                lines.append("\n".join(text_parts))

            if tool_calls:
                lines.append("")
                lines.append("Tool calls: " + ", ".join(tool_calls))

    elif msg_type == "tool_result":
        tool_name = msg.get("tool_name", "unknown")
        lines.append(f"  Tool: {tool_name}")
        result = msg.get("result", "")
        if isinstance(result, str) and len(result) > 200:
            result = result[:200] + "..."
        lines.append(f"  Result: {result}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Explore a Claude Code session")
    parser.add_argument("session_id", help="Session ID to explore (prefix match supported)")
    parser.add_argument("--summary", "-s", action="store_true", help="Show message flow summary")
    parser.add_argument("--files", "-f", action="store_true", help="List files created/edited")
    parser.add_argument("--grep", "-g", help="Search for pattern in session")
    parser.add_argument("--context", "-c", type=int, default=2, help="Context lines for grep (default: 2)")
    parser.add_argument("--message", "-m", type=int, help="Show specific message by index")
    parser.add_argument("--user-prompts", "-u", action="store_true", help="Show user prompts only")
    parser.add_argument("--limit", type=int, help="Limit number of results (for --user-prompts)")
    parser.add_argument("--raw", action="store_true", help="Output raw JSON for --message")
    parser.add_argument("--json", "-j", action="store_true", help="Output JSON")

    args = parser.parse_args()

    # Find the session file
    session_file = find_session_file(args.session_id)
    if not session_file:
        # Try to suggest similar sessions
        projects_dir = get_claude_projects_dir()
        suggestions = []
        if projects_dir.exists():
            for jsonl_file in projects_dir.glob(f"*/{args.session_id}*.jsonl"):
                suggestions.append(jsonl_file.stem)
        if suggestions:
            print(f"Error: Could not find session {args.session_id}")
            print(f"Did you mean: {suggestions[0]}?")
        else:
            print(f"Error: Could not find session {args.session_id}")
        return 1

    # Parse messages
    messages = parse_jsonl(session_file)

    if args.summary:
        summary = get_summary(messages)
        if args.json:
            print(json.dumps({"summary": summary}, indent=2))
        else:
            print(format_summary_human(summary))

    elif args.files:
        files = get_files(messages)
        if args.json:
            print(json.dumps({"files": files}, indent=2))
        else:
            print(format_files_human(files))

    elif args.grep:
        matches = grep_session(messages, args.grep, args.context)
        if args.json:
            print(json.dumps({"matches": matches}, indent=2))
        else:
            print(format_grep_human(matches, messages))

    elif args.user_prompts:
        prompts = get_user_prompts(messages, args.limit)
        if args.json:
            print(json.dumps({"user_prompts": prompts}, indent=2))
        else:
            print(format_user_prompts_human(prompts))

    elif args.message is not None:
        msg = get_message(messages, args.message)
        if msg:
            if args.json or args.raw:
                print(json.dumps(msg, indent=2))
            else:
                print(format_message_human(msg, args.message))
        else:
            print(f"Error: Message index {args.message} out of range (0-{len(messages)-1})")
            return 1

    else:
        # Default: show summary
        summary = get_summary(messages)
        if args.json:
            print(json.dumps({"summary": summary}, indent=2))
        else:
            print(format_summary_human(summary))

    return 0


if __name__ == "__main__":
    exit(main())
