#!/usr/bin/env python3
"""Index Claude Code history into LanceDB for semantic search.

This CLI script extracts documents from Claude Code sessions, generates
embeddings, and stores them in a LanceDB database for fast vector search.

Usage:
    # Index all sessions
    python index_history.py

    # Index only sessions for a specific project
    python index_history.py --project /Users/rob/myproject

    # Index a specific session
    python index_history.py --session abc123

    # Show indexing stats
    python index_history.py --stats

    # Clear and rebuild the index
    python index_history.py --rebuild
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Import from local modules
from doc_extractor import (
    Document as ExtractedDocument,
    extract_all_documents,
    extract_documents_from_session,
    get_session_stats,
    iter_all_sessions,
)
from embedder import embed_text, get_embedding_dimension, text_hash
from history_utils import find_session_file, decode_project_path
from lance_db import Document as LanceDocument, HistoryDB, get_default_db


def create_lance_document(
    extracted_doc: ExtractedDocument,
    embedding: list[float],
    chunk_index: int = 0,
) -> LanceDocument:
    """Convert an extracted document to a LanceDB document.

    Args:
        extracted_doc: Document extracted from a session
        embedding: The embedding vector for the document
        chunk_index: Index for chunked documents (0 for single-chunk docs)

    Returns:
        LanceDocument ready for storage
    """
    doc_id = f"{extracted_doc.session_id}_{extracted_doc.message_index}_{chunk_index}"

    return LanceDocument(
        id=doc_id,
        session_id=extracted_doc.session_id,
        project_path=extracted_doc.project_path,
        chunk_type=extracted_doc.doc_type,
        text=extracted_doc.content,
        embedding=embedding,
        metadata={
            "timestamp": extracted_doc.timestamp,
            "message_index": extracted_doc.message_index,
            "content_hash": text_hash(extracted_doc.content),
            **extracted_doc.metadata,
        },
    )


def index_documents(
    documents: list[ExtractedDocument],
    db: HistoryDB,
    batch_size: int = 32,
    verbose: bool = False,
) -> int:
    """Index a list of documents into LanceDB.

    Args:
        documents: List of extracted documents to index
        db: HistoryDB instance
        batch_size: Number of documents to embed at once
        verbose: Print progress information

    Returns:
        Number of documents indexed
    """
    if not documents:
        return 0

    total_indexed = 0

    # Process in batches
    for i in range(0, len(documents), batch_size):
        batch = documents[i : i + batch_size]

        # Extract texts and generate embeddings
        texts = [doc.content for doc in batch]
        embeddings = embed_text(texts, batch_size=batch_size)

        # Convert to LanceDB documents
        lance_docs = []
        for j, (doc, embedding) in enumerate(zip(batch, embeddings)):
            lance_doc = create_lance_document(doc, embedding.tolist())
            lance_docs.append(lance_doc)

        # Add to database
        added = db.add_documents(lance_docs)
        total_indexed += added

        if verbose:
            print(f"  Indexed batch {i // batch_size + 1}: {added} documents")

    return total_indexed


def index_session(
    session_id: str,
    db: HistoryDB,
    min_content_length: int = 20,
    verbose: bool = False,
) -> int:
    """Index a single session.

    Args:
        session_id: The session ID to index
        db: HistoryDB instance
        min_content_length: Minimum content length to include
        verbose: Print progress information

    Returns:
        Number of documents indexed
    """
    jsonl_path = find_session_file(session_id)
    if not jsonl_path:
        if verbose:
            print(f"Session {session_id} not found")
        return 0

    # Get project path from parent directory
    project_path = decode_project_path(jsonl_path.parent.name)

    # Check if session is already indexed
    indexed_sessions = db.get_indexed_sessions()
    full_session_id = jsonl_path.stem

    if full_session_id in indexed_sessions:
        if verbose:
            print(f"Session {session_id} already indexed, re-indexing...")
        db.delete_session(full_session_id)

    # Extract documents
    docs = extract_documents_from_session(
        jsonl_path, full_session_id, project_path, min_content_length
    )

    if verbose:
        print(f"Extracted {len(docs)} documents from session {session_id[:8]}...")

    # Index documents
    return index_documents(docs, db, verbose=verbose)


def index_all_sessions(
    db: HistoryDB,
    project_filter: Optional[str] = None,
    min_content_length: int = 20,
    skip_indexed: bool = True,
    verbose: bool = False,
) -> dict:
    """Index all sessions.

    Args:
        db: HistoryDB instance
        project_filter: Optional substring to filter projects
        min_content_length: Minimum content length to include
        skip_indexed: Skip sessions that are already indexed
        verbose: Print progress information

    Returns:
        Dict with indexing statistics
    """
    indexed_sessions = set(db.get_indexed_sessions()) if skip_indexed else set()
    stats = {
        "sessions_processed": 0,
        "sessions_skipped": 0,
        "documents_indexed": 0,
        "errors": [],
    }

    for session_id, project_path, jsonl_path in iter_all_sessions():
        # Apply project filter
        if project_filter and project_filter not in project_path:
            continue

        # Skip already indexed
        if skip_indexed and session_id in indexed_sessions:
            stats["sessions_skipped"] += 1
            continue

        if verbose:
            print(f"Indexing session {session_id[:8]}... ({project_path})")

        try:
            # Extract documents from this session
            docs = extract_documents_from_session(
                jsonl_path, session_id, project_path, min_content_length
            )

            if docs:
                count = index_documents(docs, db, verbose=verbose)
                stats["documents_indexed"] += count
                stats["sessions_processed"] += 1
            else:
                stats["sessions_skipped"] += 1
                if verbose:
                    print(f"  No indexable content in session")

        except Exception as e:
            stats["errors"].append({"session_id": session_id, "error": str(e)})
            if verbose:
                print(f"  Error: {e}")

    return stats


def show_stats(db: HistoryDB, json_output: bool = False) -> None:
    """Show indexing statistics.

    Args:
        db: HistoryDB instance
        json_output: Output in JSON format
    """
    db_stats = db.get_stats()
    session_stats = get_session_stats()

    combined = {
        "database": db_stats,
        "sessions": session_stats,
        "coverage": {
            "indexed_sessions": db_stats.get("total_sessions", 0),
            "total_sessions": session_stats.get("total_sessions", 0),
        },
    }

    if db_stats.get("total_sessions", 0) > 0 and session_stats.get("total_sessions", 0) > 0:
        combined["coverage"]["percentage"] = round(
            100.0 * db_stats["total_sessions"] / session_stats["total_sessions"], 1
        )

    if json_output:
        print(json.dumps(combined, indent=2))
    else:
        print("LanceDB History Index Stats")
        print("=" * 40)
        print(f"Database path: {db_stats.get('db_path', 'N/A')}")
        print(f"Database exists: {db_stats.get('exists', False)}")
        print()
        print("Index Coverage:")
        print(f"  Indexed documents: {db_stats.get('total_documents', 0)}")
        print(f"  Indexed sessions: {db_stats.get('total_sessions', 0)}")
        print(f"  Total sessions available: {session_stats.get('total_sessions', 0)}")
        if combined["coverage"].get("percentage"):
            print(f"  Coverage: {combined['coverage']['percentage']}%")
        print()
        if db_stats.get("chunk_types"):
            print("Document types:")
            for chunk_type, count in db_stats["chunk_types"].items():
                print(f"  {chunk_type}: {count}")


def main():
    parser = argparse.ArgumentParser(
        description="Index Claude Code history into LanceDB for semantic search"
    )
    parser.add_argument(
        "--session",
        "-s",
        type=str,
        help="Index a specific session ID (supports prefix matching)",
    )
    parser.add_argument(
        "--project",
        "-p",
        type=str,
        help="Filter to specific project (substring match)",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Clear database and rebuild index from scratch",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show indexing statistics",
    )
    parser.add_argument(
        "--min-length",
        type=int,
        default=20,
        help="Minimum content length to index (default: 20)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Batch size for embedding (default: 32)",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        help="Custom database path (default: ~/.claude/history_search.lance)",
    )
    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output results in JSON format",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    # Initialize database
    db = HistoryDB(db_path=args.db_path) if args.db_path else get_default_db()

    # Handle --stats
    if args.stats:
        show_stats(db, json_output=args.json)
        return

    # Handle --rebuild
    if args.rebuild:
        if args.verbose:
            print("Clearing existing index...")
        db.clear()

    # Handle --session
    if args.session:
        count = index_session(
            args.session,
            db,
            min_content_length=args.min_length,
            verbose=args.verbose,
        )
        result = {
            "session_id": args.session,
            "documents_indexed": count,
        }
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Indexed {count} documents from session {args.session}")
        return

    # Index all sessions
    if args.verbose:
        print("Indexing all sessions...")
        if args.project:
            print(f"  Filtering to projects matching: {args.project}")

    stats = index_all_sessions(
        db,
        project_filter=args.project,
        min_content_length=args.min_length,
        skip_indexed=not args.rebuild,
        verbose=args.verbose,
    )

    if args.json:
        print(json.dumps(stats, indent=2))
    else:
        print()
        print("Indexing complete:")
        print(f"  Sessions processed: {stats['sessions_processed']}")
        print(f"  Sessions skipped: {stats['sessions_skipped']}")
        print(f"  Documents indexed: {stats['documents_indexed']}")
        if stats["errors"]:
            print(f"  Errors: {len(stats['errors'])}")
            for err in stats["errors"][:3]:
                print(f"    - {err['session_id'][:8]}: {err['error']}")


if __name__ == "__main__":
    main()
