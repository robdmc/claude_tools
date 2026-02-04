# Scribe — A Work Log for Exploratory Projects

Scribe is a Claude Code skill that keeps a running narrative log of your exploratory work. Instead of losing track of what you tried, why it failed, and what finally worked, the scribe captures it all in plain markdown files you can read anytime.

## What It Does

- **Logs your work** — Narrative entries describing what you did, what worked, what didn't
- **Tracks git state** — Captures commit hash with each entry
- **Creates git commits** — Optionally commits your changes with the entry as the message
- **Snapshots files** — Archives versions of files at meaningful moments
- **Answers questions** — "What did we try for the null problem?" "Where did we leave off?"
- **Tracks threads** — Links related entries so you can trace an investigation from start to finish
- **Fixes mistakes** — Edit or delete entries when something goes wrong

## Requirements

- Python 3.9 or later
- [uv](https://github.com/astral-sh/uv) for dependency management
- Claude Code

## Installation

Place the `scribe/` folder in your Claude Code skills directory:

```
~/.claude/skills/scribe/
├── SKILL.md
├── references/
│   ├── entries.md
│   ├── querying.md
│   └── recovery.md
└── scripts/
    ├── entry.py
    ├── assets.py
    ├── validate.py
    ├── git_state.py
    ├── git_entry.py
    ├── common.py
    └── pyproject.toml
```

On first use, the scribe creates a `.scribe/` directory in your project.

## Usage

Just talk to the scribe naturally during your Claude Code session:

### Logging

```
"hey scribe, log this"
"scribe, we just figured out the bug — it was timezone handling"
"scribe — this was a dead end, log it"
"scribe, quick log: fixed the off-by-one error"
```

The scribe proposes an entry for you to review before writing. It automatically captures the current git commit hash.

### Git Entries (Commit Mode)

When you want to create a git commit along with your log entry, explicitly say "git":

```
"scribe, git entry — this fixes the ETL bug"
"scribe, commit this with git"
"log this with git"
```

The scribe will:
1. Show you which tracked files will be committed
2. Propose an entry for your approval
3. Create a commit with the entry text as the commit message
4. Log the entry with the commit hash

**Note:** Git entries only happen when you explicitly use the word "git". Regular log entries capture git state but don't create commits.

### Archiving Files

```
"scribe, save this notebook"
"scribe, snapshot the ETL script before I refactor"
"scribe, archive clustering.ipynb — this is the first version that works"
```

Files are copied to `.scribe/assets/` and linked in the log entry. Each archived file is named with the entry ID (e.g., `2026-01-23-14-35-clustering.ipynb`).

### Restoring Files

```
"scribe, restore the notebook from before the refactor"
"scribe, bring back the ETL script we saved last Tuesday"
```

Restored files appear next to the current version with an underscore prefix (e.g., `_2026-01-23-14-35-clustering.ipynb`) for easy comparison. The scribe never overwrites existing files.

### Querying

```
"scribe, what did we do today?"
"scribe, what did we try for the null problem?"
"scribe, where did we leave off?"
"scribe, what's still unresolved?"
"scribe, summarize last week"
"scribe, what archives do we have of the notebook?"
```

### Fixing Mistakes

```
"scribe, show me the last entry"
"scribe, delete that last entry"
"scribe, fix the last entry — the title should say 'timezone' not 'null'"
"scribe, re-archive with the correct file"
```

If an entry has errors or you want to change it, the scribe can show, edit, replace, or delete the most recent entry. Deleting an entry also removes any files it archived.

### Slash Commands

If you prefer explicit commands:

```
/scribe                              — log an entry
/scribe git entry                    — log and create git commit
/scribe save clustering.ipynb        — log and archive a file
/scribe ask what did we try?         — query the logs
```

## What Gets Created

The scribe creates a `.scribe/` directory in your project:

```
.scribe/
├── 2026-01-23.md          # Daily log file (tracked in git)
├── 2026-01-24.md          # One file per day
├── assets/
│   ├── 2026-01-23-14-35-clustering.ipynb
│   └── 2026-01-24-09-15-etl.py
└── diffs/                 # Legacy (not created for new entries)
```

**Log files** are append-only markdown, tracked in git. Each entry has YAML frontmatter with ID, timestamp, title, and git hash.

**Assets** are snapshots of files, named with the entry ID that archived them. These are gitignored.

The `.gitignore` is automatically configured:
- `.scribe/assets/` — archived files
- `.scribe/diffs/` — legacy diffs
- `.scribe/__*__.md` — staging files
- `_20*-*` — restored files (underscore prefix)

## Example Entry

```markdown
---
id: 2026-01-23-14-35
timestamp: "14:35"
title: Fixed null handling in ETL pipeline
git: abc1234
---
## 14:35 — Fixed null handling in ETL pipeline

Found that nulls originated from the 2019 migration. The legacy system used
empty strings, but the new schema expects actual NULLs. Updated `etl.py` to
coalesce empty strings to NULL for pre-2019 records.

**Files touched:**
- `etl.py` — Added coalesce logic in transform step
- `exploration.ipynb` — Validated fix on sample data

**Archived:**
- `src/etl/pipeline.py` → [`2026-01-23-14-35-pipeline.py`](assets/2026-01-23-14-35-pipeline.py) — Before null fix

---
```

The timestamp, ID, and git metadata are added automatically — you just provide the title and content.

## Git Entry Example

When you create a git entry, the commit hash references a commit you just made:

```markdown
---
id: 2026-01-23-16-20
timestamp: "16:20"
title: Completed ETL refactor
git: def5678
mode: git-entry
---
## 16:20 — Completed ETL refactor

Refactored the ETL pipeline to use the new streaming approach...

---
```

The commit `def5678` contains all your staged changes, with the full entry text as the commit message.

## Linking Related Entries

When you're following up on previous work, the scribe links entries together:

```
"scribe, the timezone hypothesis was a dead end — link back to those entries"
"scribe, this connects to the null handling work from yesterday"
```

Entries include a **Related** section that lets you trace investigations:

```markdown
**Related:** 2026-01-23-14-35 — Fixed null handling in ETL pipeline
```

## Validation

The scribe automatically validates entries after writing. Validation checks:

- Every entry has a valid ID
- Archived files referenced in entries actually exist
- Git entries have a commit hash
- Related references point to valid entry IDs
- No orphaned assets

If validation finds issues, the scribe will tell you and help fix them.

## Tips

- **Log at natural breakpoints** — When you solve something, hit a dead end, or stop for the day
- **Let the scribe propose first** — It captures context you might forget to mention
- **Use "dead end" annotations** — Failed approaches are valuable to record
- **Snapshot before risky changes** — Easy to compare or revert
- **Ask questions when returning** — "Where did we leave off?" gets you back up to speed
- **Use git entries for milestones** — When you want a proper commit, not just a log

## Limitations

- **Single session** — Not designed for multiple Claude sessions writing simultaneously
- **Project scale** — Best for weeks-to-months of work, not permanent archives
- **Plain text** — Logs are markdown; no database, no sync, no cloud
- **Latest entry only** — Edit commands only work on the most recent entry
- **Git required for git features** — If not in a git repo, git state tracking is unavailable

## Files

The skill consists of:

| File | Purpose |
|------|---------|
| `SKILL.md` | Instructions for Claude |
| `references/*.md` | Detailed examples and edge cases |
| `scripts/entry.py` | Prepares, finalizes, and edits log entries |
| `scripts/assets.py` | Archives and restores file snapshots |
| `scripts/validate.py` | Checks log consistency |
| `scripts/git_state.py` | Captures commit hash |
| `scripts/git_entry.py` | Creates git commits with entry as message |
| `scripts/common.py` | Shared utilities |
| `scripts/pyproject.toml` | Python dependencies (pyyaml) |

You don't need to run these scripts directly — Claude handles that. But they're plain Python if you want to inspect or modify them.
