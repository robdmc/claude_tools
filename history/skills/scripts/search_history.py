#!/usr/bin/env python3
"""Semantic search for Claude Code sessions using LanceDB.

Performs vector similarity search against indexed session documents,
finding conversations semantically similar to the query even when they
don't contain exact keyword matches.

Requires: An indexed database (run index_history.py first)
"""

import argparse
import json
from pathlib import Path
from typing import Optional

from embedder import embed_text
from history_utils import get_session_summaries
from lance_db import HistoryDB, SearchResult


def format_result_text(result: SearchResult, show_full: bool = False) -> str:
    """Format a search result for human-readable output.

    Args:
        result: The search result to format
        show_full: If True, show full text content

    Returns:
        Formatted string representation
    """
    project_name = Path(result.project_path).name if result.project_path else "unknown"
    session_short = result.session_id[:8] if result.session_id else "unknown"

    # Truncate text unless showing full
    text = result.text
    if not show_full and len(text) > 150:
        text = text[:147] + "..."

    # Clean up whitespace
    text = " ".join(text.split())

    # Extract timestamp if available
    timestamp = ""
    if result.metadata and result.metadata.get("timestamp"):
        ts = result.metadata["timestamp"]
        # Format: 2026-01-17T18:06:35.005Z -> 2026-01-17
        timestamp = ts[:10] if len(ts) >= 10 else ts

    lines = [
        f"Session: {session_short}... | Project: {project_name} | Date: {timestamp or 'unknown'}",
        f"Type: {result.chunk_type} | Score: {result.score:.4f}",
        f"Content: {text}",
    ]

    # Add metadata if present
    if result.metadata:
        if result.metadata.get("tool_name"):
            lines.append(f"Tool: {result.metadata['tool_name']}")

    return "\n".join(lines)


def search_history(
    query: str,
    limit: int = 10,
    project_filter: Optional[str] = None,
    session_filter: Optional[str] = None,
    chunk_type_filter: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> dict:
    """Search indexed history using semantic similarity.

    Args:
        query: The search query string
        limit: Maximum number of results to return
        project_filter: Optional project path to filter by
        session_filter: Optional session ID to filter by
        chunk_type_filter: Optional chunk type (user_prompt, assistant_text, etc.)
        db_path: Optional custom database path

    Returns:
        Dict with query info and list of results
    """
    # Initialize database
    db = HistoryDB(db_path) if db_path else HistoryDB()

    # Check if database has any data
    stats = db.get_stats()
    if not stats.get("exists") or stats.get("total_documents", 0) == 0:
        return {
            "query": query,
            "total": 0,
            "results": [],
            "error": "No indexed data found. Run index_history.py first.",
        }

    # Generate embedding for the query
    try:
        query_embedding = embed_text(query)
        query_embedding = query_embedding.tolist()
    except Exception as e:
        return {
            "query": query,
            "total": 0,
            "results": [],
            "error": f"Failed to embed query: {str(e)}",
        }

    # Perform search
    results = db.search(
        query_embedding=query_embedding,
        limit=limit,
        project_filter=project_filter,
        session_filter=session_filter,
        chunk_type_filter=chunk_type_filter,
    )

    # Convert results to serializable format
    result_dicts = []
    for r in results:
        result_dicts.append({
            "id": r.id,
            "session_id": r.session_id,
            "project_path": r.project_path,
            "chunk_type": r.chunk_type,
            "text": r.text,
            "score": r.score,
            "metadata": r.metadata,
        })

    return {
        "query": query,
        "total": len(result_dicts),
        "results": result_dicts,
    }


def format_grouped_output(results: dict, show_full: bool = False) -> str:
    """Format search results grouped by session with summaries.

    Args:
        results: Dict with query and results list
        show_full: If True, show full text content

    Returns:
        Formatted string output grouped by session
    """
    query = results.get("query", "")
    total = results.get("total", 0)
    matches = results.get("results", [])
    error = results.get("error")

    if error:
        return f"Error: {error}"

    if total == 0:
        return f"No results found for query: '{query}'"

    # Group results by session_id
    sessions = {}
    for match in matches:
        sid = match.get("session_id", "unknown")
        if sid not in sessions:
            sessions[sid] = {
                "matches": [],
                "earliest_date": None,
            }
        sessions[sid]["matches"].append(match)

        # Track earliest date for this session's matches
        ts = match.get("metadata", {}).get("timestamp", "")
        if ts:
            date = ts[:10]
            if not sessions[sid]["earliest_date"] or date < sessions[sid]["earliest_date"]:
                sessions[sid]["earliest_date"] = date

    # Look up session summaries
    session_ids = list(sessions.keys())
    summaries = get_session_summaries(session_ids)

    # Build output
    lines = [
        f"Found {total} result(s) across {len(sessions)} session(s) for: '{query}'",
        "",
    ]

    for sid, data in sessions.items():
        # Get summary info
        summary_info = summaries.get(sid, {})
        summary = summary_info.get("summary", "No summary available")
        date = data["earliest_date"] or "unknown"

        # Truncate summary if too long
        if len(summary) > 80:
            summary = summary[:77] + "..."

        lines.append(f"Session {sid[:8]}... ({date}) - \"{summary}\"")

        # List matching content
        for match in data["matches"]:
            text = match.get("text", "")
            if not show_full and len(text) > 100:
                text = text[:97] + "..."
            text = " ".join(text.split())  # Clean whitespace
            chunk_type = match.get("chunk_type", "")
            lines.append(f"  [{chunk_type}] {text}")

        lines.append("")

    return "\n".join(lines)


def format_human_readable(results: dict, show_full: bool = False) -> str:
    """Format search results for human reading.

    Args:
        results: Dict with query and results list
        show_full: If True, show full text content

    Returns:
        Formatted string output
    """
    query = results.get("query", "")
    total = results.get("total", 0)
    matches = results.get("results", [])
    error = results.get("error")

    if error:
        return f"Error: {error}"

    if total == 0:
        return f"No results found for query: '{query}'"

    lines = [
        f"Found {total} result(s) for: '{query}'",
        "",
    ]

    for i, match in enumerate(matches, 1):
        # Create a SearchResult object for formatting
        result = SearchResult(
            id=match.get("id", ""),
            session_id=match.get("session_id", ""),
            project_path=match.get("project_path", ""),
            chunk_type=match.get("chunk_type", ""),
            text=match.get("text", ""),
            score=match.get("score", 0.0),
            metadata=match.get("metadata", {}),
        )
        lines.append(f"{i}. {format_result_text(result, show_full)}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Semantic search for Claude Code session history"
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="Search query (semantic similarity)"
    )
    parser.add_argument(
        "--query", "-q",
        dest="query_flag",
        help="Search query (alternative to positional)"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=10,
        help="Maximum results to return (default: 10)"
    )
    parser.add_argument(
        "--project", "-p",
        type=str,
        help="Filter by project path (exact match)"
    )
    parser.add_argument(
        "--session", "-s",
        type=str,
        help="Filter by session ID"
    )
    parser.add_argument(
        "--type", "-t",
        type=str,
        choices=["user_prompt", "assistant_text", "tool_use", "tool_result"],
        help="Filter by content type"
    )
    parser.add_argument(
        "--full", "-f",
        action="store_true",
        help="Show full text content (not truncated)"
    )
    parser.add_argument(
        "--group", "-g",
        action="store_true",
        help="Group results by session and show session summaries"
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output JSON format"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show database statistics"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        help="Custom database path"
    )

    args = parser.parse_args()

    # Handle stats request
    if args.stats:
        db = HistoryDB(args.db_path) if args.db_path else HistoryDB()
        stats = db.get_stats()
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print("Database Statistics:")
            print(f"  Path: {stats.get('db_path', 'unknown')}")
            print(f"  Exists: {stats.get('exists', False)}")
            print(f"  Total documents: {stats.get('total_documents', 0)}")
            print(f"  Total sessions: {stats.get('total_sessions', 0)}")
            chunk_types = stats.get("chunk_types", {})
            if chunk_types:
                print("  Chunk types:")
                for ct, count in chunk_types.items():
                    print(f"    {ct}: {count}")
        return

    # Get query from either positional or flag argument
    query = args.query or args.query_flag
    if not query:
        parser.error("Query is required (provide as positional argument or with --query)")

    # Parse db_path if provided
    db_path = Path(args.db_path) if args.db_path else None

    # Perform search
    results = search_history(
        query=query,
        limit=args.limit,
        project_filter=args.project,
        session_filter=args.session,
        chunk_type_filter=args.type,
        db_path=db_path,
    )

    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    elif args.group:
        print(format_grouped_output(results, show_full=args.full))
    else:
        print(format_human_readable(results, show_full=args.full))


if __name__ == "__main__":
    main()
