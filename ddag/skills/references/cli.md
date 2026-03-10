# ddag CLI Reference

All commands: `python {SKILL_DIR}/scripts/ddag_build.py <command> --root .`

Run `--help` for full details on any command. Most commands have Python equivalents in `ddag_build` (see `references/api.md`) — prefer the Python API when you need structured return values.

## Commands

| Command | Purpose | Key flags |
|---------|---------|-----------|
| `status` | Show all nodes with type and staleness | |
| `stale` | List stale nodes in build order | |
| `script` | Generate Python build script for stale nodes | `--all` for all compute nodes |
| `build` | Build stale nodes, update stats, print sample rows | `--node <path>` for single node |
| `audit` | Check descriptions: missing, schema drift, shared columns | |
| `summary` | JSON overview: node count, pipeline count, breakdown | |
| `lineage` | Upstream/downstream lineage for a node | `--node <path>` (required) |
| `file-context` | Look up a data file across all nodes (JSON) | `--file <path>` (required) |
| `diagram` | Render Mermaid DAG diagram to PNG or .mmd fallback | `-o <path>` |
| `dump-function` | Dump transform function to .py for external editing | `--node <path>` (required) |
| `load-function` | Load edited transform function back into node | `--node <path>` (required), `--plan <text>` (required) |
| `load-script` | *Disabled in CLI* — use Python API with plans dict | |
| `clean` | Delete all compute node output files (interactive confirmation) | |

## Examples

```bash
# Build everything stale
python {SKILL_DIR}/scripts/ddag_build.py build --root .

# Build a single node (with upstream if needed)
python {SKILL_DIR}/scripts/ddag_build.py build --node path/to/node.ddag --root .

# Dump → edit → load → build cycle
python {SKILL_DIR}/scripts/ddag_build.py dump-function --node path/to/node.ddag --root .
# ... user edits _ddag_{stem}.py ...
python {SKILL_DIR}/scripts/ddag_build.py load-function --node path/to/node.ddag --plan "Updated plan describing the new logic" --root .
python {SKILL_DIR}/scripts/ddag_build.py build --node path/to/node.ddag --root .
```

```bash
# Delete all compute outputs (prompts for confirmation)
python {SKILL_DIR}/scripts/ddag_build.py clean --root .
```

If any CLI command fails (non-zero exit or traceback), show the error to the user and investigate before continuing.
