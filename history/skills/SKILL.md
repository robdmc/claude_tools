---
name: history
description: Search and explore Claude Code conversation history across all projects. Use for natural language queries like "find where I created file X" or "conversations about Y". Supports semantic search with LanceDB, progressive exploration from summaries to targeted questions, exporting sessions, and importing sessions for /resume.
allowed-tools: Bash(python {SKILL_DIR}/scripts/list_sessions.py *), Bash(python {SKILL_DIR}/scripts/explore_session.py *), Bash(python {SKILL_DIR}/scripts/import_session.py *), Bash(uv run --directory {SKILL_DIR}/scripts index_history.py *), Bash(uv run --directory {SKILL_DIR}/scripts search_history.py *), Bash(uv run --directory {SKILL_DIR}/scripts export_session.py *)
---

# Conversation History Skill

Search and explore Claude Code conversation history across all projects with progressive, token-conscious disclosure. Supports hybrid search (default, combines semantic + keyword), pure semantic search (LanceDB-powered, understands meaning), and pure keyword search (full-text, exact terms).

## Usage

Invoke with `/history <natural language query>`

### Common Commands

- `/history list` - Show recent sessions across all projects
- `/history find <query>` - Keyword search sessions for a term or file
- `/history search <query>` - Semantic search (finds similar meaning, not just keywords)
- `/history what happened in session X` - Explore a specific session
- `/history export <session_id>` - Export session to Markdown or JSON
- `/history import <session_id>` - Import session to current project for /resume
- `/history index` - Index/re-index sessions for semantic search
- `/history help` - Show available commands

## Help Output

When user asks `/history help`, display:

**History Skill Commands:**
| Command | Description |
|---------|-------------|
| `list` | Show recent sessions |
| `search <query>` | Hybrid search (semantic + keyword, default) |
| `search <query> --mode semantic` | Pure semantic search (finds similar meaning) |
| `search <query> --mode keyword` | Pure keyword search (exact terms) |
| `search <query> --weight 0.9` | Adjust hybrid balance (0=keyword, 1=semantic) |
| `explore <id>` | Explore a session (summary, files, grep) |
| `export <id>` | Export session to Markdown/JSON |
| `import <id>` | Import session for /resume |
| `index` / `sync` | Build/update search index (incremental) |
| `index rebuild` | Clear and rebuild entire index from scratch |
| `index --create-fts-index` | Create FTS index (enables hybrid/keyword search) |
| `summarize <id>` | Get detailed narrative summary of a session |
| `help` | Show this help |

**Search Modes:**
- `hybrid` (default): Combines semantic + keyword. Use `--weight` to adjust (0.7 = 70% semantic)
- `semantic`: Finds similar meaning even without exact keywords
- `keyword`: Full-text search for exact terms (error codes, filenames, etc.)

## Progressive Disclosure Flow

This skill follows a progressive disclosure pattern to minimize token usage:

| Level | Token Cost | What Happens |
|-------|-----------|--------------|
| 1. Count | ~20 | "Found 12 sessions mentioning X" |
| 2. List | ~200 | Top 5 sessions with summaries |
| 3. Explore | ~100/question | Interrogate session details |
| 4. Import | 0 | Copy session to current project |
| 5. Resume | Full | User loads via /resume |

**Always present counts first, ask before expanding to full lists.**

## Scripts

### list_sessions.py

List recent sessions:

```bash
# Sessions from current directory (default)
python {SKILL_DIR}/scripts/list_sessions.py

# Sessions from all projects
python {SKILL_DIR}/scripts/list_sessions.py --all

# Sessions from specific project
python {SKILL_DIR}/scripts/list_sessions.py --project /path/to/project --limit 10
```

Arguments:
- `--limit`: Max results (default: 5)
- `--project`: Filter to specific project path (default: current directory)
- `--all`: Show sessions from all projects (overrides --project default)
- `--json`: Output JSON

### explore_session.py

Query a specific session:

```bash
# Get message flow summary
python {SKILL_DIR}/scripts/explore_session.py <session_id> --summary

# Search for pattern within session (shows match previews)
python {SKILL_DIR}/scripts/explore_session.py <session_id> --grep "pattern" --context 2

# List files created/edited
python {SKILL_DIR}/scripts/explore_session.py <session_id> --files

# Show specific message (human-readable by default)
python {SKILL_DIR}/scripts/explore_session.py <session_id> --message 5

# Show specific message as raw JSON
python {SKILL_DIR}/scripts/explore_session.py <session_id> --message 5 --raw

# Extract user prompts only (filtered, no system injections)
python {SKILL_DIR}/scripts/explore_session.py <session_id> --user-prompts --limit 3
```

Arguments:
- `session_id` (required): The session ID to explore (prefix match supported, e.g., `35377e2e`)
- `--summary`: Show message flow with tool summaries
- `--grep`: Search for pattern within session (shows actual match text with context)
- `--context`: Lines of context around grep matches (default: 2)
- `--files`: List all files created/edited
- `--message`: Show specific message by index (human-readable by default)
- `--user-prompts`: Show only user prompts, filtered to remove system injections
- `--limit`: Limit number of results (for --user-prompts)
- `--raw`: Output raw JSON for --message
- `--json`: Output JSON

### import_session.py

Import, unimport, and manage session imports:

```bash
# Preview what would happen (recommended first step)
python {SKILL_DIR}/scripts/import_session.py <session_id> --dry-run

# Actually import
python {SKILL_DIR}/scripts/import_session.py <session_id> --target /path/to/project

# List all imported sessions in current project
python {SKILL_DIR}/scripts/import_session.py --list-imports

# Preview unimport (recommended first step)
python {SKILL_DIR}/scripts/import_session.py <session_id> --unimport --dry-run

# Actually unimport (remove imported session)
python {SKILL_DIR}/scripts/import_session.py <session_id> --unimport
```

Arguments:
- `session_id`: The session ID to import/unimport (required for import/unimport)
- `--target`: Target project path (default: current directory)
- `--dry-run`: Preview changes without modifying anything
- `--list-imports`: Show all imported sessions in the project
- `--unimport`: Remove an imported session (reverses import)
- `--json`: Output JSON

**Behavior:**
- **Replaces** the target project's session history (not merge)
- Only the imported session will appear in `/resume` for that project
- Existing session JSONL files stay on disk (not deleted), just removed from index
- Use backup to restore previous history if needed

**Safety features:**
- Creates backup of sessions-index.json before modifying
- Uses atomic writes (temp file + rename) to prevent corruption
- Validates JSON structure before and after writing
- Finds existing project directories instead of creating duplicates
- Tracks imports in `.claude_history_imports.json` for easy cleanup
- Unimport only works on sessions that were imported (tracked in manifest)

## LanceDB Semantic Search Scripts

These scripts use LanceDB for semantic vector search, finding sessions by meaning rather than exact keywords. They require dependencies (lancedb, sentence-transformers) and run via UV.

### index_history.py

Index session history into LanceDB for semantic search:

```bash
# Index all sessions (skips already-indexed)
uv run --directory {SKILL_DIR}/scripts index_history.py

# Index a specific session
uv run --directory {SKILL_DIR}/scripts index_history.py --session abc123

# Index only sessions for a specific project
uv run --directory {SKILL_DIR}/scripts index_history.py --project /Users/rob/myproject

# Show indexing stats (includes search capabilities)
uv run --directory {SKILL_DIR}/scripts index_history.py --stats

# Clear and rebuild entire index
uv run --directory {SKILL_DIR}/scripts index_history.py --rebuild

# Create FTS index (required for keyword and hybrid search)
uv run --directory {SKILL_DIR}/scripts index_history.py --create-fts-index

# Rebuild FTS index (replace existing)
uv run --directory {SKILL_DIR}/scripts index_history.py --create-fts-index --rebuild-fts
```

Arguments:
- `--session`, `-s`: Index a specific session ID (prefix match supported)
- `--project`, `-p`: Filter to sessions from a specific project (substring match)
- `--rebuild`: Clear database and rebuild from scratch
- `--create-fts-index`: Create full-text search index (enables keyword/hybrid modes)
- `--rebuild-fts`: Replace existing FTS index (use with --create-fts-index)
- `--stats`: Show indexing statistics (documents, sessions, search capabilities)
- `--min-length`: Minimum content length to index (default: 20)
- `--batch-size`: Batch size for embedding generation (default: 32)
- `--db-path`: Custom database path (default: ~/.claude/history_search.lance)
- `--json`, `-j`: Output results in JSON format
- `--verbose`, `-v`: Verbose output

### search_history.py

Search using hybrid (default), semantic, or keyword modes. Default output is a table showing session ID, timestamp, and summary (most recent first):

```bash
# Hybrid search (default: 70% semantic, 30% keyword)
# Output: table with ID, timestamp, summary
uv run --directory {SKILL_DIR}/scripts search_history.py "how to set up authentication"

# Adjust hybrid balance (0=keyword only, 1=semantic only)
uv run --directory {SKILL_DIR}/scripts search_history.py "database connection" --weight 0.9
uv run --directory {SKILL_DIR}/scripts search_history.py "TypeError" --weight 0.3

# Pure semantic search (finds similar meaning)
uv run --directory {SKILL_DIR}/scripts search_history.py "how to authenticate" --mode semantic

# Pure keyword search (exact terms like error codes, filenames)
uv run --directory {SKILL_DIR}/scripts search_history.py "PGURL" --mode keyword

# Search with filters
uv run --directory {SKILL_DIR}/scripts search_history.py "database migrations" --project myproject --limit 5

# Filter by content type
uv run --directory {SKILL_DIR}/scripts search_history.py "error handling" --type user_prompt

# Output formats
uv run --directory {SKILL_DIR}/scripts search_history.py "query"            # Default: table view
uv run --directory {SKILL_DIR}/scripts search_history.py "query" --detailed # Show matching snippets
uv run --directory {SKILL_DIR}/scripts search_history.py "query" --raw      # Individual matches
uv run --directory {SKILL_DIR}/scripts search_history.py "query" --json     # JSON output

# Show database statistics (includes FTS index status)
uv run --directory {SKILL_DIR}/scripts search_history.py --stats
```

Arguments:
- `query` (positional or `--query`, `-q`): Search query
- `--mode`, `-m`: Search mode: `hybrid` (default), `semantic`, or `keyword`
- `--weight`, `-w`: Hybrid balance: 0.0=keyword only, 1.0=semantic only (default: 0.7)
- `--limit`, `-l`: Maximum results to return (default: 10)
- `--project`, `-p`: Filter by project path (exact match)
- `--session`, `-s`: Filter by session ID
- `--type`, `-t`: Filter by content type: `user_prompt`, `assistant_text`, `tool_use`, `tool_result`
- `--detailed`, `-d`: Show detailed view with matching content snippets
- `--raw`, `-r`: Show raw results per match (not grouped by session)
- `--full`, `-f`: Show full text content (not truncated, for --detailed/--raw)
- `--stats`: Show database statistics
- `--json`, `-j`: Output JSON format
- `--db-path`: Custom database path

**Note:** Requires indexed data. Run `index_history.py` first. For keyword/hybrid modes, also run `index_history.py --create-fts-index`.

**Search results include timestamps.** Each result has metadata with the original message timestamp. When the user asks about dates/timing (e.g., "when did I...", "what date...", "how old is..."), the timestamp is already in the search output - no need for additional lookups.

### export_session.py

Export session to Markdown or JSON for sharing/archiving:

```bash
# Export to Markdown (prints to stdout)
uv run --directory {SKILL_DIR}/scripts export_session.py abc123

# Export to file
uv run --directory {SKILL_DIR}/scripts export_session.py abc123 --output transcript.md

# Export as JSON
uv run --directory {SKILL_DIR}/scripts export_session.py abc123 --format json --output session.json

# Include full tool results
uv run --directory {SKILL_DIR}/scripts export_session.py abc123 --include-results

# Exclude tool call summaries
uv run --directory {SKILL_DIR}/scripts export_session.py abc123 --no-tools
```

Arguments:
- `session_id` (required): Session ID to export (prefix match supported)
- `--format`, `-f`: Output format: `markdown` (default) or `json`
- `--output`, `-o`: Output file path (prints to stdout if not specified)
- `--no-tools`: Exclude tool call summaries (markdown only)
- `--include-results`: Include full tool results
- `--json`, `-j`: Output result metadata as JSON (for --output mode)

## Natural Language → Script Mapping

When the user asks naturally, interpret and run the appropriate script:

### Search & Explore
| User Query | Action |
|------------|--------|
| "find where I created X" | search_history.py "X" |
| "conversations about Y" | search_history.py "Y" |
| "recent sessions" / "list sessions" | list_sessions.py |
| "sessions in this project" | list_sessions.py (defaults to cwd) |
| "all my sessions" | list_sessions.py --all |
| "what happened in session Z" | explore_session.py Z --summary |
| "what files were created?" | explore_session.py Z --files |
| "search for pattern in that session" | explore_session.py Z --grep "pattern" |
| "what did I ask?" / "show my prompts" | explore_session.py Z --user-prompts |

### Search (Hybrid by Default)
| User Query | Action |
|------------|--------|
| "search for X" / "find X" | search_history.py "X" (hybrid mode) |
| "search X semantically" / "meaning search" | search_history.py "X" --mode semantic |
| "keyword search X" / "exact match X" | search_history.py "X" --mode keyword |
| "search X more semantic" / "lean semantic" | search_history.py "X" --weight 0.9 |
| "search X more keyword" / "lean keyword" | search_history.py "X" --weight 0.3 |
| "find conversations similar to X" | search_history.py "X" --mode semantic |
| "find exact term X" / "search for error code X" | search_history.py "X" --mode keyword |
| "search my prompts about X" | search_history.py "X" --type user_prompt |
| "search assistant responses about X" | search_history.py "X" --type assistant_text |
| "when did I talk about X" / "what date" | search_history.py "X" (timestamps are in output) |
| "summarize sessions about X" | search_history.py "X" --group |
| "which sessions mention X" | search_history.py "X" --group |

### Indexing
| User Query | Action |
|------------|--------|
| "index my history" / "build index" | index_history.py |
| "sync" / "sync history" | index_history.py |
| "reindex everything" / "rebuild index" | index_history.py --rebuild |
| "index stats" / "how much is indexed" | index_history.py --stats |
| "enable keyword search" / "enable hybrid" | index_history.py --create-fts-index |
| "rebuild fts index" | index_history.py --create-fts-index --rebuild-fts |

### Export
| User Query | Action |
|------------|--------|
| "export session Z" | export_session.py Z |
| "export session Z to file" | export_session.py Z --output transcript.md |
| "export session Z as JSON" | export_session.py Z --format json |
| "save that conversation" | export_session.py Z --output <path> |

### Import
| User Query | Action |
|------------|--------|
| "import that" / "import session Z" | import_session.py Z |
| "bring that session here" | import_session.py Z |
| "add session Z to this project" | import_session.py Z |

### Manage Imports (cleanup)
| User Query | Action |
|------------|--------|
| "list imports" / "show imports" | import_session.py --list-imports |
| "what did I import" / "imported sessions" | import_session.py --list-imports |
| "what's imported here" | import_session.py --list-imports |
| "unimport session Z" | import_session.py Z --unimport |
| "remove imported session Z" | import_session.py Z --unimport |
| "delete imported session" | import_session.py Z --unimport |
| "clean up history" / "cleanup imports" | import_session.py --list-imports (then offer to unimport) |
| "undo import" | import_session.py Z --unimport |
| "get rid of that import" | import_session.py Z --unimport |
| "remove session Z from here" | import_session.py Z --unimport |

**Tip:** Always use `--dry-run` first when unimporting to preview what will be deleted.

## Example Interactions

### Search Flow

```
User: /history find where I created subscription_brainstorm.md

Claude: [runs search_history.py "subscription_brainstorm.md"]
        Found 3 sessions with that file across 2 projects. Show them?

User: yes

Claude: [formats results]
        1. [2026-01-26] "Subscription model planning" - claude_workspace (34 msgs)
        2. [2026-01-20] "PRD drafting" - claude_workspace (12 msgs)
        3. [2026-01-15] "Initial brainstorm" - analysis (8 msgs)

User: what happened in the first one?

Claude: [runs explore_session.py abc123 --summary]
        You asked me to read subscriptions_brainstorm.md, then create a TRD...

User: where did that file get saved?

Claude: [runs explore_session.py abc123 --files]
        subscription_trd.md → /Users/rob/claude_workspace/docs/subscription_trd.md

User: import that

Claude: [runs import_session.py abc123]
        Imported to current project. Use /resume to continue that conversation.
```

### Hybrid Search (Default)

```
User: /history search user authentication

Claude: [runs search_history.py "user authentication"]
        Found 10 results (mode: hybrid). Top matches:

        1. Session: 8f3a2c1e... | Project: web-app | Date: 2026-01-15
           Type: user_prompt | Score: 0.8734
           Content: Can you help me implement JWT-based login for my Express app?

        2. Session: 5d7b9f2a... | Project: api-server | Date: 2026-01-10
           Type: assistant_text | Score: 0.8521
           Content: Here's how to add authentication middleware using Passport.js...

User: search that more semantically

Claude: [runs search_history.py "user authentication" --weight 0.9]
        (adjusts to 90% semantic, 10% keyword)

User: explore the first one

Claude: [runs explore_session.py 8f3a2c1e --summary]
        You asked me to implement JWT authentication. I created auth middleware,
        login/logout routes, and integrated with your PostgreSQL user table...
```

### Keyword Search (Exact Terms)

```
User: /history search PGURL --mode keyword

Claude: [runs search_history.py "PGURL" --mode keyword]
        Found 3 results (mode: keyword). Top matches:

        1. Session: 2a4f1c9e... | Project: api-server | Date: 2026-01-20
           Type: user_prompt | Score: 12.34
           Content: How do I set the PGURL environment variable?

User: /history search TypeError: Cannot read property --mode keyword

Claude: [runs search_history.py "TypeError: Cannot read property" --mode keyword]
        Found exact matches for that error message...
```

### Indexing Workflow

```
User: /history index

Claude: [runs index_history.py --verbose]
        Indexing all sessions...
        Indexing session 8f3a2c1e... (web-app)
        Indexing session 5d7b9f2a... (api-server)
        ...
        Indexing complete:
          Sessions processed: 42
          Sessions skipped: 0
          Documents indexed: 1,847

        Tip: Run with --create-fts-index to enable full-text and hybrid search modes.

User: /history index --create-fts-index

Claude: [runs index_history.py --create-fts-index]
        Creating FTS index on 1,847 documents...
        FTS index created successfully.

User: /history index stats

Claude: [runs index_history.py --stats]
        LanceDB History Index Stats
        ========================================
        Database path: ~/.claude/history_search.lance
        Database exists: True

        Index Coverage:
          Indexed documents: 1,847
          Indexed sessions: 42
          Total sessions available: 42
          Coverage: 100.0%

        Search Capabilities:
          Vector search: enabled
          Full-text search (FTS): enabled
          Hybrid search: enabled

        Document types:
          user_prompt: 523
          assistant_text: 891
          tool_use: 287
          tool_result: 146
```

## Narrative Summaries (Subagent)

When the user asks for a "detailed summary", "longer summary", or "what happened in session X" and wants more than a quick overview, spawn a subagent to generate narrative summaries. This keeps the raw session data out of the main context.

**Single session:**
```
User: "give me a detailed summary of session 5fe6f22c"

Claude: [spawns Task agent with prompt:]
  "Read session 5fe6f22c using:
   - python /path/to/explore_session.py 5fe6f22c --summary
   - python /path/to/explore_session.py 5fe6f22c --user-prompts

   Write a 2-3 paragraph narrative summary of what the user was trying to accomplish,
   what was done, and the outcome. Return ONLY the formatted summary, not raw tool output."
```

**Multiple sessions - USE PARALLEL AGENTS:**
When summarizing multiple sessions, spawn one agent per session IN PARALLEL (multiple Task calls in a single message). This is faster and keeps each agent's context focused.

```
User: "summarize all those sessions about keyboard buttons"

Claude: [spawns multiple Task agents in parallel, one per session:]

Task 1: "Summarize session 5fe6f22c..."
Task 2: "Summarize session 5719c0c1..."
Task 3: "Summarize session b36a1c54..."
(all in the same message)
```

Each agent should return a formatted summary using bullets for scannability:
```
**Session <id> (<date> <start_time> - <end_time>) - <title>**
- **Goal:** One sentence - what was the user trying to accomplish?
- **What happened:**
  - Key event/attempt 1
  - Key event/attempt 2
  - Key discovery or pivot (if any)
- **Outcome:** What was the end result? (committed, abandoned, created plan, etc.)
```

The subagent should extract the time range from the first and last messages in the --summary output.

The subagent should use `subagent_type: "general-purpose"` and has access to the explore_session.py script via Bash.

**Prompt limits:** Default to `--limit 20` on `--user-prompts`. User can request more detail:

| User says | Action |
|-----------|--------|
| "summarize session X" | Default: `--limit 20` |
| "full summary of X" / "detailed summary" / "with all prompts" | No limit: omit `--limit` |
| "brief summary of X" | Shorter: `--limit 10` |

For multiple sessions, ask before spawning: "Summarize with default detail or full detail?"

**Natural language triggers:**
| User Query | Action |
|------------|--------|
| "detailed summary of session X" | Spawn subagent for single session |
| "what really happened in session X" | Spawn subagent for single session |
| "summarize those sessions" / "summarize all of them" | Spawn subagent for multiple sessions |
| "give me longer summaries" | Spawn subagent for sessions from previous search |

## Token Budget Guidelines

- Always run search/list first to get counts
- Ask user before expanding beyond top 5 results
- Use `--summary` for quick overviews instead of full content
- Only import when user explicitly wants to /resume
- The import operation itself costs 0 tokens (file operations only)
