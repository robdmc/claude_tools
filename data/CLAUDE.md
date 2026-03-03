# Data Skill Development Guide

Instructions for Claude sessions working on this skill.

## Before Making Changes

1. **Read the current skill files** to understand the existing structure:
   - `skills/SKILL.md` - Main skill definition (Claude reads this)
   - `skills/scripts/probe.py` - File structure probing utility
   - `skills/scripts/pyproject.toml` - Bundled uv environment deps
   - `skills/prompts/` - Marimo notebook prompts (copied to user projects)

## Skill Architecture

```
data/
├── README.md              # Human documentation
├── CLAUDE.md              # This file - development instructions
└── skills/
    ├── SKILL.md           # Skill definition for Claude
    ├── scripts/
    │   ├── pyproject.toml # Bundled uv environment deps
    │   └── probe.py       # CSV/Parquet structural prober
    └── prompts/
        ├── marimo.md          # Marimo notebook assistant prompt
        ├── marimo-check.md    # Marimo check instructions
        └── viz-preferences.md # Viz preferences for marimo notebooks
```

## Key Design Decisions

These decisions were made intentionally - preserve them unless explicitly changing:

- **No visualization**: The data skill never generates charts, plots, or images. It delegates to the viz skill by preparing `.viz/<name>.parquet` files.
- **Polars by default**: Use polars as the default library unless there's a specific reason to use pandas or duckdb.
- **Probe before load**: For unfamiliar CSV files, always probe first to understand structure before attempting to load.
- **Marimo for exploration**: When users want interactive exploration, create marimo notebooks rather than printing large DataFrames.
- **Separate prompts directory**: Marimo-related prompts are copied into user projects (`.claude/prompts/`) so they persist across sessions.
- **`{SKILL_DIR}` for execution**: All Python is run via `uv run --project {SKILL_DIR}` to use the bundled dependencies, never the caller's environment.

## Making Changes

### SKILL.md changes

Keep it focused on what Claude needs to know: execution patterns, library selection, output conventions, and the marimo workflow. Move detailed examples into reference files if SKILL.md grows too large.

### probe.py changes

The prober should remain a standalone script with no imports beyond the standard library (for CSV probing) and polars (for structured formats). It prints a compact summary to stdout.

### Dependency changes

Edit `skills/scripts/pyproject.toml`. The environment should contain data analysis libraries only. Resist adding visualization libraries beyond what marimo notebooks need (hvplot, holoviews, seaborn, matplotlib are there for marimo use).

### Prompt changes

Prompts in `skills/prompts/` are copied into user projects. Changes here affect new copies only, not existing user installations.

## Testing Changes

No dedicated test suite. Test by running an end-to-end analysis:

1. Probe a CSV file: `uv run --project skills/scripts python skills/scripts/probe.py <file>`
2. Run a polars analysis: `uv run --project skills/scripts python -c "import polars as pl; ..."`
3. Test marimo notebook creation and validation

## Integration Points

- **Viz skill**: Data skill preps `.viz/<name>.parquet` files; viz skill renders them.
- **Marimo prompts**: Copied to `.claude/prompts/` in user projects for persistent notebook editing context.
- **gsheet tool**: Can provide data as Parquet files that the data skill then analyzes.
