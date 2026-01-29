#!/usr/bin/env python3
"""Text embedding module for semantic search.

This module provides text embedding functionality using sentence-transformers,
designed for use with LanceDB vector search in the history skill.
"""

import hashlib
from pathlib import Path
from typing import List, Optional, Union

import numpy as np

# Lazy-loaded model instance
_model = None
_model_name = None

# Default embedding model - good balance of quality and speed
DEFAULT_MODEL = "all-MiniLM-L6-v2"

# Cache directory for models
DEFAULT_CACHE_DIR = Path.home() / ".cache" / "claude-history" / "models"


def get_embedding_model(
    model_name: str = DEFAULT_MODEL,
    cache_dir: Optional[Path] = None,
    device: Optional[str] = None
):
    """Get or initialize the embedding model.

    Uses lazy initialization and caches the model instance to avoid
    reloading on every call.

    Args:
        model_name: Name of the sentence-transformers model to use.
            Default is 'all-MiniLM-L6-v2' which produces 384-dim embeddings.
        cache_dir: Directory to cache downloaded models.
            Defaults to ~/.cache/claude-history/models
        device: Device to run model on ('cpu', 'cuda', 'mps').
            If None, auto-detects best available device.

    Returns:
        SentenceTransformer model instance

    Raises:
        ImportError: If sentence-transformers is not installed
    """
    global _model, _model_name

    if _model is not None and _model_name == model_name:
        return _model

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise ImportError(
            "sentence-transformers is required for embedding. "
            "Install with: pip install sentence-transformers"
        )

    if cache_dir is None:
        cache_dir = DEFAULT_CACHE_DIR

    cache_dir.mkdir(parents=True, exist_ok=True)

    _model = SentenceTransformer(
        model_name,
        cache_folder=str(cache_dir),
        device=device
    )
    _model_name = model_name

    return _model


def embed_text(
    text: Union[str, List[str]],
    model_name: str = DEFAULT_MODEL,
    normalize: bool = True,
    batch_size: int = 32
) -> np.ndarray:
    """Generate embeddings for text.

    Args:
        text: Single string or list of strings to embed
        model_name: Name of the embedding model to use
        normalize: Whether to L2-normalize the embeddings (recommended for cosine similarity)
        batch_size: Batch size for encoding multiple texts

    Returns:
        numpy array of shape (n_texts, embedding_dim) or (embedding_dim,) for single text

    Examples:
        >>> embedding = embed_text("Hello world")
        >>> embedding.shape
        (384,)

        >>> embeddings = embed_text(["Hello", "World"])
        >>> embeddings.shape
        (2, 384)
    """
    model = get_embedding_model(model_name)

    single_input = isinstance(text, str)
    if single_input:
        text = [text]

    embeddings = model.encode(
        text,
        normalize_embeddings=normalize,
        batch_size=batch_size,
        show_progress_bar=len(text) > 100
    )

    if single_input:
        return embeddings[0]

    return embeddings


def embed_documents(
    documents: List[dict],
    text_field: str = "text",
    model_name: str = DEFAULT_MODEL,
    batch_size: int = 32
) -> List[dict]:
    """Add embeddings to a list of documents.

    Takes documents with a text field and adds a 'vector' field containing
    the embedding.

    Args:
        documents: List of dicts, each containing a text field
        text_field: Name of the field containing text to embed
        model_name: Name of the embedding model to use
        batch_size: Batch size for encoding

    Returns:
        Same documents with 'vector' field added

    Example:
        >>> docs = [{"id": 1, "text": "Hello"}, {"id": 2, "text": "World"}]
        >>> docs = embed_documents(docs)
        >>> "vector" in docs[0]
        True
    """
    texts = [doc.get(text_field, "") for doc in documents]

    embeddings = embed_text(texts, model_name=model_name, batch_size=batch_size)

    for doc, embedding in zip(documents, embeddings):
        doc["vector"] = embedding.tolist()

    return documents


def get_embedding_dimension(model_name: str = DEFAULT_MODEL) -> int:
    """Get the embedding dimension for a model.

    Args:
        model_name: Name of the embedding model

    Returns:
        Dimension of the embedding vectors

    Example:
        >>> get_embedding_dimension("all-MiniLM-L6-v2")
        384
    """
    model = get_embedding_model(model_name)
    return model.get_sentence_embedding_dimension()


def text_hash(text: str) -> str:
    """Generate a hash for text content.

    Useful for caching embeddings and detecting duplicate content.

    Args:
        text: Text to hash

    Returns:
        SHA256 hash as hex string (first 16 chars)

    Example:
        >>> text_hash("Hello world")
        '64ec88ca00b268e5'
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def chunk_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    separator: str = "\n"
) -> List[str]:
    """Split text into overlapping chunks for embedding.

    Long texts should be chunked before embedding since most models
    have token limits and performance degrades with very long inputs.

    Args:
        text: Text to split
        chunk_size: Target size of each chunk in characters
        chunk_overlap: Number of characters to overlap between chunks
        separator: Preferred split point (tries to split on this first)

    Returns:
        List of text chunks

    Example:
        >>> chunks = chunk_text("Hello world. This is a test.", chunk_size=15)
        >>> len(chunks)
        2
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        if end >= len(text):
            chunks.append(text[start:])
            break

        # Try to find a good break point
        break_point = text.rfind(separator, start, end)
        if break_point == -1 or break_point <= start:
            # No separator found, try space
            break_point = text.rfind(" ", start, end)

        if break_point == -1 or break_point <= start:
            # No good break point, just cut
            break_point = end

        chunks.append(text[start:break_point])
        start = break_point - chunk_overlap

        # Skip separator if we found one
        if start < len(text) and text[start] == separator:
            start += 1

    return chunks


def main():
    """Test embedding functionality."""
    import argparse

    parser = argparse.ArgumentParser(description="Test text embedding")
    parser.add_argument("--text", "-t", help="Text to embed")
    parser.add_argument("--model", "-m", default=DEFAULT_MODEL, help="Model name")
    parser.add_argument("--dimension", "-d", action="store_true", help="Show embedding dimension")

    args = parser.parse_args()

    if args.dimension:
        dim = get_embedding_dimension(args.model)
        print(f"Model: {args.model}")
        print(f"Embedding dimension: {dim}")
        return

    if args.text:
        embedding = embed_text(args.text, model_name=args.model)
        print(f"Text: {args.text}")
        print(f"Embedding shape: {embedding.shape}")
        print(f"Embedding (first 10 values): {embedding[:10]}")
        print(f"Text hash: {text_hash(args.text)}")
    else:
        # Run basic test
        print("Running embedding test...")
        test_texts = [
            "How do I install Python packages?",
            "What's the weather like today?",
            "Installing pip dependencies in Python"
        ]

        embeddings = embed_text(test_texts, model_name=args.model)
        print(f"Model: {args.model}")
        print(f"Embedded {len(test_texts)} texts")
        print(f"Embedding shape: {embeddings.shape}")

        # Show similarity between texts
        from numpy import dot
        print("\nSimilarity matrix:")
        for i, t1 in enumerate(test_texts):
            sims = [f"{dot(embeddings[i], embeddings[j]):.3f}" for j in range(len(test_texts))]
            print(f"  {i}: {sims}  '{t1[:40]}'")


if __name__ == "__main__":
    main()
