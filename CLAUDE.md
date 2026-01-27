# Claude Tools Repository

A collection of Claude skills, agents, and commands that extend Claude Code's capabilities.

## Quick Start

Run `/install` to interactively install tools to your global (`~/.claude/`) or project (`.claude/`) location.

```
/install        # Interactive installation wizard
/install list   # Show available tools
```

## Available Tools

| Tool | Description |
|------|-------------|
| **brainstorming** | Socratic brainstorming skill with parallel perspective agents |
| **scribe** | Narrative logging skill with file archiving |
| **viz** | Data visualization skill for matplotlib/seaborn plots |
| **duckdb_sql** | DuckDB SQL query assistant |

## Tool Structure

Each tool is a top-level directory containing one or more component types:

```
tool_name/
├── skills/                 # Skill definitions
│   ├── SKILL.md           # Required - Skill definition with YAML frontmatter
│   ├── scripts/           # Optional - Executable code (Python/Bash)
│   ├── references/        # Optional - Documentation loaded as needed
│   └── assets/            # Optional - Templates, images, fonts
├── agents/                # Agent definitions (optional)
│   └── agent-name.md      # Agent markdown files
└── commands/              # Legacy commands (optional)
    └── command-name.md    # Simple markdown commands
```

### Skills

Skills are the primary way to extend Claude. A skill requires:
- `skills/SKILL.md` - Skill definition with YAML frontmatter

Optional subdirectories:
- `skills/scripts/` - Executable code that the skill can invoke
- `skills/references/` - Documentation loaded into context as needed
- `skills/assets/` - Files used in output (templates, images)

### Agents

Agents are markdown files defining specialized personas for use with the Task tool:
- Stored in `agents/` directory
- Flat structure (no subdirectories)
- Installed to `{target}/agents/` when using `/install`

### Commands (Legacy)

Commands are simple markdown files without frontmatter:
- Stored in `commands/` directory
- Less capable than skills (no scripts, references, or assets)
- Still functional but skills are recommended for new development

## Path Placeholders

Skills should use placeholders for portable paths:

| Placeholder | Resolves To |
|-------------|-------------|
| `{SKILL_DIR}` | Directory containing the SKILL.md file |
| `{AGENTS_DIR}` | The agents directory (`~/.claude/agents/` or `.claude/agents/`) |

Example in SKILL.md:
```yaml
allowed-tools: Bash(python {SKILL_DIR}/scripts/runner.py:*)
```

## Adding New Tools

1. Create a top-level directory with your tool name
2. Add at least one component:
   - `skills/SKILL.md` for a skill
   - `agents/*.md` for agents
   - `commands/*.md` for legacy commands
3. Follow the standard directory structure
4. Test with `/install list` to verify discovery

## Installation Modes

| Mode | Description |
|------|-------------|
| **Copy** | Files are copied to target. Independent but won't auto-update. |
| **Symlink** | Links to source files. Auto-updates but requires repo access. |

## Installation Targets

| Target | Path | Use Case |
|--------|------|----------|
| **Global** | `~/.claude/` | Available in all projects |
| **Project** | `.claude/` | Only in current project, can be version controlled |
