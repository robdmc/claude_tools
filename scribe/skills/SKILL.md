---
name: scribe
description: Maintains a narrative log of exploratory work with file archives and git state tracking. Capabilities: (1) Log entries with propose-confirm flow, (2) Archive files linked to entries, (3) Capture git state (commit hash + diff), (4) Create git commits with entry as message, (5) Restore archived files, (6) Query past work by time or topic, (7) Link related entries for thread tracking. Activates when user addresses "scribe" directly (e.g., "hey scribe, log this", "scribe, save this notebook", "scribe, what did we try yesterday?") or uses `/scribe` commands.
disable-model-invocation: true
allowed-tools: Read, Write, Glob, Grep, Bash(uv run --project * python *), Bash(mkdir *), Bash(rm -f *), Bash(git status*), Bash(git diff --no-ext-diff*), Bash(git rev-parse*), Bash(git add*), Bash(git commit*)
argument-hint: [log | git entry | save <file> | restore <asset> | ask <question>]
---

# Scribe

The scribe maintains a narrative log of your exploratory work, can archive important files, and tracks git state.

**Address naturally:** "hey scribe, log this" / "scribe, save this notebook" / "scribe, what did we try yesterday?"

**Or use commands:** `/scribe` / `/scribe save file.py` / `/scribe ask what happened last week?`

## Quick Reference

| Mode | Trigger | Action |
|------|---------|--------|
| Log | "scribe, log this" | Propose entry → confirm → capture git state → write |
| Quick log | "scribe, quick log: fixed bug" | Propose entry → confirm → capture git state → write |
| Git entry | "scribe, git entry" / "commit this with git" | Propose entry → confirm → create git commit → write |
| Archive | "scribe, save notebook.ipynb" | Log + archive file |
| Restore | "scribe, restore the ETL script" | Copy from assets |
| Query | "scribe, what did we try?" | Search and summarize |

**Important:** Git entries ONLY happen when user explicitly says "git" (e.g., "git entry", "commit with git", "scribe git log"). Never auto-promote to git entry.

## Directory Structure

```
.scribe/
├── 2026-01-23.md      # Daily log files
├── assets/            # Archived files
│   └── 2026-01-23-14-35-notebook.ipynb
└── diffs/             # Git diffs per entry
    └── 2026-01-23-14-35.diff
```

## Scripts

Scripts in `{SKILL_DIR}/scripts/`. Resolve `{SKILL_DIR}` to the directory containing this SKILL.md file.

**Run scripts with uv:** `uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/<script.py> <args>`

| Script | Purpose |
|--------|---------|
| `entry.py write --file .scribe/draft.md` | Write entry from temp file |
| `entry.py write --file ... --git <hash> --git-diff` | Write entry with git metadata |
| `entry.py write --file ... --git <hash> --git-mode git-entry` | Write git entry |
| `entry.py new-id` | Generate entry ID for current time (handles collisions) |
| `entry.py last` | Get last entry ID from today |
| `git_state.py hash` | Get current HEAD commit hash (short) |
| `git_state.py save-diff <id>` | Save diff to `.scribe/diffs/{id}.diff` |
| `git_state.py save-diff <id> --ext "py,sql"` | Save diff with custom extensions |
| `git_entry.py status` | Show modified tracked files (preview) |
| `git_entry.py commit --file <entry.md>` | Stage modified files, commit with entry as message |
| `assets.py save <id> <file>` | Archive a file |
| `assets.py list [filter]` | List archived files |
| `assets.py get <asset> --dest <dir>` | Restore a file |
| `validate.py` | Check for errors |

**Python 3.9+ required.**

## Entry Format

Entries use YAML frontmatter for metadata:

```markdown
---
id: 2026-01-23-14-35
timestamp: "14:35"
title: Fixed null handling in ETL pipeline
git: abc1234
diff: diffs/2026-01-23-14-35.diff
---
## 14:35 — Fixed null handling in ETL pipeline

What happened, why it was tried...

**Files touched:**
- `etl.py` — Added coalesce logic

---
```

For git entries (commit mode), no `diff` field — the commit IS the snapshot:

```markdown
---
id: 2026-01-23-14-35
timestamp: "14:35"
title: Fixed null handling in ETL pipeline
git: def5678
mode: git-entry
---
## 14:35 — Fixed null handling in ETL pipeline

What happened, why it was tried...

---
```

## Logging Flow (Regular Entries)

Follow these steps when logging:

1. **Assess** — Check conversation context, recent logs, `git status`
2. **Propose** — Draft entry, offer optional file archives
3. **Confirm** — Wait for user approval
4. **Capture git state** — Run:
   - `uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ git_state.py hash` → save the hash
   - `uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ entry.py new-id` → get entry ID
   - `uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ git_state.py save-diff <id>` → save diff
5. **Write** — Run `rm -f .scribe/draft.md`, create draft, then:
   `uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ entry.py write --file .scribe/draft.md --git <hash> --git-diff`

**Important:** Always show a preview and wait for confirmation before writing.

### Draft Format

Create the draft file at `.scribe/draft.md` (use `rm -f` first):

```markdown
## Brief title here

What happened, why, what was tried.

**Files touched:**
- `file.py` — What changed

---
```

The script adds timestamp, ID, and git metadata automatically via frontmatter.

## Git Entry Flow

**Trigger:** User must explicitly say "git" (e.g., "scribe, git entry", "log this with git", "commit this with git")

1. **Assess** — Check context, run `git status` to see modified tracked files
2. **Propose** — Draft entry with title, show which tracked files will be committed
3. **Confirm** — Wait for user approval
4. **Prepare entry file** — Create temp file with YAML frontmatter (id, timestamp, title):
   ```markdown
   ---
   id: 2026-01-23-14-35
   timestamp: "14:35"
   title: Fixed null handling in ETL pipeline
   ---
   ## 14:35 — Fixed null handling in ETL pipeline

   What happened...

   ---
   ```
5. **Commit** — `uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ git_entry.py commit --file .scribe/draft.md`
6. **Get hash** — `uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ git_state.py hash`
7. **Write** — `uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ entry.py write --file .scribe/draft.md --git <hash> --git-mode git-entry`

**Staging behavior:** Only stages modified tracked files. Untracked files are ignored.

## Diff Extensions

By default, diffs only include `.py` files. To include other extensions:
```bash
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ git_state.py save-diff <id> --ext "py,sql,ipynb"
```

## Entry IDs

Format: `YYYY-MM-DD-HH-MM` (e.g., `2026-01-23-14-35`). Collisions get `-02`, `-03` suffix.

IDs link entries to assets and diffs, and enable **Related** cross-references:
```markdown
**Related:** 2026-01-23-14-35 — Previous entry title
```

## Archiving

When archiving files, include the **Archived** section in your draft before writing. The asset filename is predictable: `{entry-id}-{filename}`.

1. Get entry ID — `uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ entry.py new-id` (handles collisions)
2. Draft entry with **Archived** section using that ID
3. Write entry — `uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ entry.py write --file .scribe/draft.md --git <hash> --git-diff`
4. Archive files — `uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ assets.py save <id> <file>`

Example **Archived** section:
```markdown
**Archived:**
- `src/notebook.ipynb` → [`2026-01-23-14-35-notebook.ipynb`](assets/2026-01-23-14-35-notebook.ipynb)
```

## Querying

- **Time-based:** Read `.scribe/YYYY-MM-DD.md` directly
- **Topic-based:** `Grep` in `.scribe/`, then Read matches
- **Assets:** `uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ assets.py list [filter]`

## Orientation (New Sessions)

1. Read today's log file
2. Run `git status` to see changes
3. Ask user what to capture

## Initialization

On first use, check if `.scribe/` exists. If not:
```bash
mkdir -p .scribe/assets .scribe/diffs
```

Then ensure `.gitignore` contains these entries (add if missing):
```
.scribe/
_20*-*
```

## Error Handling

- **No `.scribe/` directory**: Run initialization first
- **Script fails**: Show error output to user, don't retry automatically
- **Asset not found**: List available assets with `assets.py list`
- **No git repo**: `git_state.py hash` will error — git features unavailable

## Reference Files

For detailed examples and edge cases, see:
- [references/logging.md](references/logging.md) — Entry formats, examples
- [references/archiving.md](references/archiving.md) — Archive/restore details
- [references/querying.md](references/querying.md) — Query patterns
- [references/recovery.md](references/recovery.md) — Error recovery, edit commands

## Principles

- **Narrator, not stenographer** — Write prose, not dumps
- **Capture the why** — Not just what, but why it was tried
- **Stay concise** — Entries should be scannable
- **Preserve dead ends** — Failed approaches prevent repeats
- **Git state anchors context** — Commit hash precisely identifies code state
