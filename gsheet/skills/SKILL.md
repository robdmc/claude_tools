---
name: gsheet
description: >
  Download data from Google Sheets as CSV files with interactive tab selection and optional data cleaning.
  Use when user asks to download, fetch, pull, or get data from a Google Sheet or Google Spreadsheet,
  or when a workflow requires importing Google Sheets data locally.
allowed-tools: >
  Bash(uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/gsheet.py *),
  Bash
---

## Workflow

Always follow this interactive flow:

### Step 1: List tabs

```bash
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/gsheet.py --list "<SHEET_URL_OR_ID>"
```

This returns JSON with the spreadsheet name, tab names, and the CSV filenames that will be created. Note: first run opens a browser for Google OAuth — the user grants read-only access and a token is saved for future runs.

### Step 2: Ask the user

**If 4 or fewer tabs:** Use AskUserQuestion with `multiSelect: true` to present a checklist of all tabs. Each tab should be an option with its name as the label and its CSV filename as the description.

**If more than 4 tabs:** Print the numbered tab list to the user, then use AskUserQuestion with a single free-text question: "Which tabs? (enter comma-separated names, or 'all')". Do not use the multi-select checklist.

If the user selects all tabs, omit `-t` flags in the download command. Otherwise, pass only the selected tabs with `-t` flags.

### Step 3: Download

```bash
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/gsheet.py "<SHEET_URL_OR_ID>" -o <OUTPUT_DIR> -t "tab1" -t "tab2"
```

Omit `-t` flags to download all tabs. Use `-t` once per tab to download specific tabs.

### Step 4: Probe & offer to clean

Requires the `data` skill installed at `~/.claude/skills/data`. Skip this step if unavailable.

After downloading, probe each CSV to check if it's messy:

```bash
uv run --project ~/.claude/skills/data python ~/.claude/skills/data/probe.py <file.csv>
```

Show the probe summary to the user. If the probe reveals messiness (skip rows, multiple column groups, formatted numbers like `$`, `,`, `%`), ask: **"Want me to clean this into an analysis-ready parquet file?"**

**If yes:** Use the probe output to write a polars cleaning script, run it via the data skill's uv env:

```bash
uv run --project ~/.claude/skills/data python /tmp/clean_sheet.py
```

The cleaning script should:
1. Skip header/section rows (use `skip_rows` from probe)
2. Select the relevant columns — if multiple column groups exist, ask the user which group(s) they want
3. Strip `$`, `,`, `%` from values and cast to numeric
4. Save as `<name>.parquet` alongside the raw CSV

**If no:** Leave the raw CSV as-is.

