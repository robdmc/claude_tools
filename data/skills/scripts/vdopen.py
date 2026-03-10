#!/usr/bin/env python3
"""Open data files in VisiData in a new iTerm2 window.

Usage:
    vdopen.py <filepath>                  # flat files (CSV, Parquet, JSON, etc.)
    vdopen.py <dbfile> <table_name>       # DuckDB: view a specific table
    vdopen.py --list-tables <dbfile>      # DuckDB: list available tables
"""

import os
import subprocess
import sys

DUCKDB_EXTENSIONS = {".ddb", ".duckdb"}


def resolve_path(path: str) -> str:
    return os.path.abspath(path)


def open_in_iterm(command: str, cwd: str) -> None:
    script = f'''
tell application "iTerm2"
    activate
    create window with default profile command "bash -lc 'cd \\"{cwd}\\" && {command}'"
end tell
'''
    subprocess.run(
        ["osascript", "-e", script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def list_tables(dbfile: str) -> list[str]:
    import duckdb

    con = duckdb.connect(dbfile, read_only=True)
    rows = con.execute(
        "SELECT table_schema || '.' || table_name "
        "FROM information_schema.tables "
        "WHERE table_type = 'BASE TABLE' "
        "ORDER BY table_schema, table_name"
    ).fetchall()
    con.close()
    return [row[0] for row in rows]


def main() -> None:
    if len(sys.argv) < 2:
        print((__doc__ or "").strip(), file=sys.stderr)
        sys.exit(1)

    cwd = os.getcwd()

    # --list-tables mode
    if sys.argv[1] == "--list-tables":
        if len(sys.argv) < 3:
            print("Error: --list-tables requires a database file", file=sys.stderr)
            sys.exit(1)
        dbfile = resolve_path(sys.argv[2])
        for table in list_tables(dbfile):
            print(table)
        return

    filepath = resolve_path(sys.argv[1])
    ext = os.path.splitext(filepath)[1].lower()

    # DuckDB file
    if ext in DUCKDB_EXTENSIONS:
        if len(sys.argv) < 3:
            print("Error: DuckDB files require a table name. Use --list-tables first.", file=sys.stderr)
            sys.exit(1)
        table = sys.argv[2]
        cmd = f'duckdb -csv \\"{filepath}\\" \\"SELECT * FROM {table}\\" | vd -f csv'
        open_in_iterm(cmd, cwd)
        return

    # Flat files
    open_in_iterm(f'vd \\"{filepath}\\"', cwd)


if __name__ == "__main__":
    main()
