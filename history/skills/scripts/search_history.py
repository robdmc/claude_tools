#!/usr/bin/env python3
"""Semantic search for Claude Code sessions using LanceDB.

Performs vector similarity search, full-text search, or hybrid search
against indexed session documents, finding conversations semantically
similar to the query or matching keywords.

Requires: An indexed database (run index_history.py first)
"""

import argparse
import json
from pathlib import Path
from typing import Optional

from embedder import embed_text
from history_utils import get_session_summaries
from lance_db import HistoryDB, SearchMode, SearchResult


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
    mode: str = "vector",
    hybrid_weight: float = 0.7,
    project_filter: Optional[str] = None,
    session_filter: Optional[str] = None,
    chunk_type_filter: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> dict:
    """Search indexed history using vector, FTS, or hybrid search.

    Args:
        query: The search query string
        limit: Maximum number of results to return
        mode: Search mode - 'vector', 'fts', or 'hybrid'
        hybrid_weight: Balance between vector (1.0) and keyword (0.0) for hybrid mode.
                      Default 0.7 means 70% semantic, 30% keyword.
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
            "mode": mode,
            "total": 0,
            "results": [],
            "error": "No indexed data found. Run index_history.py first.",
        }

    # Convert mode string to SearchMode enum
    try:
        search_mode = SearchMode(mode)
    except ValueError:
        return {
            "query": query,
            "mode": mode,
            "total": 0,
            "results": [],
            "error": f"Invalid search mode: {mode}. Use 'vector', 'fts', or 'hybrid'.",
        }

    # Check FTS index for FTS and hybrid modes
    if search_mode in (SearchMode.FTS, SearchMode.HYBRID) and not db.has_fts_index():
        # Try to create the index
        if not db.create_fts_index():
            if search_mode == SearchMode.FTS:
                return {
                    "query": query,
                    "mode": mode,
                    "total": 0,
                    "results": [],
                    "error": "FTS index not available. Run index_history.py --create-fts-index first.",
                }
            # For hybrid, we'll fall back to vector in the lance_db module

    # Generate embedding for vector and hybrid modes
    query_embedding = None
    if search_mode in (SearchMode.VECTOR, SearchMode.HYBRID):
        try:
            query_embedding = embed_text(query)
            query_embedding = query_embedding.tolist()
        except Exception as e:
            if search_mode == SearchMode.VECTOR:
                return {
                    "query": query,
                    "mode": mode,
                    "total": 0,
                    "results": [],
                    "error": f"Failed to embed query: {str(e)}",
                }
            # For hybrid, if embedding fails, fall back to FTS
            search_mode = SearchMode.FTS

    # Perform search
    results = db.search(
        query_embedding=query_embedding,
        query_text=query if search_mode in (SearchMode.FTS, SearchMode.HYBRID) else None,
        mode=search_mode,
        hybrid_weight=hybrid_weight,
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
        "mode": mode,
        "total": len(result_dicts),
        "results": result_dicts,
    }


def format_table_output(results: dict) -> str:
    """Format search results as a clean table with session summaries.

    Shows sessions in a scannable table format, then offers exploration options.
    This is the default progressive disclosure format.

    Args:
        results: Dict with query and results list

    Returns:
        Formatted table output with next steps
    """
    query = results.get("query", "")
    mode = results.get("mode", "vector")
    total = results.get("total", 0)
    matches = results.get("results", [])
    error = results.get("error")

    if error:
        return f"Error: {error}"

    if total == 0:
        return f"No results found for query: '{query}' (mode: {mode})"

    # Group results by session_id
    sessions = {}
    for match in matches:
        sid = match.get("session_id", "unknown")
        if sid not in sessions:
            sessions[sid] = {
                "matches": [],
                "latest_timestamp": "",
                "best_score": 0.0,
            }
        sessions[sid]["matches"].append(match)

        # Track latest timestamp for this session's matches
        ts = match.get("metadata", {}).get("timestamp", "")
        if ts:
            if not sessions[sid]["latest_timestamp"] or ts > sessions[sid]["latest_timestamp"]:
                sessions[sid]["latest_timestamp"] = ts

        # Track best score
        score = match.get("score", 0.0)
        if score > sessions[sid]["best_score"]:
            sessions[sid]["best_score"] = score

    # Look up session summaries
    session_ids = list(sessions.keys())
    summaries = get_session_summaries(session_ids)

    # Sort sessions by timestamp (most recent first)
    sorted_sessions = sorted(
        sessions.items(),
        key=lambda x: x[1]["latest_timestamp"] or "",
        reverse=True
    )

    # Build table output
    lines = [
        f"Found {len(sessions)} session(s) for: '{query}'",
        "",
        "ID        Timestamp          Summary",
        "--------  -----------------  " + "-" * 45,
    ]

    for sid, data in sorted_sessions:
        # Get summary info
        summary_info = summaries.get(sid, {})
        summary = summary_info.get("summary", "No summary available")

        # Format timestamp as "YYYY-MM-DD HH:MM"
        ts = data["latest_timestamp"]
        if ts and len(ts) >= 16:
            # "2026-01-17T18:06:35.005Z" -> "2026-01-17 18:06"
            timestamp = ts[:10] + " " + ts[11:16]
        else:
            timestamp = "unknown"

        # Truncate summary to fit table
        max_summary_len = 45
        if len(summary) > max_summary_len:
            summary = summary[:max_summary_len - 3] + "..."

        # Clean up summary (single line)
        summary = " ".join(summary.split())

        lines.append(f"{sid[:8]}  {timestamp:17}  {summary}")

    # Add exploration options
    first_id = sorted_sessions[0][0][:8] if sorted_sessions else "abc12345"
    lines.extend([
        "",
        "Next steps:",
        f"  /history what happened in {first_id}   # Explore session details",
        f"  /history export {first_id}             # Export as markdown",
        f"  /history import {first_id}             # Import for /resume",
    ])

    return "\n".join(lines)


def format_grouped_output(results: dict, show_full: bool = False) -> str:
    """Format search results grouped by session with matching content.

    Shows sessions with their matching content snippets.
    Use --group flag to get this detailed view.

    Args:
        results: Dict with query and results list
        show_full: If True, show full text content

    Returns:
        Formatted string output grouped by session
    """
    query = results.get("query", "")
    mode = results.get("mode", "vector")
    total = results.get("total", 0)
    matches = results.get("results", [])
    error = results.get("error")

    if error:
        return f"Error: {error}"

    if total == 0:
        return f"No results found for query: '{query}' (mode: {mode})"

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
        f"Found {total} match(es) across {len(sessions)} session(s) for: '{query}' (mode: {mode})",
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
    mode = results.get("mode", "vector")
    total = results.get("total", 0)
    matches = results.get("results", [])
    error = results.get("error")

    if error:
        return f"Error: {error}"

    if total == 0:
        return f"No results found for query: '{query}' (mode: {mode})"

    lines = [
        f"Found {total} result(s) for: '{query}' (mode: {mode})",
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
        description="Search Claude Code session history using vector, FTS, or hybrid search"
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="Search query"
    )
    parser.add_argument(
        "--query", "-q",
        dest="query_flag",
        help="Search query (alternative to positional)"
    )
    parser.add_argument(
        "--mode", "-m",
        type=str,
        choices=["semantic", "keyword", "hybrid"],
        default="hybrid",
        help="Search mode: 'semantic' (vector similarity), 'keyword' (full-text), or 'hybrid' (combined). Default: hybrid"
    )
    parser.add_argument(
        "--weight", "-w",
        type=float,
        default=0.7,
        help="Hybrid search weight: 0.0=keyword only, 1.0=semantic only. Default: 0.7 (70%% semantic)"
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
        "--detailed", "-d",
        action="store_true",
        help="Show detailed view with matching content snippets (default: table view)"
    )
    parser.add_argument(
        "--raw", "-r",
        action="store_true",
        help="Show raw results per match (not grouped by session)"
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
            print(f"  FTS index: {'available' if stats.get('has_fts_index', False) else 'not created'}")
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

    # Map CLI modes to internal modes
    mode_map = {"semantic": "vector", "keyword": "fts", "hybrid": "hybrid"}
    internal_mode = mode_map.get(args.mode, "hybrid")

    # Perform search
    results = search_history(
        query=query,
        limit=args.limit,
        mode=internal_mode,
        hybrid_weight=args.weight,
        project_filter=args.project,
        session_filter=args.session,
        chunk_type_filter=args.type,
        db_path=db_path,
    )

    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    elif args.raw:
        print(format_human_readable(results, show_full=args.full))
    elif args.detailed:
        print(format_grouped_output(results, show_full=args.full))
    else:
        # Default: clean table view
        print(format_table_output(results))


if __name__ == "__main__":
    main()
