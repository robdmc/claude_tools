---
name: presentation
description: Create and manage presentations using Marp markdown. Trigger on "presentation", "slides", "deck", "slide deck", "Marp", "charts" (when referring to slides, not graphs).
---

# Marp Presentation Skill

Create and manage professional presentations from markdown using Marp.

**Terminology:** The user may refer to slides as "charts" (not graphs/visualizations - those are called "graphs").

## Project Structure

All presentations live in a `presentations/` folder at project root. Each presentation is self-contained with its own assets directory:

```
project-root/
├── .viz/                           # Global viz output (from viz skill)
├── presentations/
│   ├── q4-review/
│   │   ├── slides.md               # Main presentation file
│   │   └── assets/                 # Images, graphs for this deck
│   │       ├── revenue-graph.png
│   │       └── logo.png
│   └── product-launch/
│       ├── slides.md
│       └── assets/
└── .claude/skills/presentation/    # The skill itself
```

## Three Workflows

### Workflow 1: Blank Canvas (Sketch-First)

For users who have completed analysis and know the structure they want.

1. **Create deck with titles**: "Create a presentation called q4-review with these slides: Title, Executive Summary, Revenue Analysis, Customer Growth, Challenges, Next Steps"
2. **Skill creates**: `presentations/q4-review/slides.md` with title-only slides
3. **Preview**: Compile to PDF to see the structure
4. **Focus on slide**: "Let's work on Revenue Analysis"
5. **Iterate**: "Add three bullets about growth metrics" / "Include the revenue graph from viz"
6. **Move focus**: "Now let's do Customer Growth"
7. **Reorder/add/delete**: "Move Challenges before Next Steps" / "Add a slide called Appendix"

### Workflow 2: Analysis-Driven (Incremental)

For users building a presentation while doing analysis.

1. **During analysis**: Generate a graph with viz skill
2. **Add to presentation**: "Add this graph to the q4-review presentation as a new slide called Revenue Trends"
3. **Continue analysis**: More work, more insights
4. **Update existing**: "Update the Revenue Trends slide with a bullet about 15% YoY growth"
5. **Replace viz**: "Replace the graph on Revenue Trends with the updated version"

### Workflow 3: Context Synthesis (One-Shot)

For users who want Claude to generate a presentation from available context.

1. **Trigger**: "Create a presentation about the Q4 analysis" or "Summarize this project as a deck"
2. **Context gathering**: By default, use what's already in conversation context
   - If user mentions scribe: Load scribe notes from `.scribe/`
   - If user mentions viz: List/examine outputs in `.viz/`
   - If user mentions files: Read specified files
3. **Propose structure**: Claude proposes slide titles based on synthesized context
4. **Iterate on outline**: User approves, adds, removes, reorders proposed titles
5. **Guided slide-by-slide**: Claude walks through each slide, prompting user for input:
   - "For the Executive Summary, I'm thinking [draft]. What would you adjust?"
   - "The Revenue Analysis slide could include [the graph from viz]. Should I add it?"
6. **Refinement**: User provides feedback, Claude refines each slide before moving to next

**Key behaviors for context synthesis:**
- Start by proposing titles and getting approval on structure first
- Don't fill in all content at once - walk through slide by slide
- Actively prompt user at each step rather than assuming
- Mention what context sources are available (scribe notes, viz outputs) and ask if they should be incorporated

**Tip - Tagging for later:** Users can tag scribe entries during analysis (e.g., "presentation artifact") and later ask: "Create a presentation from scribe entries tagged 'presentation artifact'". Search `.scribe/` for matching entries and use those as context.

## Context Tracking

The skill tracks context to enable natural conversation about presentations:

**Active Presentation:**
- Set when user creates/opens a presentation
- Inferred from recent conversation ("the q4-review deck")
- Ask if ambiguous and multiple presentations exist

**Focused Slide:**
- Set when user says "let's work on X" or "focus on X"
- Inferred from recent edits ("add another bullet" applies to last-edited slide)
- Shifts naturally with "next slide", "previous slide", "now let's do Y"

## Key Operations

| Operation | Example Command |
|-----------|-----------------|
| Create blank deck | "Create presentation called q4-review with slides: Title, Summary, Analysis" |
| One-shot from context | "Create a presentation summarizing this analysis" |
| One-shot with sources | "Create a deck based on the scribe notes and viz outputs" |
| Focus on slide | "Let's work on the Summary slide" |
| Add content | "Add a bullet about market growth" |
| Import viz | "Add the revenue graph from viz to this slide" |
| Add new slide | "Add a slide called Appendix after Next Steps" |
| Delete slide | "Remove the Challenges slide" |
| Reorder | "Move Summary to after Analysis" |
| Update viz | "Replace the graph with the updated version from viz" |
| Compile | "Generate a PDF" / "Compile to PowerPoint" |

## Viz Integration

When user says "add this graph to the presentation":

1. Identify source file in `.viz/` (from context or ask)
2. Copy to `presentations/<slug>/assets/<filename>.png`
3. Add/update slide with `![w:700](./assets/<filename>.png)`

When user says "update the graph":

1. Identify which graph (from context or ask)
2. Re-copy from `.viz/` to `assets/` (overwrite)
3. No markdown changes needed if filename unchanged

**Why copy to assets?** Each presentation is self-contained and portable. Copying ensures the presentation works even if `.viz/` changes or the presentation is shared.

## Creating a Presentation

When creating a new presentation:

1. Create directory: `presentations/<slug>/`
2. Create assets folder: `presentations/<slug>/assets/`
3. Create `slides.md` with frontmatter and CSS

### Standard Template

Use this CSS in every presentation for consistent, professional styling:

```markdown
---
marp: true
theme: default
paginate: true
style: |
  section {
    background: white;
    color: #1a1a1a;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    display: block !important;
    padding: 120px 70px 60px 70px;
    position: relative;
  }
  section:not(.title) > h2:first-child {
    position: absolute;
    top: 50px;
    left: 70px;
    margin: 0;
    font-size: 1.6em;
    color: #2563eb;
  }
  section.title {
    display: flex !important;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
  }
  section.title h1 {
    font-size: 2.5em;
    color: #2563eb;
  }
  h2 { color: #2563eb; }
  h3 { color: #374151; }
  ul, ol { margin-left: 0; padding-left: 1.5em; }
  li { margin-bottom: 0.5em; line-height: 1.4; }
  table { width: 100%; border-collapse: collapse; margin: 1em 0; }
  th { background: #2563eb; color: white; padding: 12px; text-align: left; }
  td { padding: 10px 12px; border-bottom: 1px solid #e5e7eb; }
  tr:nth-child(even) { background: #f9fafb; }
  img { max-width: 100%; height: auto; }
  code { background: #f3f4f6; padding: 2px 6px; border-radius: 4px; }
---
```

### Title Slide

```markdown
<!-- _class: title -->

# Presentation Title

### Subtitle or Author

Date
```

### Content Slides (Blank Canvas)

When creating from an outline, use title-only slides:

```markdown
---

## Executive Summary

---

## Revenue Analysis

---

## Customer Growth
```

## Compilation

Use the compile script with a presentation slug:

```bash
{SKILL_DIR}/scripts/compile_marp.sh q4-review pdf
```

Or compile directly:

```bash
cd presentations/q4-review
marp --no-stdin --allow-local-files slides.md -o slides.pdf
```

**Output formats:** pdf, pptx, html

**Critical flags:**
- `--no-stdin` - Prevents marp from hanging waiting for input
- `--allow-local-files` - Enables local image references

## Slide Structure

### Slides with Images/Graphs

```markdown
---

## Analysis Results

![w:700](./assets/revenue-graph.png)

Key insight from the data.
```

### Image Sizing

```markdown
![w:500](image.png)       # Width 500px
![h:400](image.png)       # Height 400px
![w:600 h:400](image.png) # Both dimensions
```

### Two-Column Layout

```markdown
---

## Comparison

<div style="display: flex; gap: 40px;">
<div style="flex: 1;">

### Option A
- Point 1
- Point 2

</div>
<div style="flex: 1;">

### Option B
- Point 1
- Point 2

</div>
</div>
```

### Speaker Notes

```markdown
---

## Slide Title

Content here

<!--
Speaker notes go here.
These won't appear on the slide.
-->
```

## Integration with Other Skills

### Viz Skill

- Viz outputs graphs to `.viz/` directory
- Copy relevant graphs to presentation assets for portability
- Reference as `./assets/<filename>.png` in slides

### Scribe Skill

- Scribe notes live in `.scribe/` directory
- Can be used as source material for context synthesis workflow
- Search by tags to find relevant entries

## References

- `references/workflows.md` - Detailed workflow examples
- `references/marp-syntax.md` - Complete Marp syntax reference
- `references/chart-styling.md` - Matplotlib styling for presentation graphs
