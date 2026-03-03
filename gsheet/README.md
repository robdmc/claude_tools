# GSheet

Download data from Google Sheets as CSV files. Lists tabs, lets the user pick which ones to download, and optionally cleans messy data into analysis-ready parquet files.

## How It Works

1. **List tabs** — Shows all tabs in a spreadsheet with their CSV filenames
2. **Select tabs** — User picks which tabs to download (or all)
3. **Download** — Saves each tab as a CSV file
4. **Clean (optional)** — Probes CSVs for messiness and offers to clean into parquet

## Usage

```bash
# List tabs in a spreadsheet
uv run --project <scripts_dir> python <scripts_dir>/gsheet.py --list "<SHEET_URL_OR_ID>"

# Download all tabs
uv run --project <scripts_dir> python <scripts_dir>/gsheet.py "<SHEET_URL_OR_ID>" -o <OUTPUT_DIR>

# Download specific tabs
uv run --project <scripts_dir> python <scripts_dir>/gsheet.py "<SHEET_URL_OR_ID>" -o <OUTPUT_DIR> -t "Tab1" -t "Tab2"
```

## First Run / Setup

### Google Cloud Credentials

The script requires a `credentials.json` file in the `skills/scripts/` directory. To obtain one:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or use an existing one)
3. Enable the **Google Sheets API**
4. Create OAuth 2.0 credentials (Desktop application type)
5. Download the JSON and save it as `skills/scripts/credentials.json`

### OAuth Login

On first run, the script opens a browser for Google OAuth login. Grant read-only access to your sheets. A token is saved to `~/.config/gsheet/token.json` for future runs.

## Dependencies

Managed by `uv` via `pyproject.toml`. No manual install needed.

- google-auth-oauthlib
- google-api-python-client

## Installation

Use the `/install` command from the claude_tools repository:

```
/install
```
