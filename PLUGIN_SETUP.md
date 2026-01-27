# Plugin Setup

This repository works best with these recommended plugins installed.

## Prerequisites

Ensure you have Claude Code CLI installed and configured. See [README.md](README.md#installing-claude-code) for installation instructions.

## Add Marketplaces

```bash
claude plugin marketplace add anthropics/skills
claude plugin marketplace add anthropics/claude-plugins-official
```

## Install Recommended Plugins

```bash
claude plugin install context7@claude-plugins-official
claude plugin install document-skills@anthropic-agent-skills
claude plugin install plugin-dev@claude-plugins-official
claude plugin install pyright-lsp@claude-plugins-official
```

| Plugin | Description |
|--------|-------------|
| **context7** | Up-to-date documentation lookup for libraries and frameworks |
| **document-skills** | Document creation and manipulation (PDF, PPTX, XLSX, etc.) |
| **plugin-dev** | Skill and agent development tools (`/skill-creator`, `/agent-development`) |
| **pyright-lsp** | Python language server for type checking and intellisense |

## Verification

```bash
# List installed marketplaces
claude plugin marketplace list

# List installed plugins
claude plugin list

# List all available plugins
claude plugin list --available --json
```

## Uninstalling

```bash
# Remove a plugin
claude plugin uninstall document-skills
claude plugin uninstall pyright-lsp@claude-plugins-official

# Remove a marketplace
claude plugin marketplace remove anthropic-agent-skills
claude plugin marketplace rm claude-plugins-official
```
