# Recovery Reference

Commands for handling interruptions, fixing mistakes, and editing entries.

## Pending Entry Commands

If an entry is interrupted (prepare ran but finalize didn't):

```bash
# Check if there's a pending entry
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/entry.py status

# Output shows:
# Pending entry: 2026-01-23-14-35
# Staging file: __2026-01-23-14-35__.md
# Title filled: no
# Body filled: no
# Mode: git-entry
# Archives: 2 file(s)

# Abort and discard the pending entry
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/entry.py abort
```

The daily log is never touched until finalize succeeds, so aborting is always safe.

## Edit Latest Entry Commands

If something goes wrong with a finalized entry, use `edit-latest`:

```bash
# Display the latest entry
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/entry.py edit-latest show

# Remove latest entry AND its assets
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/entry.py edit-latest delete

# Replace latest entry with new content
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/entry.py edit-latest replace --file .scribe/draft.md

# Re-archive a different file for latest entry
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/entry.py edit-latest rearchive correct_file.py

# Delete assets for latest entry (keep the entry text)
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/entry.py edit-latest unarchive
```

## Common Recovery Flows

### Interrupted Entry (Prepare but No Finalize)

```bash
# Check status
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/entry.py status

# If you want to continue: use Edit to fill in __TITLE__ and __BODY__, then finalize
# If you want to discard:
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/entry.py abort
```

### Finalize Failed (Placeholders Not Replaced)

The finalize command will error if `__TITLE__` or `__BODY__` are still present:

```
Error: Title placeholder (__TITLE__) not replaced
```

Fix by using Edit to replace the placeholders, then run finalize again.

### Wrong File Archived

```bash
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/entry.py edit-latest rearchive correct_file.py
```

### Fix Entry Content

1. Create corrected entry in a temp file
2. Run: `uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/entry.py edit-latest replace --file .scribe/draft.md`

### Remove Archives but Keep Entry

1. `uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/entry.py edit-latest unarchive`
2. Then replace the entry to remove the **Archived** section

## Validation

Run validation to check for issues:

```bash
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/validate.py
```

Validation checks:
- Every entry has an ID
- Entry ID format is valid
- Archived files referenced in entries actually exist
- Related references point to valid entry IDs
- No orphaned assets (files in `assets/` not referenced by any entry)

If validation fails, fix the issue before continuing. Use `edit-latest` commands to fix or remove broken entries.

## Other Entry Commands

```bash
# Show last entry ID from today's log only
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/entry.py last

# Include title (useful for Related links)
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/entry.py last --with-title
```
