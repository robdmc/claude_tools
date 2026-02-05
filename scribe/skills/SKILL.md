---
name: scribe
description: Maintains a narrative log of exploratory work with file archives and git state tracking. Capabilities: (1) Log entries with propose-confirm flow, (2) Archive files linked to entries, (3) Capture git state (commit hash), (4) Create git commits with entry as message, (5) Restore archived files, (6) Query past work by time or topic, (7) Link related entries for thread tracking. Activates when user addresses "scribe" directly (e.g., "hey scribe, log this", "scribe, save this notebook", "scribe, what did we try yesterday?") or uses `/scribe` commands.
disable-model-invocation: true
allowed-tools: Read, Edit, Glob, Grep, Bash(uv run --project * python *), Bash(mkdir *), Bash(rm -f *), Bash(git status*), Bash(git rev-parse*), Bash(git add*), Bash(git commit*)
argument-hint: [log | git entry | save <file> | restore <asset> | ask <question>]
---

# Scribe

The scribe maintains a narrative log of your exploratory work, can archive important files, and tracks git state.

**Address naturally:** "hey scribe, log this" / "scribe, save this notebook" / "scribe, what did we try yesterday?"

## Quick Reference

| Mode | Trigger | Action |
|------|---------|--------|
| Log | "scribe, log this" | Propose → confirm → prepare → Edit → finalize |
| Git entry | "scribe, git entry" | Same flow with `--git-entry` flag (creates commit) |
| Archive | "scribe, save notebook.ipynb" | Same flow with `--archive` flag |
| Restore | "scribe, restore the ETL script" | Copy from assets |
| Query | "scribe, what did we try?" | Search and summarize |

**Important:** Git entries ONLY happen when user explicitly says "git". Never auto-promote.

## CRITICAL: Always Propose Before Finalizing

**NEVER** run `entry.py prepare` or `entry.py finalize` without first:
1. Showing the user the proposed entry text (title + body) in a markdown block
2. Getting explicit user approval ("ok", "yes", "looks good", etc.)

This applies to ALL entry types (log, git-entry, archive).

### Example Propose Step

> Here's the entry I'll create:
>
> **Title:** Migrate signup forecast to Parquet format
>
> **Body:** Removed all DuckDB dependencies, switching to a simpler Parquet-based workflow. The notebook now loads from `subscriptions.parquet` and saves to `signup_forecast.parquet`...
>
> **Files touched:** `compute_signup_forecast.nb.py`
>
> Does this look good?

## Directory Structure

```
.scribe/
├── 2026-01-23.md      # Daily log files (tracked in git)
├── assets/            # Archived files (gitignored)
└── diffs/             # Legacy diffs (gitignored, not created for new entries)
```

## Entry Flow

1. **Assess** — Check context, recent logs, `git status`
2. **Propose** — Draft the full entry text (title and body) and show it to the user in a markdown block. Ask "Does this look good?" or "Should I proceed?"
3. **Confirm** — STOP and WAIT for explicit user approval ("ok", "yes", "looks good", etc.). Do NOT proceed until user confirms.
4. **Prepare** — `entry.py prepare [options]` → outputs staging file path
5. **Edit title** — Replace `__TITLE__` in staging file
6. **Edit body** — Replace `__BODY__` in staging file
7. **Finalize** — `entry.py finalize` → validates, appends to log, archives files

### Prepare Command

```bash
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/entry.py prepare [options]
```

| Option | Description |
|--------|-------------|
| `--git-entry` | Create git commit when finalizing |
| `--touched "file.py:desc"` | Add to **Files touched:** section (repeatable) |
| `--archive "file.py:desc"` | Archive file when finalizing (repeatable) |
| `--related ID` | Add to **Related:** section with auto title lookup (repeatable) |

Outputs the staging file path (e.g., `.scribe/__2026-01-23-14-35__.md`).

### Staging File

The staging file contains placeholders to fill:

```markdown
---
id: 2026-01-23-14-35
timestamp: "14:35"
title: __TITLE__
git: abc123
_pending:
  git_entry: false
---
## 14:35 — __TITLE__

__BODY__

**Files touched:**
- `etl.py` — Added coalesce logic

---
```

Use the Edit tool to replace `__TITLE__` and `__BODY__` with actual content.

### Finalize Command

```bash
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/entry.py finalize
```

This validates placeholders are filled, strips `_pending`, archives files, appends to daily log, and (if git-entry) creates commit.

## Scripts

Scripts in `{SKILL_DIR}/scripts/`. Run with: `uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/<script.py>`

| Script | Purpose |
|--------|---------|
| `entry.py prepare` | Create staging file with placeholders |
| `entry.py finalize` | Complete entry (archive, append, commit) |
| `entry.py abort` | Delete staging file (recover from interruption) |
| `entry.py status` | Show pending entry state |
| `entry.py last --with-title` | Get last entry ID (for `--related`) |
| `assets.py save <id> <file>` | Archive a file |
| `assets.py list [filter]` | List archived files |
| `assets.py get <asset> --dest <dir>` | Restore a file |
| `validate.py` | Check for errors |

## Entry Structure

Daily logs (`.scribe/YYYY-MM-DD.md`) contain entries:

```markdown
---
id: 2026-01-23-14-35
timestamp: "14:35"
title: Entry title here
git: abc1234
---
## 14:35 — Entry title here

Narrative...

**Files touched:**
- `file.py` — Description

---
```

Searchable fields: `id:`, `title:`, `git:`, `mode: git-entry`, `**Related:**`, `**Archived:**`

## Querying

- **Time-based:** Read `.scribe/YYYY-MM-DD.md` directly
- **Topic-based:** `Grep` in `.scribe/`, then Read matches
- **Assets:** `assets.py list [filter]`

## Error Recovery

| Command | Use |
|---------|-----|
| `entry.py abort` | Discard pending entry |
| `entry.py status` | Check pending state |
| `entry.py edit-latest show` | View last finalized entry |
| `entry.py edit-latest delete` | Remove last entry + assets |
| `entry.py edit-latest replace --file` | Replace last entry content |

## Principles

- **Narrator, not stenographer** — Write prose, not dumps
- **Capture the why** — Not just what, but why it was tried
- **Stay concise** — Entries should be scannable
- **Preserve dead ends** — Failed approaches prevent repeats
- **Git state anchors context** — Commit hash precisely identifies code state

## Reference Files

For detailed examples: [references/entries.md](references/entries.md) | [references/querying.md](references/querying.md) | [references/recovery.md](references/recovery.md)
