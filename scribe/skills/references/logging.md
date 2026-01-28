# Logging Reference

Detailed examples and formats for the logging mode.

## Example Interaction

> **User:** scribe, log this
>
> **Claude:** Here's what I'll log:
>
> ---
> **14:35 — Fixed null handling in ETL pipeline**
>
> Found that nulls originated from the 2019 migration. Updated `etl.py` to coalesce nulls to zero for pre-2019 records. Validated on test dataset.
>
> **Files touched:** `etl.py`, `exploration.ipynb`
>
> ---
>
> **Archive these files?** (optional)
> - [ ] `etl.py`
> - [ ] `exploration.ipynb`
>
> Let me know if this looks right, or any changes.

Then the user might say:
- "looks good" → Claude captures git state and writes the entry
- "also snapshot etl.py" → Claude writes entry + archives the file
- "no, the issue was timezone handling not nulls" → Claude revises and re-proposes

## Entry Format (Input)

Provide the title without a timestamp — the script adds the current time automatically.

(Legacy format `## HH:MM — Title` is also accepted; the script will use the provided time instead of current time.)

```markdown
## [Brief title]

[Narrative paragraph describing what happened]

**Files touched:** (if applicable)
- `path/to/file.py` — Added retry logic; increased timeout to 30s
- `config.yaml` — Bumped max_retries from 3 to 5

---
```

## Entry Format (Output)

The script adds YAML frontmatter with metadata:

```markdown
---
id: 2026-01-23-14-35
timestamp: "14:35"
title: Fixed null handling in ETL pipeline
git: abc1234
diff: diffs/2026-01-23-14-35.diff
---
## 14:35 — Fixed null handling in ETL pipeline

[Narrative content...]

**Files touched:**
- `etl.py` — Added coalesce logic

---
```

## Writing the Entry

Use Claude's Write tool to create a temp file, then pass it to `entry.py`:

**Step 1:** Capture git state:

```bash
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ git_state.py hash
# Output: abc1234

uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ entry.py new-id
# Output: 2026-01-23-14-35

uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ git_state.py save-diff 2026-01-23-14-35
# Output: Saved: diffs/2026-01-23-14-35.diff
#         2 file(s), +15/-3 lines
```

**Step 2:** Use the Write tool to create `/tmp/scribe_entry_${CLAUDE_SESSION_ID}.md`:

```markdown
## Fixed null handling in ETL pipeline

Found that nulls originated from the 2019 migration.

**Files touched:**
- `etl.py` — Added coalesce logic

---
```

**Step 3:** Run the script with git flags:

```bash
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ entry.py write \
  --file /tmp/scribe_entry_${CLAUDE_SESSION_ID}.md \
  --git abc1234 \
  --git-diff
```

Output: `Entry written: 2026-01-23-14-35`

The script automatically:
- Gets the current system time (24-hour local time)
- Prepends the timestamp to the title (`## Title` → `## HH:MM — Title`)
- Generates the entry ID from the date + time
- Handles collisions (adds `-02`, `-03` suffix if needed)
- Builds YAML frontmatter with id, timestamp, title, git hash, and diff path
- Creates today's log file if it doesn't exist
- Appends the entry
- Validates the entry (unless `--no-validate` is passed)

## Git Entry Example

When the user explicitly requests a git entry:

> **User:** scribe, git entry — this fixes the ETL bug

**Step 1:** Show what will be committed:

```bash
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ git_entry.py status
# Output: Modified tracked files (3):
#           etl.py
#           tests/test_etl.py
#           config.yaml
```

**Step 2:** Propose entry and wait for confirmation.

**Step 3:** Create temp file with frontmatter for commit message:

```markdown
---
id: 2026-01-23-14-35
timestamp: "14:35"
title: Fixed null handling in ETL pipeline
---
## 14:35 — Fixed null handling in ETL pipeline

Found that nulls originated from the 2019 migration.

**Files touched:**
- `etl.py` — Added coalesce logic

---
```

**Step 4:** Create commit:

```bash
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ git_entry.py commit \
  --file /tmp/scribe_entry_${CLAUDE_SESSION_ID}.md
# Output: Created commit: def5678
#         [main def5678] Fixed null handling in ETL pipeline
#          3 files changed, 25 insertions(+), 8 deletions(-)
```

**Step 5:** Write scribe entry:

```bash
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ entry.py write \
  --file /tmp/scribe_entry_${CLAUDE_SESSION_ID}.md \
  --git def5678 \
  --git-mode git-entry
```

## What to Capture

- The question, problem, or goal being worked on
- Approaches tried
- What worked, what failed, and why
- Files created or modified, with brief descriptions of changes
- Key discoveries, surprises, or turning points

## User Annotations

The user may add context: `scribe — this was a dead end`. Incorporate their editorial judgment.

## After Writing

Display a brief summary so the user can verify:

> Logged:
>
> **14:35 — [Title]**
>
> [First sentence or two of the narrative]
>
> *Files touched: `file1.py`, `file2.py`*
>
> *Git: abc1234 | Diff saved*
