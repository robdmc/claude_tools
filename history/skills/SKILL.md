---
name: history
description: Search and explore Claude Code conversation history across all projects. Use for natural language queries like "find where I created file X" or "conversations about Y". Supports progressive exploration from summaries to targeted questions to importing sessions for /resume.
allowed-tools: Bash(python {SKILL_DIR}/scripts/search_sessions.py *), Bash(python {SKILL_DIR}/scripts/list_sessions.py *), Bash(python {SKILL_DIR}/scripts/explore_session.py *), Bash(python {SKILL_DIR}/scripts/import_session.py *)
---

# Conversation History Skill

Search and explore Claude Code conversation history across all projects with progressive, token-conscious disclosure.

## Usage

Invoke with `/history <natural language query>`

### Common Commands

- `/history list` - Show recent sessions across all projects
- `/history find <query>` - Search sessions for a term or file
- `/history what happened in session X` - Explore a specific session
- `/history import <session_id>` - Import session to current project for /resume

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

### search_sessions.py

Search all sessions for a term:

```bash
# Basic search (summary and firstPrompt only)
python {SKILL_DIR}/scripts/search_sessions.py --query "subscription" --limit 5

# Deep search (also searches inside JSONL message content)
python {SKILL_DIR}/scripts/search_sessions.py --query "efficiency" --deep --limit 10
```

Arguments:
- `--query` (required): Search term (searches summary and firstPrompt)
- `--deep`: Also search inside JSONL message content (slower but finds more)
- `--limit`: Max results (default: 5)
- `--json`: Output JSON instead of human-readable

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

## Natural Language → Script Mapping

When the user asks naturally, interpret and run the appropriate script:

### Search & Explore
| User Query | Action |
|------------|--------|
| "find where I created X" | search_sessions.py --query "X" |
| "conversations about Y" | search_sessions.py --query "Y" |
| "deep search for Z" | search_sessions.py --query "Z" --deep |
| "recent sessions" / "list sessions" | list_sessions.py |
| "sessions in this project" | list_sessions.py (defaults to cwd) |
| "all my sessions" | list_sessions.py --all |
| "what happened in session Z" | explore_session.py Z --summary |
| "what files were created?" | explore_session.py Z --files |
| "search for pattern in that session" | explore_session.py Z --grep "pattern" |
| "what did I ask?" / "show my prompts" | explore_session.py Z --user-prompts |

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

## Example Interaction

```
User: /history find where I created subscription_brainstorm.md

Claude: [runs search_sessions.py --query "subscription_brainstorm.md"]
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

## Token Budget Guidelines

- Always run search/list first to get counts
- Ask user before expanding beyond top 5 results
- Use `--summary` for quick overviews instead of full content
- Only import when user explicitly wants to /resume
- The import operation itself costs 0 tokens (file operations only)
