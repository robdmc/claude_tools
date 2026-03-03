#!/usr/bin/env python3
"""Download Google Sheets data as CSV files."""

import argparse
import csv
import os
import re
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDS_PATH = os.path.join(SCRIPT_DIR, "credentials.json")
TOKEN_PATH = os.path.join(os.path.expanduser("~"), ".config", "gsheet", "token.json")


def authenticate():
    """Authenticate with Google and return credentials."""
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDS_PATH):
                print(f"Error: credentials.json not found at {CREDS_PATH}", file=sys.stderr)
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return creds


def extract_sheet_id(url_or_id):
    """Extract the spreadsheet ID from a URL or return as-is if already an ID."""
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url_or_id)
    if match:
        return match.group(1)
    return url_or_id.strip()


def tab_to_filename(tab_name):
    """Convert a tab name to a slugified CSV filename."""
    slug = tab_name.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-{2,}', '-', slug).strip('-')
    return f"{slug}.csv"


def get_spreadsheet_info(service, spreadsheet_id):
    """Get spreadsheet title and tab names."""
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    title = spreadsheet["properties"]["title"]
    tabs = [s["properties"]["title"] for s in spreadsheet["sheets"]]
    return title, tabs


def list_tabs(spreadsheet_id):
    """List tabs and their would-be filenames as JSON."""
    creds = authenticate()
    service = build("sheets", "v4", credentials=creds)
    title, tabs = get_spreadsheet_info(service, spreadsheet_id)

    import json
    info = {
        "spreadsheet": title,
        "tabs": [{"name": t, "filename": tab_to_filename(t)} for t in tabs],
    }
    print(json.dumps(info, indent=2))


def download_tabs(spreadsheet_id, output_dir, tab_names=None):
    """Download specified tabs (or all) as CSV files."""
    creds = authenticate()
    service = build("sheets", "v4", credentials=creds)
    title, all_tabs = get_spreadsheet_info(service, spreadsheet_id)

    if tab_names:
        missing = [t for t in tab_names if t not in all_tabs]
        if missing:
            print(f"Error: tabs not found: {', '.join(missing)}", file=sys.stderr)
            print(f"Available tabs: {', '.join(all_tabs)}", file=sys.stderr)
            sys.exit(1)
        tabs_to_download = tab_names
    else:
        tabs_to_download = all_tabs

    print(f"Spreadsheet: {title}")
    os.makedirs(output_dir, exist_ok=True)

    for tab in tabs_to_download:
        print(f"  Downloading tab: {tab}")

        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=tab)
            .execute()
        )
        rows = result.get("values", [])

        if not rows:
            print(f"    (empty)")
            continue

        max_cols = max(len(row) for row in rows)
        normalized = [row + [""] * (max_cols - len(row)) for row in rows]

        filepath = os.path.join(output_dir, tab_to_filename(tab))

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(normalized)

        print(f"    Saved: {filepath} ({len(rows)} rows)")

    print("Done.")


def main():
    parser = argparse.ArgumentParser(description="Download Google Sheets data as CSV")
    parser.add_argument("sheet", help="Google Sheets URL or spreadsheet ID")
    parser.add_argument("-o", "--output", default=".", help="Output directory (default: current directory)")
    parser.add_argument("-t", "--tab", action="append", default=None, help="Tab name to download (can be repeated)")
    parser.add_argument("--list", action="store_true", help="List tabs as JSON without downloading")
    args = parser.parse_args()

    spreadsheet_id = extract_sheet_id(args.sheet)

    if args.list:
        list_tabs(spreadsheet_id)
    else:
        download_tabs(spreadsheet_id, args.output, args.tab)


if __name__ == "__main__":
    main()
