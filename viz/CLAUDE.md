# Viz Skill Development Guide

Instructions for Claude sessions working on this skill.

## Before Making Changes

1. **Invoke the skill-creator skill** for guidance on skill development best practices:
   ```
   /skill-creator
   ```

2. **Read the current skill files** to understand the existing structure:
   - `skills/SKILL.md` - Main skill definition (Claude reads this)
   - `skills/references/styling.md` - Publication quality standards
   - `skills/scripts/viz_runner.py` - Thin runner script
   - `skills/scripts/pyproject.toml` - Bundled uv environment deps

## Skill Architecture

```
viz/
├── README.md              # Human documentation
├── CLAUDE.md              # This file - development instructions
└── skills/
    ├── SKILL.md           # Skill definition for Claude
    ├── references/
    │   └── styling.md     # Publication quality standards
    └── scripts/
        ├── pyproject.toml # Bundled uv environment deps
        └── viz_runner.py  # Thin runner script (~40-60 lines)
```

## Key Design Decisions

These decisions were made intentionally - preserve them unless explicitly changing:

- **Pure rendering engine**: The skill never acquires data. The caller provides `.parquet`/`.csv` files. Data preparation is the caller's responsibility, not the viz skill's.
- **No code injection**: Generated scripts are completely self-contained (imports, data load, plot, watermark, savefig, show). They must run independently without any external state.
- **Two Python environments**: The caller's environment handles data preparation; the bundled uv environment handles rendering. These are deliberately separate.
- **Parquet/CSV is the interface contract**: The data file is the boundary between data preparation and visualization. This separation is load-bearing.
- **Thin runner**: `viz_runner.py` is intentionally ~40-60 lines. If it grows beyond ~80 lines, reconsider the design. Complexity belongs in the generated scripts, not the runner.
- **No metadata JSON files**: The `.py` script IS the documentation. Anyone can read the script to understand what data it uses and how it plots.
- **No test suite by design**: The runner is simple enough that errors surface immediately during use. A test suite would add maintenance burden without meaningful coverage.
- **Lean SKILL.md**: Should stay ~80-120 lines. Styling details, examples, and edge cases go in `references/styling.md`, not in SKILL.md.

## Making Changes

### Runner changes (`viz_runner.py`)

Keep it thin. Resist adding features. The runner's job is to execute a generated script in the bundled environment - nothing more. If you find yourself adding logic to the runner, it probably belongs in the generated script template instead.

### SKILL.md changes

Keep it lean. SKILL.md tells Claude *what to do* and *how to structure the output*. Move detailed guidance, styling specifics, and examples to `references/`. If SKILL.md grows past ~120 lines, refactor content into reference files.

### Styling changes

Edit `references/styling.md`, not SKILL.md. Styling details include color palettes, font sizes, axis formatting, legend placement, and publication quality standards.

### Dependencies

The bundled uv environment should only contain: `matplotlib`, `seaborn`, `pandas`, `pyarrow`. Resist adding libraries. If a visualization needs a specialized library, that's a sign it may not belong in this skill.

## Testing Changes

No dedicated test suite. Test by creating a visualization end-to-end:

1. Write a data file (`.parquet` or `.csv`) to `.viz/`
2. Write a self-contained Python script that reads the data and produces a plot
3. Run the runner: `uv run --directory <scripts_dir> python <scripts_dir>/viz_runner.py <name>`
4. Verify the output image is correct

## Integration Points

- **Invocation**: The skill is invoked by Claude when users ask to plot, chart, graph, or visualize data.
- **Runner invocation**: `uv run --directory <scripts_dir> python <scripts_dir>/viz_runner.py <name>`
- **Presentation skill**: The presentation skill copies images from `.viz/` into its `assets/` directory. Changes to output paths or naming conventions affect presentation integration.
- **Working directory**: All viz artifacts live in `.viz/` at the project root.
