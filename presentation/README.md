# Presentation Skill

Create and manage professional presentations using Marp markdown with Claude.

## Overview

This skill helps you create slide decks through natural conversation. You can:

- Create presentations with a defined structure upfront
- Build presentations incrementally during analysis
- Have Claude synthesize a presentation from your work

**Note:** When talking to Claude, "charts" means slides and "graphs" means visualizations.

## Project Structure

Presentations are stored in a `presentations/` folder at your project root:

```
your-project/
├── presentations/
│   ├── q4-review/
│   │   ├── slides.md      # The presentation
│   │   └── assets/        # Images for this deck
│   └── product-launch/
│       ├── slides.md
│       └── assets/
└── .viz/                  # Graphs from viz skill
```

Each presentation is self-contained with its own assets folder, making it easy to share or move.

## Quick Start

### Create a Presentation

```
"Create a presentation called q4-review with these slides:
Title, Executive Summary, Revenue, Customers, Next Steps"
```

Claude creates the presentation with title-only slides, ready for you to fill in.

### Add Content

```
"Let's work on the Revenue slide"
"Add three bullets about our growth metrics"
"Include the revenue graph from viz"
```

### Compile to PDF

```
"Generate a PDF"
```

Or run directly:
```bash
.claude/skills/presentation/scripts/compile_marp.sh q4-review pdf
```

## Three Ways to Work

### 1. Blank Canvas

You know the structure. Claude creates the skeleton.

1. Tell Claude your slide titles
2. Claude creates title-only slides
3. Focus on one slide at a time
4. Add content, graphs, iterate
5. Compile when done

**Best for:** Planned presentations, status updates, recurring reports

### 2. Analysis-Driven

Build the presentation as you work.

1. Do your analysis, create graphs
2. "Add this graph to my presentation as a new slide"
3. Continue working, add more slides
4. Update slides as insights emerge

**Best for:** Data exploration, research presentations

### 3. Context Synthesis

Claude proposes a presentation from your work.

1. "Create a presentation about our Q4 analysis"
2. Claude proposes slide titles
3. You approve/adjust the structure
4. Claude walks through each slide with you
5. You refine content together

**Best for:** Summarizing completed work, quick decks from notes

## Commands Reference

| What you want | What to say |
|---------------|-------------|
| Create deck | "Create presentation called X with slides: A, B, C" |
| Focus on slide | "Let's work on the Summary slide" |
| Add bullet | "Add a bullet about market growth" |
| Add graph | "Add the revenue graph from viz" |
| New slide | "Add a slide called Appendix after Next Steps" |
| Delete slide | "Remove the Challenges slide" |
| Reorder | "Move Summary to after Analysis" |
| Update graph | "Replace the graph with the updated version" |
| Compile | "Generate a PDF" / "Compile to PowerPoint" |
| Navigate | "Next slide" / "Previous slide" |

## Working with Graphs

Graphs from the viz skill (`.viz/`) are copied into your presentation's `assets/` folder. This keeps each presentation self-contained.

**Add a graph:**
```
"Add the revenue graph to this slide"
```

**Update a graph:**
```
"Replace the graph with the updated version from viz"
```

## Compilation

Output formats: PDF, PowerPoint (pptx), HTML

**Using the script:**
```bash
.claude/skills/presentation/scripts/compile_marp.sh <name> [format]

# Examples
.claude/skills/presentation/scripts/compile_marp.sh q4-review        # PDF
.claude/skills/presentation/scripts/compile_marp.sh q4-review pptx   # PowerPoint
```

**Direct marp command:**
```bash
cd presentations/q4-review
marp --no-stdin --allow-local-files slides.md -o slides.pdf
```

## Tips

- **Slide titles are stable** - Claude references slides by title, not number
- **One slide at a time** - Focus commands help Claude know where to edit
- **Graphs are copied** - Original stays in `.viz/`, copy goes to `assets/`
- **Self-contained decks** - Share the whole folder, images included

## Troubleshooting

**Marp hangs:** Make sure to use `--no-stdin` flag

**Images not showing:** Use `--allow-local-files` flag, check paths are relative (`./assets/`)

**Wrong slide edited:** Say "Let's work on [slide title]" to set focus

**Multiple presentations:** If Claude asks which one, specify the name

## Requirements

- [Marp CLI](https://github.com/marp-team/marp-cli) installed
- For PDF output: Chrome/Chromium (marp uses it for rendering)
