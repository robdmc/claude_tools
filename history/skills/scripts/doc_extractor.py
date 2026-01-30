#!/usr/bin/env python3
"""Document extractor for Claude Code sessions.

Extracts documents from Claude Code session JSONL files for indexing
with LanceDB. Documents are chunks of conversation content with metadata.

Each document contains:
- session_id: The session it came from
- project_path: The project associated with the session
- doc_type: Type of content (user_prompt, assistant_text, tool_use, tool_result)
- content: The text content
- timestamp: When the message occurred
- message_index: Position in the conversation
- metadata: Additional context (tool names, file paths, etc.)
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from history_utils import (
    decode_project_path,
    extract_text_from_content,
    get_claude_projects_dir,
    load_sessions_index,
    parse_jsonl,
)


@dataclass
class Document:
    """A document extracted from a Claude Code session."""

    session_id: str
    project_path: str
    doc_type: str  # user_prompt, assistant_text, tool_use, tool_result
    content: str
    timestamp: Optional[str] = None
    message_index: int = 0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "project_path": self.project_path,
            "doc_type": self.doc_type,
            "content": self.content,
            "timestamp": self.timestamp,
            "message_index": self.message_index,
            "metadata": self.metadata,
        }


def is_system_injection(content: str) -> bool:
    """Check if content is a system injection rather than a real user prompt.

    Args:
        content: The text content to check

    Returns:
        True if the content appears to be a system injection
    """
    system_patterns = [
        "<local-command",
        "<command-name>/clear",
        "<command-name>/",
        "Base directory for this skill",
        "<command-message>",
        "<tool_result>",
        "<system-reminder>",
        "You are in plan mode",
        "<context-loaded>",
        "# Task Worker Agent Protocol",
    ]
    for pattern in system_patterns:
        if pattern in content:
            return True
    return False


def extract_documents_from_message(
    msg: dict,
    session_id: str,
    project_path: str,
    message_index: int,
    min_content_length: int = 20,
) -> list[Document]:
    """Extract documents from a single message.

    Args:
        msg: The parsed message dictionary
        session_id: The session ID
        project_path: The project path
        message_index: Position in conversation
        min_content_length: Minimum content length to include

    Returns:
        List of Document objects extracted from the message
    """
    docs = []
    msg_type = msg.get("type")
    timestamp = msg.get("timestamp")

    if msg_type == "user":
        content = msg.get("message", {}).get("content", "")
        text = extract_text_from_content(content)

        # Filter out system injections and short content
        if text and len(text) >= min_content_length and not is_system_injection(text):
            docs.append(
                Document(
                    session_id=session_id,
                    project_path=project_path,
                    doc_type="user_prompt",
                    content=text,
                    timestamp=timestamp,
                    message_index=message_index,
                )
            )

    elif msg_type == "assistant":
        content = msg.get("message", {}).get("content", [])

        if isinstance(content, list):
            for item in content:
                if not isinstance(item, dict):
                    continue

                item_type = item.get("type")

                if item_type == "text":
                    text = item.get("text", "")
                    # Skip thinking blocks and short content
                    if (
                        text
                        and len(text) >= min_content_length
                        and not text.startswith("<")
                    ):
                        docs.append(
                            Document(
                                session_id=session_id,
                                project_path=project_path,
                                doc_type="assistant_text",
                                content=text,
                                timestamp=timestamp,
                                message_index=message_index,
                            )
                        )

                elif item_type == "tool_use":
                    tool_name = item.get("name", "")
                    tool_input = item.get("input", {})

                    # Extract meaningful content from tool calls
                    tool_content = _extract_tool_content(tool_name, tool_input)
                    if tool_content and len(tool_content) >= min_content_length:
                        docs.append(
                            Document(
                                session_id=session_id,
                                project_path=project_path,
                                doc_type="tool_use",
                                content=tool_content,
                                timestamp=timestamp,
                                message_index=message_index,
                                metadata={
                                    "tool_name": tool_name,
                                    "tool_id": item.get("id", ""),
                                },
                            )
                        )

    elif msg_type == "tool_result":
        tool_name = msg.get("tool_name", "")
        result = msg.get("result", "")

        # Only include text results that are meaningful
        if isinstance(result, str) and len(result) >= min_content_length:
            # Truncate very long tool results
            if len(result) > 5000:
                result = result[:5000] + "... [truncated]"

            docs.append(
                Document(
                    session_id=session_id,
                    project_path=project_path,
                    doc_type="tool_result",
                    content=result,
                    timestamp=timestamp,
                    message_index=message_index,
                    metadata={
                        "tool_name": tool_name,
                        "tool_use_id": msg.get("tool_use_id", ""),
                    },
                )
            )

    return docs


def _extract_tool_content(tool_name: str, tool_input: dict) -> str:
    """Extract meaningful content from tool inputs.

    Args:
        tool_name: Name of the tool
        tool_input: The tool's input dictionary

    Returns:
        Extracted content string
    """
    if not isinstance(tool_input, dict):
        return ""

    # For file operations, include the file path context
    if tool_name in ("Write", "Edit", "Read"):
        file_path = tool_input.get("file_path", "")
        if tool_name == "Write":
            content = tool_input.get("content", "")
            return f"Write to {file_path}:\n{content}"
        elif tool_name == "Edit":
            old_string = tool_input.get("old_string", "")
            new_string = tool_input.get("new_string", "")
            return f"Edit {file_path}:\nOld: {old_string}\nNew: {new_string}"
        elif tool_name == "Read":
            return f"Read file: {file_path}"

    # For bash commands, include the command
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        description = tool_input.get("description", "")
        if description:
            return f"Bash ({description}): {command}"
        return f"Bash: {command}"

    # For search tools
    if tool_name == "Grep":
        pattern = tool_input.get("pattern", "")
        path = tool_input.get("path", "")
        return f"Grep for '{pattern}' in {path or 'cwd'}"

    if tool_name == "Glob":
        pattern = tool_input.get("pattern", "")
        path = tool_input.get("path", "")
        return f"Find files matching '{pattern}' in {path or 'cwd'}"

    # For WebSearch/WebFetch
    if tool_name == "WebSearch":
        query = tool_input.get("query", "")
        return f"Web search: {query}"

    if tool_name == "WebFetch":
        url = tool_input.get("url", "")
        prompt = tool_input.get("prompt", "")
        return f"Fetch {url}: {prompt}"

    # For Task tool
    if tool_name == "Task":
        description = tool_input.get("description", "")
        prompt = tool_input.get("prompt", "")
        return f"Task: {description}\n{prompt}"

    # Generic fallback: concatenate string values
    parts = []
    for key, value in tool_input.items():
        if isinstance(value, str) and value:
            parts.append(f"{key}: {value}")
    return "\n".join(parts)


def extract_documents_from_session(
    jsonl_path: Path,
    session_id: str,
    project_path: str,
    min_content_length: int = 20,
) -> list[Document]:
    """Extract all documents from a session JSONL file.

    Args:
        jsonl_path: Path to the JSONL file
        session_id: The session ID
        project_path: The project path
        min_content_length: Minimum content length to include

    Returns:
        List of Document objects
    """
    messages = parse_jsonl(jsonl_path)
    docs = []

    for i, msg in enumerate(messages):
        docs.extend(
            extract_documents_from_message(
                msg, session_id, project_path, i, min_content_length
            )
        )

    return docs


def iter_all_sessions() -> Iterator[tuple[str, str, Path]]:
    """Iterate over all sessions in the Claude projects directory.

    Yields:
        Tuples of (session_id, project_path, jsonl_path)
    """
    projects_dir = get_claude_projects_dir()
    if not projects_dir.exists():
        return

    for index_file in projects_dir.glob("*/sessions-index.json"):
        project_dir = index_file.parent
        encoded_path = project_dir.name
        project_path = decode_project_path(encoded_path)

        try:
            sessions, original_path = load_sessions_index(index_file)
            if original_path:
                project_path = original_path
        except (json.JSONDecodeError, IOError):
            continue

        for session in sessions:
            session_id = session.get("sessionId", "")
            if not session_id:
                continue

            # Prefer projectPath from session entry
            session_project_path = session.get("projectPath", project_path)
            jsonl_path = project_dir / f"{session_id}.jsonl"

            if jsonl_path.exists():
                yield session_id, session_project_path, jsonl_path


def extract_all_documents(
    min_content_length: int = 20,
    project_filter: Optional[str] = None,
) -> Iterator[Document]:
    """Extract documents from all sessions.

    Args:
        min_content_length: Minimum content length to include
        project_filter: Optional substring to filter projects

    Yields:
        Document objects from all sessions
    """
    for session_id, project_path, jsonl_path in iter_all_sessions():
        # Apply project filter if specified
        if project_filter and project_filter not in project_path:
            continue

        docs = extract_documents_from_session(
            jsonl_path, session_id, project_path, min_content_length
        )
        for doc in docs:
            yield doc


def get_session_stats() -> dict:
    """Get statistics about all sessions.

    Returns:
        Dictionary with session counts and totals
    """
    total_sessions = 0
    total_messages = 0
    projects = set()

    for session_id, project_path, jsonl_path in iter_all_sessions():
        total_sessions += 1
        projects.add(project_path)

        # Count messages
        try:
            with open(jsonl_path, "r") as f:
                total_messages += sum(1 for _ in f)
        except IOError:
            pass

    return {
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "total_projects": len(projects),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract documents from Claude Code sessions"
    )
    parser.add_argument(
        "--stats", "-s", action="store_true", help="Show session statistics"
    )
    parser.add_argument(
        "--project",
        "-p",
        type=str,
        help="Filter to specific project (substring match)",
    )
    parser.add_argument(
        "--session", type=str, help="Extract from specific session ID"
    )
    parser.add_argument(
        "--limit", "-l", type=int, default=10, help="Limit output documents"
    )
    parser.add_argument(
        "--min-length", type=int, default=20, help="Minimum content length"
    )
    parser.add_argument(
        "--json", "-j", action="store_true", help="Output JSON"
    )

    args = parser.parse_args()

    if args.stats:
        stats = get_session_stats()
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"Total sessions: {stats['total_sessions']}")
            print(f"Total messages: {stats['total_messages']}")
            print(f"Total projects: {stats['total_projects']}")

    elif args.session:
        # Find and extract from specific session
        from history_utils import find_session_file

        jsonl_path = find_session_file(args.session)
        if not jsonl_path:
            print(f"Error: Session {args.session} not found")
            exit(1)

        # Get project path from parent directory
        project_path = decode_project_path(jsonl_path.parent.name)

        docs = extract_documents_from_session(
            jsonl_path,
            args.session,
            project_path,
            args.min_length,
        )

        if args.limit:
            docs = docs[: args.limit]

        if args.json:
            print(json.dumps([d.to_dict() for d in docs], indent=2))
        else:
            for doc in docs:
                print(f"[{doc.message_index}] {doc.doc_type}")
                print(f"  Content: {doc.content[:100]}...")
                if doc.metadata:
                    print(f"  Metadata: {doc.metadata}")
                print()

    else:
        # Extract from all sessions
        docs = list(
            extract_all_documents(
                min_content_length=args.min_length, project_filter=args.project
            )
        )

        if args.limit:
            docs = docs[: args.limit]

        if args.json:
            print(json.dumps([d.to_dict() for d in docs], indent=2))
        else:
            print(f"Extracted {len(docs)} documents")
            print()
            for doc in docs[:5]:  # Show first 5
                print(f"[{doc.session_id[:8]}] {doc.doc_type}")
                print(f"  Project: {doc.project_path}")
                print(f"  Content: {doc.content[:80]}...")
                print()
