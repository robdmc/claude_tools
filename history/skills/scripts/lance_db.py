#!/usr/bin/env python3
"""LanceDB module for Claude Code history search.

Provides an interface to LanceDB for storing and searching session embeddings
with vector similarity search, full-text search, and hybrid search.
Handles database creation, document storage, and search queries.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import lancedb
import pyarrow as pa
from lancedb.rerankers import LinearCombinationReranker

from history_utils import get_claude_projects_dir


class SearchMode(Enum):
    """Search mode for queries.

    Attributes:
        VECTOR: Pure vector similarity search using embeddings
        FTS: Full-text search using keyword matching
        HYBRID: Combined vector + FTS search with weighted reranking
    """
    VECTOR = "vector"
    FTS = "fts"
    HYBRID = "hybrid"


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
        score: Similarity score (lower is better for L2 distance, higher for relevance)
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
    and vector similarity search, full-text search, and hybrid search.

    Example:
        >>> db = HistoryDB()
        >>> db.add_documents([doc1, doc2])
        >>> results = db.search(query_embedding, limit=5)
        >>> # Or use hybrid search
        >>> results = db.search(query_embedding, query_text="keyword", mode=SearchMode.HYBRID, limit=5)
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
        self._fts_index_created: bool = False

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

    def create_fts_index(self, replace: bool = False) -> bool:
        """Create a full-text search index on the text column.

        This is required for FTS and hybrid search modes.

        Args:
            replace: If True, replace existing FTS index

        Returns:
            True if index was created successfully, False otherwise
        """
        try:
            db = self._get_db()
            if self.table_name not in db.table_names():
                return False

            table = db.open_table(self.table_name)
            table.create_fts_index("text", replace=replace)
            self._fts_index_created = True
            return True
        except Exception as e:
            # Index might already exist
            if "already exists" in str(e).lower():
                self._fts_index_created = True
                return True
            return False

    def has_fts_index(self) -> bool:
        """Check if the FTS index exists on the table.

        Returns:
            True if FTS index exists, False otherwise
        """
        if self._fts_index_created:
            return True

        try:
            db = self._get_db()
            if self.table_name not in db.table_names():
                return False

            table = db.open_table(self.table_name)
            # Check if text_idx exists in the index list
            indices = table.list_indices()
            for idx in indices:
                # LanceDB names FTS indices as "<column>_idx"
                if idx.get("name") == "text_idx" or idx.get("index_type") == "FTS":
                    self._fts_index_created = True
                    return True
            return False
        except Exception:
            return False

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
        query_embedding: Optional[List[float]] = None,
        query_text: Optional[str] = None,
        mode: SearchMode = SearchMode.VECTOR,
        hybrid_weight: float = 0.7,
        limit: int = 10,
        session_filter: Optional[str] = None,
        project_filter: Optional[str] = None,
        chunk_type_filter: Optional[str] = None
    ) -> List[SearchResult]:
        """Search for documents using vector, FTS, or hybrid search.

        Args:
            query_embedding: The embedding vector for vector/hybrid search
            query_text: The text query for FTS/hybrid search
            mode: Search mode - VECTOR, FTS, or HYBRID
            hybrid_weight: Balance between vector (1.0) and FTS (0.0) for hybrid search.
                          Default 0.7 means 70% vector, 30% FTS.
            limit: Maximum number of results to return
            session_filter: Optional session ID to filter by
            project_filter: Optional project path to filter by
            chunk_type_filter: Optional chunk type to filter by

        Returns:
            List of SearchResult objects sorted by relevance (best first)

        Raises:
            ValueError: If required parameters are missing for the search mode
        """
        # Validate inputs based on mode
        if mode == SearchMode.VECTOR and query_embedding is None:
            raise ValueError("query_embedding is required for VECTOR search mode")
        if mode == SearchMode.FTS and query_text is None:
            raise ValueError("query_text is required for FTS search mode")
        if mode == SearchMode.HYBRID and (query_embedding is None or query_text is None):
            raise ValueError("Both query_embedding and query_text are required for HYBRID search mode")

        # Get embedding dimension (use 384 as default for MiniLM)
        embedding_dim = len(query_embedding) if query_embedding else 384

        try:
            table = self._get_or_create_table(embedding_dim)
        except Exception:
            # Table doesn't exist or is empty
            return []

        # Build where clause for filters
        where_clauses = []
        if session_filter:
            where_clauses.append(f"session_id = '{session_filter}'")
        if project_filter:
            where_clauses.append(f"project_path = '{project_filter}'")
        if chunk_type_filter:
            where_clauses.append(f"chunk_type = '{chunk_type_filter}'")
        where_clause = " AND ".join(where_clauses) if where_clauses else None

        # Execute search based on mode
        if mode == SearchMode.VECTOR:
            results = self._vector_search(table, query_embedding, limit, where_clause)
        elif mode == SearchMode.FTS:
            results = self._fts_search(table, query_text, limit, where_clause)
        elif mode == SearchMode.HYBRID:
            results = self._hybrid_search(table, query_embedding, query_text, limit, where_clause, hybrid_weight)
        else:
            results = []

        return results

    def _vector_search(
        self,
        table: lancedb.table.Table,
        query_embedding: List[float],
        limit: int,
        where_clause: Optional[str]
    ) -> List[SearchResult]:
        """Perform pure vector similarity search.

        Args:
            table: LanceDB table to search
            query_embedding: Query vector
            limit: Max results
            where_clause: Optional SQL where clause

        Returns:
            List of SearchResult objects
        """
        search = table.search(query_embedding)

        if where_clause:
            search = search.where(where_clause)

        results = search.limit(limit).to_list()
        return self._convert_results(results, score_field="_distance")

    def _fts_search(
        self,
        table: lancedb.table.Table,
        query_text: str,
        limit: int,
        where_clause: Optional[str]
    ) -> List[SearchResult]:
        """Perform full-text search.

        Args:
            table: LanceDB table to search
            query_text: Text query
            limit: Max results
            where_clause: Optional SQL where clause

        Returns:
            List of SearchResult objects
        """
        # FTS requires an index - check and create if needed
        if not self.has_fts_index():
            # Try to create the index automatically
            if not self.create_fts_index():
                return []

        search = table.search(query_text, query_type="fts")

        if where_clause:
            search = search.where(where_clause)

        results = search.limit(limit).to_list()
        return self._convert_results(results, score_field="_score")

    def _hybrid_search(
        self,
        table: lancedb.table.Table,
        query_embedding: List[float],
        query_text: str,
        limit: int,
        where_clause: Optional[str],
        weight: float = 0.7
    ) -> List[SearchResult]:
        """Perform hybrid search combining vector and FTS with weighted reranking.

        Args:
            table: LanceDB table to search
            query_embedding: Query vector
            query_text: Text query
            limit: Max results
            where_clause: Optional SQL where clause
            weight: Balance between vector (1.0) and FTS (0.0). Default 0.7.

        Returns:
            List of SearchResult objects
        """
        # FTS requires an index - check and create if needed
        if not self.has_fts_index():
            # Try to create the index automatically
            if not self.create_fts_index():
                # Fall back to vector search if FTS index creation fails
                return self._vector_search(table, query_embedding, limit, where_clause)

        # Use LinearCombinationReranker with configurable weight
        # weight=1.0 means 100% vector, weight=0.0 means 100% FTS
        reranker = LinearCombinationReranker(weight=weight)

        # Build hybrid search with explicit vector and text queries
        search = (
            table.search(query_type="hybrid")
            .vector(query_embedding)
            .text(query_text)
            .rerank(reranker=reranker)
        )

        if where_clause:
            search = search.where(where_clause)

        results = search.limit(limit).to_list()
        return self._convert_results(results, score_field="_relevance_score")

    def _convert_results(
        self,
        rows: List[Dict[str, Any]],
        score_field: str = "_distance"
    ) -> List[SearchResult]:
        """Convert raw LanceDB results to SearchResult objects.

        Args:
            rows: Raw results from LanceDB
            score_field: Name of the score field (_distance, _score, or _relevance_score)

        Returns:
            List of SearchResult objects
        """
        search_results = []
        for row in rows:
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
                score=row.get(score_field, 0.0),
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
            Dict with stats like total documents, sessions, FTS index status, etc.
        """
        try:
            db = self._get_db()
            if self.table_name not in db.table_names():
                return {
                    "total_documents": 0,
                    "total_sessions": 0,
                    "db_path": str(self.db_path),
                    "exists": False,
                    "has_fts_index": False,
                }

            table = db.open_table(self.table_name)
            df = table.to_pandas()

            return {
                "total_documents": len(df),
                "total_sessions": df["session_id"].nunique() if "session_id" in df.columns else 0,
                "chunk_types": df["chunk_type"].value_counts().to_dict() if "chunk_type" in df.columns else {},
                "db_path": str(self.db_path),
                "exists": True,
                "has_fts_index": self.has_fts_index(),
            }
        except Exception as e:
            return {
                "total_documents": 0,
                "total_sessions": 0,
                "db_path": str(self.db_path),
                "exists": False,
                "has_fts_index": False,
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
            self._fts_index_created = False
            return True
        except Exception:
            return False


def get_default_db() -> HistoryDB:
    """Get a HistoryDB instance with default settings.

    Returns:
        HistoryDB instance connected to the default database
    """
    return HistoryDB()
