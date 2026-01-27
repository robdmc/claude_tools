# History

Search and explore Claude Code conversation history across all projects. Find past sessions, explore what happened in them, and import sessions to resume work.

## Features

- **Search**: Find sessions by keyword across all projects
- **List**: Show recent sessions with summaries
- **Explore**: Query within a session (files created, message flow, grep)
- **Import/Unimport**: Bring sessions to current project for `/resume`

## Usage

Invoke with `/history <natural language query>`:

```
/history list                          # Recent sessions
/history find subscription model       # Search for a term
/history what happened in abc123       # Explore a session
/history import abc123                 # Import for /resume
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

### search_sessions.py

Search all sessions for a term:

```bash
python search_sessions.py --query "subscription" --limit 5 --json
```

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

## Installation

Use the `/install` command from the claude_tools repository:

```
/install history
```

Or manually copy/symlink the `history/skills/` directory to your Claude Code skills location.
