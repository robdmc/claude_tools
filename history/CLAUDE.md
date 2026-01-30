# History Skill Development Guide

Instructions for Claude sessions working on this skill.

## Before Making Changes

1. **Invoke the skill-creator skill** for guidance on skill development best practices:
   ```
   /document-skills:skill-creator
   ```

2. **Read the current skill files** to understand the existing structure:
   - `skills/SKILL.md` - Main skill definition (Claude reads this)
   - `skills/scripts/*.py` - Python scripts for session operations

## Skill Architecture

```
history/
├── README.md                       # Human documentation
├── CLAUDE.md                       # This file - development instructions
└── skills/
    ├── SKILL.md                    # Main skill definition (required)
    └── scripts/
        ├── pyproject.toml          # Python dependencies for LanceDB stack
        ├── history_utils.py        # Shared utilities (path handling, JSONL parsing)
        │
        │   # Core Modules (LanceDB stack)
        ├── doc_extractor.py        # Extract documents from JSONL sessions
        ├── embedder.py             # Generate text embeddings (sentence-transformers)
        ├── lance_db.py             # LanceDB interface for vector storage/search
        │
        │   # CLI Scripts (LanceDB-based)
        ├── index_history.py        # Build/update vector index from sessions
        ├── search_history.py       # Semantic vector search across sessions
        ├── export_session.py       # Export sessions to various formats
        │
        │   # Legacy/Utility Scripts
        ├── list_sessions.py        # List recent sessions (metadata only)
        ├── explore_session.py      # Query within a session
        └── import_session.py       # Import/unimport sessions
```

## LanceDB Architecture

The history skill uses LanceDB for semantic search across Claude Code sessions. This enables finding conversations by meaning rather than exact keyword matches.

### Data Flow

```
Session JSONL files (in ~/.claude/projects/)
         │
         ▼
   doc_extractor.py
   (Extract documents: user prompts, assistant text, tool calls)
         │
         ▼
   embedder.py
   (Generate 384-dim embeddings via sentence-transformers)
         │
         ▼
   lance_db.py
   (Store in LanceDB at ~/.claude/history_search.lance)
         │
         ▼
   search_history.py
   (Vector similarity search)
```

### Core Components

#### history_utils.py
Shared utilities for all scripts:
- `get_claude_projects_dir()` - Path to `~/.claude/projects/`
- `decode_project_path()` / `encode_project_path()` - Handle path encoding
- `parse_jsonl()` - Parse session JSONL files
- `load_sessions_index()` - Load sessions-index.json (handles old and new formats)
- `find_session_file()` / `find_session()` - Locate sessions by ID (supports prefix matching)

#### doc_extractor.py
Extracts indexable documents from session JSONL files:
- **Document types**: `user_prompt`, `assistant_text`, `tool_use`, `tool_result`
- **Filtering**: Removes system injections, short content (< 20 chars), and thinking blocks
- **Tool content extraction**: Formats tool calls (Bash, Read, Edit, etc.) into searchable text
- **Iteration**: `iter_all_sessions()` walks all projects, `extract_all_documents()` yields docs

#### embedder.py
Generates text embeddings for vector search:
- **Model**: `all-MiniLM-L6-v2` (384-dimensional embeddings)
- **Caching**: Model cached at `~/.cache/claude-history/models/`
- **Functions**:
  - `embed_text()` - Single or batch text embedding
  - `embed_documents()` - Add 'vector' field to document dicts
  - `chunk_text()` - Split long texts into overlapping chunks
  - `text_hash()` - Content deduplication

#### lance_db.py
LanceDB interface for vector storage and search:
- **Database path**: `~/.claude/history_search.lance`
- **Table name**: `sessions`
- **Schema**: id, session_id, project_path, chunk_type, text, vector, metadata
- **Key classes**:
  - `Document` - Input document with embedding
  - `SearchResult` - Search result with score and metadata
  - `HistoryDB` - Main interface (add_documents, search, delete_session, get_stats)
- **Search**: Vector similarity with optional filters (session, project, chunk_type)

### CLI Scripts

#### index_history.py
Build or update the vector index:
```bash
# Index all sessions (skips already indexed)
python index_history.py

# Index specific session
python index_history.py --session <id>

# Filter to project
python index_history.py --project /path/to/project

# Rebuild from scratch
python index_history.py --rebuild

# Show stats
python index_history.py --stats
```

#### search_history.py
Semantic search across indexed sessions:
```bash
# Basic search
python search_history.py "how to set up authentication"

# Filter by type
python search_history.py "error handling" --type user_prompt

# Filter by project
python search_history.py "database" --project /path/to/project

# JSON output
python search_history.py "testing" --json --limit 5
```

### Dependencies

Defined in `pyproject.toml`:
- `lancedb>=0.6.0` - Vector database
- `sentence-transformers>=2.2.0` - Embedding models
- `pyarrow>=15.0.0` - Arrow format support

## Key Design Decisions

These decisions were made intentionally - preserve them unless explicitly changing:

- **Progressive disclosure**: Start with counts, expand to lists, then details
- **Token efficiency**: Minimize context usage, ask before expanding
- **Session storage**: All sessions live in `~/.claude/projects/`
- **Import behavior**: Replaces target project history (not merge)
- **Import tracking**: Uses `.claude_history_imports.json` manifest for cleanup
- **Safety**: Backups before modifying, atomic writes, dry-run support
- **Semantic search**: LanceDB enables meaning-based search, not just keywords
- **Lazy model loading**: Embedding model loaded on first use, cached for reuse
- **Incremental indexing**: Skip already-indexed sessions by default

## Making Changes

### Updating SKILL.md

This is what Claude reads when the skill is triggered. Keep it:
- Concise but complete
- Focused on "what Claude needs to do"
- Well-organized with clear sections
- Updated `allowed-tools` frontmatter when adding new scripts

### Updating scripts/

When modifying scripts:
- Keep backward compatibility with existing CLI arguments
- Support both `--json` and human-readable output
- Handle both old (list) and new (dict with entries) index formats

For LanceDB-related modules:
- Keep the modular separation (extractor -> embedder -> lance_db -> CLI)
- Maintain consistent error handling (return empty results, not exceptions)
- Use `history_utils.py` for shared functionality

## Testing Changes

### Basic Script Tests

After modifying the skill:

1. Test list: `python scripts/list_sessions.py --limit 3`
2. Test explore: `python scripts/explore_session.py <session_id> --summary`
3. Test import dry-run: `python scripts/import_session.py <session_id> --dry-run`

### LanceDB Stack Tests

Test the indexing and search pipeline:

```bash
cd skills/scripts

# 1. Check document extraction
python doc_extractor.py --stats
python doc_extractor.py --limit 5

# 2. Test embedding generation
python embedder.py --text "test query"
python embedder.py --dimension

# 3. Index a session and check stats
python index_history.py --session <session_id> --verbose
python index_history.py --stats

# 4. Test semantic search
python search_history.py "your search query" --limit 5
python search_history.py "your query" --json

# 5. Test with filters
python search_history.py "query" --type user_prompt
python search_history.py "query" --project /path/to/project

# 6. Full rebuild test (careful - rebuilds entire index)
python index_history.py --rebuild --verbose
```

### Integration Test

End-to-end flow in a scratch project:
1. Import a session: `python import_session.py <session_id> --dry-run`
2. Index the session: `python index_history.py --session <session_id>`
3. Search for content from that session: `python search_history.py "<known text>"`

## Integration Points

This skill works with:

- **Claude Code's /resume**: Import makes sessions appear in `/resume` list
- **Claude's projects directory**: Reads from `~/.claude/projects/`
- **LanceDB storage**: Index stored at `~/.claude/history_search.lance`
- **Model cache**: Embeddings model at `~/.cache/claude-history/models/`
