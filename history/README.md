# History

Search and explore Claude Code conversation history across all projects. Find past sessions by meaning (semantic search) or keyword, explore what happened in them, export transcripts, and import sessions to resume work.

## Features

- **Hybrid Search**: Combines semantic (vector) and keyword (full-text) search with configurable balance
- **Semantic Search**: Find sessions by meaning using LanceDB vector search
- **Keyword Search**: Full-text search for exact terms like error codes or filenames
- **List**: Show recent sessions with summaries
- **Explore**: Query within a session (files created, message flow, grep)
- **Export**: Save sessions as Markdown or JSON transcripts
- **Import/Unimport**: Bring sessions to current project for `/resume`

## Usage

Invoke with `/history <natural language query>`:

```
/history list                          # Recent sessions
/history search authentication setup   # Semantic search (finds similar meaning)
/history what happened in abc123       # Explore a session
/history export abc123                 # Export to Markdown
/history import abc123                 # Import for /resume
/history index                         # Build/update search index
```

## Progressive Disclosure

The skill minimizes token usage through progressive disclosure:

| Level | Token Cost | What Happens |
|-------|-----------|--------------|
| 1. Count | ~20 | "Found 12 sessions mentioning X" |
| 2. List | ~200 | Top 5 sessions with summaries |
| 3. Explore | ~100/question | Interrogate session details |
| 4. Import | 0 | Copy session to current project |
| 5. Resume | Full | User loads via /resume |

## Scripts

Scripts in `skills/scripts/` fall into two categories:

### Standard Python Scripts

Run directly with `python`:

```bash
python list_sessions.py --limit 10 --json
python explore_session.py <session_id> --summary
python import_session.py <session_id> --dry-run
```

### LanceDB Scripts (require UV)

These require dependencies (lancedb, sentence-transformers) and run via UV:

```bash
# Index sessions for semantic search
uv run --directory skills/scripts index_history.py --stats

# Semantic search
uv run --directory skills/scripts search_history.py "how to set up auth"

# Export session
uv run --directory skills/scripts export_session.py <session_id> --output transcript.md
```

## Script Reference

### list_sessions.py

List recent sessions:

```bash
python list_sessions.py --limit 10 --project /path/to/project --json
```

### explore_session.py

Query a specific session:

```bash
python explore_session.py <session_id> --summary     # Message flow
python explore_session.py <session_id> --files       # Files created/edited
python explore_session.py <session_id> --grep "X"    # Search within
python explore_session.py <session_id> --message 5   # Specific message
```

### import_session.py

Import/manage sessions:

```bash
python import_session.py <session_id> --dry-run     # Preview import
python import_session.py <session_id>               # Actually import
python import_session.py --list-imports             # Show imported sessions
python import_session.py <session_id> --unimport    # Remove import
```

### index_history.py

Build/update the LanceDB vector index:

```bash
uv run index_history.py                    # Index new sessions
uv run index_history.py --rebuild          # Rebuild entire index
uv run index_history.py --stats            # Show index statistics
uv run index_history.py --session abc123   # Index specific session
uv run index_history.py --create-fts-index # Create FTS index for hybrid search
uv run index_history.py --create-fts-index --rebuild-fts  # Rebuild FTS index
```

### search_history.py

Search using hybrid (default), semantic, or keyword modes:

```bash
# Hybrid search (default: 70% semantic, 30% keyword)
uv run search_history.py "authentication setup"

# Adjust hybrid balance (0=keyword, 1=semantic)
uv run search_history.py "database connection" --weight 0.9   # More semantic
uv run search_history.py "TypeError" --weight 0.3             # More keyword

# Pure semantic (vector similarity)
uv run search_history.py "how to authenticate" --mode semantic

# Pure keyword (full-text search, good for exact terms)
uv run search_history.py "PGURL" --mode keyword

# Filters
uv run search_history.py "errors" --type user_prompt   # Filter by type
uv run search_history.py "testing" --project myapp     # Filter by project

# Output formats
uv run search_history.py "query"               # Default: table view (ID, timestamp, summary)
uv run search_history.py "query" --detailed    # Show matching content snippets
uv run search_history.py "query" --raw         # Show individual matches (not grouped)
uv run search_history.py "query" --json        # JSON output
```

### export_session.py

Export sessions to portable formats:

```bash
uv run export_session.py <session_id>                    # Print Markdown
uv run export_session.py <session_id> --output file.md   # Save to file
uv run export_session.py <session_id> --format json      # Export as JSON
uv run export_session.py <session_id> --include-results  # Include tool results
```

## Installation

Use the `/install` command from the claude_tools repository:

```
/install history
```

Or manually copy/symlink the `history/skills/` directory to your Claude Code skills location.

## Requirements

- **Standard scripts**: Python 3.9+
- **LanceDB scripts**: UV (for dependency management), ~500MB for embedding model on first run
