# Presentation Skill

Build professional Marp presentations from a sketch file.

**Note:** When talking to Claude, "charts" means slides and "graphs" means visualizations.

## How It Works

1. Run `/presentation <filename>` — if the file doesn't exist, a skeleton is created for you
2. Edit the sketch file to add your talking points and viz references
3. Run `/presentation <filename>` again — Claude builds and compiles the presentation

## Quick Start

```
/presentation q4-review.md
```

If `q4-review.md` doesn't exist, Claude creates it with a skeleton showing all available components. Edit it, then run the command again to build.

## Sketch Format

The sketch file is plain markdown with a few custom tags:

```markdown
# Presentation Title

## Slide Title
- Key point one
- Key point two
[viz: chart-name]

## Another Slide
[callout: Big stat or key quote here]

- Supporting detail
```

### All Available Components

| Component | Syntax | Description |
|-----------|--------|-------------|
| Title | `# Title` | First `#` heading — presentation title |
| Slide | `## Slide Title` | Each `##` becomes a slide |
| Bullets | `- text` | Bullet list |
| Numbered list | `1. text` | Ordered list |
| Viz embed | `[viz: name]` | Graph from `.viz/` (no extension needed) |
| Image | `[image: path]` | Any local image by path |
| Callout box | `[callout: text]` | Highlighted box for key stats or quotes |
| Two-column | `[two-col]` ... `[---]` ... `[/two-col]` | Side-by-side layout |
| Table | pipe table | Standard markdown table |
| Block quote | `> text` | Block quote |
| Speaker notes | `[notes: text]` | Hidden from audience |

### Example Sketch

```markdown
# Q4 Business Review

## Revenue Analysis
- Revenue grew 15% YoY
- North region outperformed expectations
[viz: revenue-by-region]

## Key Result
[callout: 42% increase in enterprise customers]

- Driven by new product launch
- Retention also improved to 94%

## Comparison
[two-col]
### Q3
- Revenue: $3.8M
- Customers: 420

[---]
### Q4
- Revenue: $4.2M
- Customers: 523
[/two-col]

## Next Steps
1. Expand North region headcount
2. Launch retention program
[notes: Close with a call to action — ask for questions]
```

## Viz Integration

`[viz: name]` fuzzy-matches against `.viz/*.png`. You don't need the full filename or extension — `[viz: revenue]` will match `revenue-by-region.png`. If multiple files match, Claude will ask which one you want.

Matched images are copied into `presentations/<slug>/assets/` to keep each presentation self-contained.

## Output

Presentations are written to `presentations/<slug>/`:

```
presentations/
└── q4-business-review/
    ├── slides.md       # Generated Marp source
    ├── slides.pdf      # Compiled output
    └── assets/         # Copied images
```

Output formats available: PDF (default), PowerPoint (pptx), HTML.

To compile manually:
```bash
.claude/skills/presentation/scripts/compile_marp.sh q4-review pdf
```

## Requirements

- [Marp CLI](https://github.com/marp-team/marp-cli) installed (`npm install -g @marp-team/marp-cli`)
- For PDF output: Chrome/Chromium (Marp uses it for rendering)

## Troubleshooting

**Marp hangs:** The script uses `--no-stdin` to prevent this. If running Marp directly, include that flag.

**Images not showing:** Use `--allow-local-files` flag. Check that image paths are relative (`./assets/`).

**Viz reference not found:** Check `.viz/` directory. The name is fuzzy-matched so partial names work.
