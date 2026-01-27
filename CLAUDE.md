# Claude Tools Repository

A collection of Claude skills and agents. Use `/install` to add tools to your Claude Code environment.

## Creating a New Tool

### Directory Layout

Each tool is a top-level directory with this structure:

```
tool_name/
├── README.md              # Human documentation (required)
├── skills/                # Skill definitions
│   └── SKILL.md           # Skill for Claude (required)
└── agents/                # Agent definitions (optional)
    └── worker-name.md     # Agent protocols
```

### README.md

Each tool needs a human-readable README at the root explaining:
- What the tool does
- How to use it
- Any requirements or dependencies

This is for humans browsing the repo, not for Claude.

### Skills

Use the `/skill-creator` skill for guidance on writing SKILL.md files, including:
- YAML frontmatter fields
- System prompt design
- Scripts, references, and assets

### Agents

Use the `/agent-development` skill or the `agent-creator` agent for guidance on writing agent markdown files, including:
- Agent frontmatter structure
- System prompt best practices
- Tool restrictions

## Path Placeholders

Skills use these placeholders for portable paths:

| Placeholder | Resolves To |
|-------------|-------------|
| `{SKILL_DIR}` | Directory containing the SKILL.md file |
| `{AGENTS_DIR}` | The agents directory (`~/.claude/agents/` or `.claude/agents/`) |

`{SKILL_DIR}` is interpolated in `allowed-tools` frontmatter. `{AGENTS_DIR}` in the SKILL.md body is a documentation convention—Claude reads the referenced file at runtime.

## Installation

### Quick Start

```
/install        # Interactive installation wizard
/install list   # Show available tools
```

### Modes

| Mode | Description |
|------|-------------|
| **Copy** | Files are copied to target. Independent but won't auto-update. |
| **Symlink** | Links to source files. Auto-updates but requires repo access. |

### Targets

| Target | Path | Use Case |
|--------|------|----------|
| **Global** | `~/.claude/` | Available in all projects |
| **Project** | `.claude/` | Only in current project, can be version controlled |
