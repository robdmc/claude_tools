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
        ├── search_sessions.py      # Search across all sessions
        ├── list_sessions.py        # List recent sessions
        ├── explore_session.py      # Query within a session
        └── import_session.py       # Import/unimport sessions
```

## Key Design Decisions

These decisions were made intentionally - preserve them unless explicitly changing:

- **Progressive disclosure**: Start with counts, expand to lists, then details
- **Token efficiency**: Minimize context usage, ask before expanding
- **Session storage**: All sessions live in `~/.claude/projects/`
- **Import behavior**: Replaces target project history (not merge)
- **Import tracking**: Uses `.claude_history_imports.json` manifest for cleanup
- **Safety**: Backups before modifying, atomic writes, dry-run support

## Making Changes

### Updating SKILL.md

This is what Claude reads when the skill is triggered. Keep it:
- Concise but complete
- Focused on "what Claude needs to do"
- Well-organized with clear sections
- Updated `allowed-tools` frontmatter when adding new scripts

### Updating scripts/

The Python scripts are standalone and use only standard library:
- `search_sessions.py` - Searches `summary` and `firstPrompt` fields
- `list_sessions.py` - Lists sessions sorted by modified time
- `explore_session.py` - Parses JSONL files for detailed queries
- `import_session.py` - Copies sessions between projects

When modifying scripts:
- Keep backward compatibility with existing CLI arguments
- Support both `--json` and human-readable output
- Handle both old (list) and new (dict with entries) index formats

## Testing Changes

After modifying the skill:

1. Test search: `python scripts/search_sessions.py --query "test" --limit 3`
2. Test list: `python scripts/list_sessions.py --limit 3`
3. Test explore: `python scripts/explore_session.py <session_id> --summary`
4. Test import dry-run: `python scripts/import_session.py <session_id> --dry-run`
5. Test import flow end-to-end in a scratch project

## Integration Points

This skill works with:

- **Claude Code's /resume**: Import makes sessions appear in `/resume` list
- **Claude's projects directory**: Reads from `~/.claude/projects/`
