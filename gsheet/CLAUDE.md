# GSheet Skill Development Guide

Instructions for Claude sessions working on this skill.

## Before Making Changes

1. **Read the current skill files** to understand the existing structure:
   - `skills/SKILL.md` - Main skill definition (Claude reads this)
   - `skills/scripts/gsheet.py` - Google Sheets download script
   - `skills/scripts/pyproject.toml` - Bundled uv environment deps
   - `skills/scripts/credentials.json` - Google OAuth client credentials (not in git)

## Skill Architecture

```
gsheet/
├── README.md              # Human documentation
├── CLAUDE.md              # This file - development instructions
└── skills/
    ├── SKILL.md           # Skill definition for Claude
    └── scripts/
        ├── .gitignore     # Ignores .venv, __pycache__, token.json
        ├── credentials.json # Google OAuth client credentials (not in git)
        ├── gsheet.py      # Main download script
        ├── pyproject.toml # Bundled uv environment deps
        └── uv.lock        # Locked dependencies
```

## Key Design Decisions

- **Interactive tab selection**: The skill always lists tabs first, then asks the user which to download. This prevents accidentally downloading dozens of tabs from large spreadsheets.
- **Cross-skill integration**: The clean/probe step uses the `data` skill's probe.py and uv environment. This is intentional — the data skill owns data cleaning capabilities.
- **OAuth credentials**: `credentials.json` is the Google Cloud OAuth client config. It ships with the skill but is gitignored. Users who clone fresh need to provide their own.
- **Token storage**: User tokens are saved to `~/.config/gsheet/token.json`, not in the skill directory. This keeps user-specific auth separate from the skill.
- **CSV as output format**: Google Sheets data is downloaded as CSV, the simplest portable format. Parquet conversion happens only during the optional clean step.

## Making Changes

### Script changes (`gsheet.py`)

The script is straightforward: authenticate, call the Sheets API, write CSVs. Key areas:
- `authenticate()` — Handles OAuth flow and token refresh
- `extract_sheet_id()` — Parses URLs or raw IDs
- `tab_to_filename()` — Slugifies tab names for filenames
- `download_tabs()` — Core download logic

### SKILL.md changes

The SKILL.md defines the interactive workflow (list → ask → download → probe → clean). Changes to the workflow steps should be reflected in both SKILL.md and this CLAUDE.md.

### Dependencies

The uv environment should only contain Google API libraries. Resist adding data processing libraries — that's the data skill's domain.

## Testing Changes

Test by running the full workflow against a real Google Sheet:

1. List tabs: `uv run --project skills/scripts python skills/scripts/gsheet.py --list "<SHEET_URL>"`
2. Download a tab: `uv run --project skills/scripts python skills/scripts/gsheet.py "<SHEET_URL>" -o /tmp/test -t "Sheet1"`
3. Verify the CSV output is correct

## Integration Points

- **Invocation**: The skill is invoked when users ask to download, fetch, or get data from Google Sheets.
- **Data skill**: The probe/clean workflow depends on the data skill being installed (`~/.claude/skills/data`).
- **Credential path**: `gsheet.py` resolves `credentials.json` relative to its own directory (`SCRIPT_DIR`).
