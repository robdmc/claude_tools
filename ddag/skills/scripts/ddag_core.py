"""ddag_core.py — Create and manage .ddag node files (SQLite databases)."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS script_info (
    id            INTEGER NOT NULL DEFAULT 1 CHECK (id = 1) PRIMARY KEY,
    description   TEXT,
    is_active     INTEGER NOT NULL DEFAULT 1,
    branched_from TEXT,
    force_stale   INTEGER NOT NULL DEFAULT 0
);
INSERT OR IGNORE INTO script_info (id) VALUES (1);

CREATE TABLE IF NOT EXISTS sources (
    path TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS parameters (
    name          TEXT NOT NULL PRIMARY KEY,
    type          TEXT DEFAULT 'str',
    default_value TEXT,
    current_value TEXT,
    description   TEXT
);

CREATE TABLE IF NOT EXISTS transform_function (
    id            INTEGER NOT NULL DEFAULT 1 CHECK (id = 1) PRIMARY KEY,
    function_body TEXT,
    updated_at    TEXT
);
INSERT OR IGNORE INTO transform_function (id) VALUES (1);

CREATE TABLE IF NOT EXISTS outputs (
    path        TEXT NOT NULL PRIMARY KEY,
    description TEXT,
    row_count   INTEGER,
    col_count   INTEGER,
    built_at    TEXT
);

CREATE TABLE IF NOT EXISTS output_columns (
    output_path TEXT NOT NULL REFERENCES outputs(path),
    name        TEXT NOT NULL,
    description TEXT,
    PRIMARY KEY (output_path, name)
);
"""


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def connect(ddag_path):
    """Open a .ddag file, creating and initializing if needed."""
    path = Path(ddag_path)
    db = sqlite3.connect(str(path))
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA_SQL)
    _migrate(db)
    return db


def _migrate(db):
    """Add columns introduced after initial schema. Currently a no-op — all columns are in SCHEMA_SQL."""
    pass


def create_source_node(ddag_path, description, output_paths):
    """Create a source node (no transform function)."""
    db = connect(ddag_path)
    try:
        with db:
            db.execute("UPDATE script_info SET description = ? WHERE id = 1", (description,))
            for p in output_paths:
                db.execute(
                    "INSERT INTO outputs (path) VALUES (?) ON CONFLICT(path) DO NOTHING",
                    (p,),
                )
    finally:
        db.close()


def create_compute_node(ddag_path, description, source_paths, output_paths, function_body, params=None):
    """Create a compute node with a transform function.

    Safe for re-creation: preserves existing output/column descriptions and stats.
    """
    db = connect(ddag_path)
    try:
        with db:
            db.execute("UPDATE script_info SET description = ? WHERE id = 1", (description,))
            for p in source_paths:
                db.execute(
                    "INSERT INTO sources (path) VALUES (?) ON CONFLICT(path) DO NOTHING",
                    (p,),
                )
            for p in output_paths:
                db.execute(
                    "INSERT INTO outputs (path) VALUES (?) ON CONFLICT(path) DO NOTHING",
                    (p,),
                )
            db.execute(
                "UPDATE transform_function SET function_body = ?, updated_at = ? WHERE id = 1",
                (function_body, _now_iso()),
            )
            if params:
                for name, info in params.items():
                    db.execute(
                        "INSERT INTO parameters (name, type, default_value, current_value, description) "
                        "VALUES (?, ?, ?, ?, ?) "
                        "ON CONFLICT(name) DO UPDATE SET type=excluded.type, "
                        "default_value=excluded.default_value, current_value=excluded.current_value, "
                        "description=excluded.description",
                        (name, info.get("type", "str"), info.get("default"), info.get("value"), info.get("description")),
                    )
    finally:
        db.close()


def read_node(ddag_path):
    """Read all metadata from a .ddag file. Returns a dict."""
    db = connect(ddag_path)
    info = dict(db.execute("SELECT * FROM script_info WHERE id = 1").fetchone())
    sources = [row["path"] for row in db.execute("SELECT path FROM sources").fetchall()]
    params = [dict(row) for row in db.execute("SELECT * FROM parameters").fetchall()]
    tf = dict(db.execute("SELECT * FROM transform_function WHERE id = 1").fetchone())
    outputs = [dict(row) for row in db.execute("SELECT * FROM outputs").fetchall()]
    columns = {}
    for row in db.execute("SELECT * FROM output_columns").fetchall():
        columns.setdefault(row["output_path"], []).append(
            {"name": row["name"], "description": row["description"]}
        )
    db.close()
    return {
        "description": info["description"],
        "is_active": bool(info["is_active"]),
        "branched_from": info["branched_from"],
        "force_stale": bool(info["force_stale"]),
        "sources": sources,
        "parameters": params,
        "transform_function": tf["function_body"],
        "updated_at": tf["updated_at"],
        "outputs": outputs,
        "output_columns": columns,
        "is_source_node": tf["function_body"] is None,
    }


def set_function(ddag_path, function_body):
    """Update the transform function."""
    db = connect(ddag_path)
    try:
        with db:
            db.execute(
                "UPDATE transform_function SET function_body = ?, updated_at = ? WHERE id = 1",
                (function_body, _now_iso()),
            )
    finally:
        db.close()


def dump_function(ddag_path, output_path=None):
    """Dump the transform function to a .py file for external editing.

    Returns the output file path.
    """
    db = connect(ddag_path)
    try:
        row = db.execute("SELECT function_body FROM transform_function WHERE id = 1").fetchone()
    finally:
        db.close()
    body = row["function_body"]
    if body is None:
        raise ValueError(f"{ddag_path} is a source node (no transform function)")
    if output_path is None:
        stem = Path(ddag_path).stem
        output_path = f"_ddag_{stem}.py"
    Path(output_path).write_text(body + "\n")
    return output_path


def load_function(ddag_path, input_path=None):
    """Load a transform function from a .py file back into the node."""
    if input_path is None:
        stem = Path(ddag_path).stem
        input_path = f"_ddag_{stem}.py"
    body = Path(input_path).read_text().rstrip("\n")
    set_function(ddag_path, body)
    return input_path


def update_output_stats(ddag_path, output_path, row_count, col_count):
    """Update output stats after a build."""
    db = connect(ddag_path)
    try:
        with db:
            db.execute(
                "UPDATE outputs SET row_count = ?, col_count = ?, built_at = ? WHERE path = ?",
                (row_count, col_count, _now_iso(), output_path),
            )
    finally:
        db.close()


def set_output_description(ddag_path, output_path, description):
    """Set description for an output file."""
    db = connect(ddag_path)
    try:
        with db:
            db.execute("UPDATE outputs SET description = ? WHERE path = ?", (description, output_path))
    finally:
        db.close()


def set_column_descriptions(ddag_path, output_path, col_descriptions):
    """Upsert column descriptions for an output file. col_descriptions: {name: description}.

    Merges with existing descriptions — only the keys present in col_descriptions
    are inserted or updated. Existing columns not in col_descriptions are left unchanged.
    """
    db = connect(ddag_path)
    try:
        with db:
            for name, desc in col_descriptions.items():
                db.execute(
                    "INSERT INTO output_columns (output_path, name, description) VALUES (?, ?, ?)"
                    " ON CONFLICT(output_path, name) DO UPDATE SET description = excluded.description",
                    (output_path, name, desc),
                )
    finally:
        db.close()


def remove_source(ddag_path, source_path):
    """Remove a source path from a node."""
    db = connect(ddag_path)
    try:
        with db:
            db.execute("DELETE FROM sources WHERE path = ?", (source_path,))
    finally:
        db.close()


def remove_output(ddag_path, output_path):
    """Remove an output path and its column descriptions from a node."""
    db = connect(ddag_path)
    try:
        with db:
            db.execute("DELETE FROM output_columns WHERE output_path = ?", (output_path,))
            db.execute("DELETE FROM outputs WHERE path = ?", (output_path,))
    finally:
        db.close()


def get_sources_dict(ddag_path):
    """Return sources as {basename_without_ext: path} for use in transform calls."""
    db = connect(ddag_path)
    try:
        rows = db.execute("SELECT path FROM sources").fetchall()
    finally:
        db.close()
    result = {}
    for row in rows:
        p = Path(row["path"])
        key = p.stem
        # Handle duplicates by appending parent dir
        if key in result:
            key = f"{p.parent.name}_{p.stem}"
        result[key] = row["path"]
    return result


def get_outputs_dict(ddag_path):
    """Return outputs as {basename_without_ext: path} for use in transform calls."""
    db = connect(ddag_path)
    try:
        rows = db.execute("SELECT path FROM outputs").fetchall()
    finally:
        db.close()
    result = {}
    for row in rows:
        p = Path(row["path"])
        key = p.stem
        if key in result:
            key = f"{p.parent.name}_{p.stem}"
        result[key] = row["path"]
    return result


def get_params_dict(ddag_path):
    """Return parameters as {name: value} with type coercion."""
    db = connect(ddag_path)
    try:
        rows = db.execute("SELECT name, type, default_value, current_value FROM parameters").fetchall()
    finally:
        db.close()
    coerce = {"str": str, "int": int, "float": float, "bool": lambda v: v.lower() in ("true", "1", "yes")}
    result = {}
    for row in rows:
        raw = row["current_value"] if row["current_value"] is not None else row["default_value"]
        if raw is not None:
            fn = coerce.get(row["type"], str)
            result[row["name"]] = fn(raw)
        else:
            result[row["name"]] = None
    return result


def clone_node(src_path, dest_path):
    """Clone a node to a new file. Sets branched_from on the clone."""
    import shutil
    shutil.copy2(src_path, dest_path)
    db = connect(dest_path)
    try:
        with db:
            db.execute(
                "UPDATE script_info SET branched_from = ? WHERE id = 1",
                (str(src_path),),
            )
    finally:
        db.close()


def deactivate_node(ddag_path):
    """Mark a node as inactive (excluded from DAG)."""
    db = connect(ddag_path)
    try:
        with db:
            db.execute("UPDATE script_info SET is_active = 0 WHERE id = 1")
    finally:
        db.close()


def activate_node(ddag_path):
    """Mark a node as active (included in DAG)."""
    db = connect(ddag_path)
    try:
        with db:
            db.execute("UPDATE script_info SET is_active = 1 WHERE id = 1")
    finally:
        db.close()


def is_active(ddag_path):
    """Check if a node is active."""
    db = connect(ddag_path)
    try:
        row = db.execute("SELECT is_active FROM script_info WHERE id = 1").fetchone()
        return bool(row["is_active"])
    finally:
        db.close()


def set_force_stale(ddag_path):
    """Mark a node as force-stale (will be rebuilt on next build regardless of timestamps)."""
    db = connect(ddag_path)
    try:
        with db:
            db.execute("UPDATE script_info SET force_stale = 1 WHERE id = 1")
    finally:
        db.close()


def clear_force_stale(ddag_path):
    """Clear the force-stale flag on a node."""
    db = connect(ddag_path)
    try:
        with db:
            db.execute("UPDATE script_info SET force_stale = 0 WHERE id = 1")
    finally:
        db.close()
