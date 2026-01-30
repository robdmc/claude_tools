#!/usr/bin/env python3
"""LanceDB module for Claude Code history search.

Provides an interface to LanceDB for storing and searching session embeddings
with vector similarity search. Handles database creation, document storage,
and semantic search queries.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import lancedb
import pyarrow as pa

from history_utils import get_claude_projects_dir


# Default paths
DEFAULT_DB_PATH = Path.home() / ".claude" / "history_search.lance"
DEFAULT_TABLE_NAME = "sessions"


@dataclass
class Document:
    """Represents a document to be stored in LanceDB.

    Attributes:
        id: Unique identifier for the document (usually session_id + chunk index)
        session_id: The Claude session ID this document belongs to
        project_path: Path to the project this session is from
        chunk_type: Type of content (e.g., "summary", "user_message", "assistant_message")
        text: The actual text content
        embedding: Vector embedding of the text
        metadata: Additional metadata (modified time, message index, etc.)
    """
    id: str
    session_id: str
    project_path: str
    chunk_type: str
    text: str
    embedding: List[float]
    metadata: Dict[str, Any]


@dataclass
class SearchResult:
    """Represents a search result from LanceDB.

    Attributes:
        id: Document ID
        session_id: The Claude session ID
        project_path: Path to the project
        chunk_type: Type of content matched
        text: The matched text
        score: Similarity score (lower is better for L2 distance)
        metadata: Additional metadata
    """
    id: str
    session_id: str
    project_path: str
    chunk_type: str
    text: str
    score: float
    metadata: Dict[str, Any]


class HistoryDB:
    """Interface to LanceDB for storing and searching session documents.

    Handles database connection, table creation, document storage,
    and vector similarity search.

    Example:
        >>> db = HistoryDB()
        >>> db.add_documents([doc1, doc2])
        >>> results = db.search(query_embedding, limit=5)
    """

    def __init__(
        self,
        db_path: Optional[Union[str, Path]] = None,
        table_name: str = DEFAULT_TABLE_NAME
    ):
        """Initialize the LanceDB connection.

        Args:
            db_path: Path to the LanceDB database directory.
                     Defaults to ~/.claude/history_search.lance
            table_name: Name of the table to use. Defaults to "sessions"
        """
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.table_name = table_name
        self._db: Optional[lancedb.DBConnection] = None
        self._table: Optional[lancedb.table.Table] = None

    def _get_db(self) -> lancedb.DBConnection:
        """Get or create the database connection."""
        if self._db is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._db = lancedb.connect(str(self.db_path))
        return self._db

    def _get_schema(self, embedding_dim: int) -> pa.Schema:
        """Create PyArrow schema for the table.

        Args:
            embedding_dim: Dimension of the embedding vectors

        Returns:
            PyArrow schema for the documents table
        """
        return pa.schema([
            pa.field("id", pa.string()),
            pa.field("session_id", pa.string()),
            pa.field("project_path", pa.string()),
            pa.field("chunk_type", pa.string()),
            pa.field("text", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), embedding_dim)),
            pa.field("metadata", pa.string()),  # JSON-encoded
        ])

    def _get_or_create_table(self, embedding_dim: int) -> lancedb.table.Table:
        """Get existing table or create a new one.

        Args:
            embedding_dim: Dimension of the embedding vectors

        Returns:
            LanceDB table
        """
        if self._table is not None:
            return self._table

        db = self._get_db()

        # Check if table exists
        existing_tables = db.table_names()
        if self.table_name in existing_tables:
            self._table = db.open_table(self.table_name)
        else:
            # Create new table with schema
            schema = self._get_schema(embedding_dim)
            self._table = db.create_table(self.table_name, schema=schema)

        return self._table

    def add_documents(self, documents: List[Document]) -> int:
        """Add documents to the database.

        Args:
            documents: List of Document objects to add

        Returns:
            Number of documents added

        Raises:
            ValueError: If documents list is empty or embeddings have inconsistent dimensions
        """
        if not documents:
            return 0

        # Validate embedding dimensions
        embedding_dim = len(documents[0].embedding)
        for doc in documents:
            if len(doc.embedding) != embedding_dim:
                raise ValueError(
                    f"Inconsistent embedding dimensions: expected {embedding_dim}, "
                    f"got {len(doc.embedding)} for document {doc.id}"
                )

        table = self._get_or_create_table(embedding_dim)

        # Convert documents to records
        records = []
        for doc in documents:
            records.append({
                "id": doc.id,
                "session_id": doc.session_id,
                "project_path": doc.project_path,
                "chunk_type": doc.chunk_type,
                "text": doc.text,
                "vector": doc.embedding,
                "metadata": json.dumps(doc.metadata),
            })

        # Add to table
        table.add(records)
        return len(records)

    def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        session_filter: Optional[str] = None,
        project_filter: Optional[str] = None,
        chunk_type_filter: Optional[str] = None
    ) -> List[SearchResult]:
        """Search for similar documents using vector similarity.

        Args:
            query_embedding: The embedding vector for the search query
            limit: Maximum number of results to return
            session_filter: Optional session ID to filter by
            project_filter: Optional project path to filter by
            chunk_type_filter: Optional chunk type to filter by

        Returns:
            List of SearchResult objects sorted by similarity (best first)
        """
        embedding_dim = len(query_embedding)

        try:
            table = self._get_or_create_table(embedding_dim)
        except Exception:
            # Table doesn't exist or is empty
            return []

        # Build search query
        search = table.search(query_embedding)

        # Apply filters if specified
        where_clauses = []
        if session_filter:
            where_clauses.append(f"session_id = '{session_filter}'")
        if project_filter:
            where_clauses.append(f"project_path = '{project_filter}'")
        if chunk_type_filter:
            where_clauses.append(f"chunk_type = '{chunk_type_filter}'")

        if where_clauses:
            search = search.where(" AND ".join(where_clauses))

        # Execute search
        results = search.limit(limit).to_list()

        # Convert to SearchResult objects
        search_results = []
        for row in results:
            metadata = {}
            if row.get("metadata"):
                try:
                    metadata = json.loads(row["metadata"])
                except json.JSONDecodeError:
                    pass

            search_results.append(SearchResult(
                id=row["id"],
                session_id=row["session_id"],
                project_path=row["project_path"],
                chunk_type=row["chunk_type"],
                text=row["text"],
                score=row.get("_distance", 0.0),
                metadata=metadata,
            ))

        return search_results

    def delete_session(self, session_id: str) -> int:
        """Delete all documents for a session.

        Args:
            session_id: The session ID to delete

        Returns:
            Number of documents deleted
        """
        try:
            db = self._get_db()
            if self.table_name not in db.table_names():
                return 0

            table = db.open_table(self.table_name)

            # Count before delete
            count_before = table.count_rows(f"session_id = '{session_id}'")

            # Delete documents
            table.delete(f"session_id = '{session_id}'")

            return count_before
        except Exception:
            return 0

    def get_indexed_sessions(self) -> List[str]:
        """Get list of all indexed session IDs.

        Returns:
            List of unique session IDs in the database
        """
        try:
            db = self._get_db()
            if self.table_name not in db.table_names():
                return []

            table = db.open_table(self.table_name)

            # Get unique session IDs
            df = table.to_pandas()
            if "session_id" in df.columns:
                return df["session_id"].unique().tolist()
            return []
        except Exception:
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics.

        Returns:
            Dict with stats like total documents, sessions, etc.
        """
        try:
            db = self._get_db()
            if self.table_name not in db.table_names():
                return {
                    "total_documents": 0,
                    "total_sessions": 0,
                    "db_path": str(self.db_path),
                    "exists": False,
                }

            table = db.open_table(self.table_name)
            df = table.to_pandas()

            return {
                "total_documents": len(df),
                "total_sessions": df["session_id"].nunique() if "session_id" in df.columns else 0,
                "chunk_types": df["chunk_type"].value_counts().to_dict() if "chunk_type" in df.columns else {},
                "db_path": str(self.db_path),
                "exists": True,
            }
        except Exception as e:
            return {
                "total_documents": 0,
                "total_sessions": 0,
                "db_path": str(self.db_path),
                "exists": False,
                "error": str(e),
            }

    def clear(self) -> bool:
        """Clear all data from the database.

        Returns:
            True if successful, False otherwise
        """
        try:
            db = self._get_db()
            if self.table_name in db.table_names():
                db.drop_table(self.table_name)
            self._table = None
            return True
        except Exception:
            return False


def get_default_db() -> HistoryDB:
    """Get a HistoryDB instance with default settings.

    Returns:
        HistoryDB instance connected to the default database
    """
    return HistoryDB()
