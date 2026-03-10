# ddag — Development Guide

Instructions for Claude sessions working on this skill.

## Before Making Changes

1. **Read the current skill files** to understand the existing structure:
   - `skills/SKILL.md` — Main skill definition (Claude reads this)
   - `skills/scripts/ddag_core.py` — Node CRUD: create/read/update .ddag files
   - `skills/scripts/ddag_build.py` — DAG assembly, cycle detection, staleness, build script generation
   - `skills/references/` — Detailed API, CLI, schema, and workflow docs

## Skill Architecture

```
ddag/
├── README.md              # Human documentation
├── CLAUDE.md              # This file — development instructions
├── skills/
│   ├── SKILL.md           # Skill definition for Claude
│   ├── references/
│   │   ├── api.md         # Python API reference with examples
│   │   ├── cli.md         # CLI command reference
│   │   ├── schema.md      # SQLite schema (6 tables)
│   │   └── workflows.md   # Advanced workflows (branching, script conversion, audit)
│   └── scripts/
│       ├── ddag_core.py   # Node CRUD operations
│       └── ddag_build.py  # DAG-wide operations and CLI entrypoint
└── tests/
    └── test_ddag.py       # Test battery (28 tests)
```

## Key Design Decisions

These decisions were made intentionally — preserve them unless explicitly changing:

- **Primary customer is Claude Code** — SKILL.md teaches Claude how to create/manage nodes
- **No CLI framework** — helper scripts called directly via `python skills/scripts/ddag_core.py` or imported
- **SQLite per node** — each .ddag file is a self-contained SQLite DB with 6 tables (script_info, sources, parameters, transform_function, outputs, output_columns)
- **Source vs compute nodes** — source nodes have NULL function_body, compute nodes have a Python function
- **DAG edges discovered automatically** — by matching source paths to output paths across all .ddag files
- **Makefile-like staleness** — compare timestamps to determine what needs rebuilding
- **Transform functions use `def transform(sources, params, outputs)`** signature with imports inside the function
- **`{SKILL_DIR}` for execution** — scripts are invoked relative to the skill directory, not the caller's environment

## Making Changes

### SKILL.md changes

Keep it focused on what Claude needs to know: invocation patterns, checkpoints, creation workflows, and modification patterns. Move detailed examples into reference files if SKILL.md grows too large.

### Script changes

- Keep scripts small and focused — `ddag_core.py` handles SQLite CRUD, `ddag_build.py` handles DAG logic
- All file paths in .ddag files are **relative to the project root**
- The .ddag file never contains data — only metadata and function definitions
- When modifying the schema, update `skills/references/schema.md`, the `SCHEMA_SQL` in `skills/scripts/ddag_core.py`, and relevant tests

### Reference changes

Reference files are loaded into context on demand. Keep them accurate and in sync with the scripts.

## Testing

```bash
python ddag/tests/test_ddag.py
```

All tests run in a temp directory and clean up after themselves. Tests cover: node creation, DAG assembly, staleness detection, build execution, cycle detection, metadata descriptions, branching, conflict detection, force-stale propagation, sourceless compute nodes, dump/load round-trips, and build script parsing.

After any script changes, run the full test battery to verify.

## Integration Points

- **Data skill**: ddag nodes can wrap data files that the data skill analyzes
- **Viz skill**: ddag pipeline outputs (Parquet files) can be handed off for visualization
