# Presentation Skill

Build professional PPTX presentations from prose documents.

## How It Works

1. Write a document describing your presentation — slide-by-slide specs, an outline, or detailed notes
2. Run `/presentation <filename>`
3. Claude reads the document, designs the deck (colors, style, structure), generates all slides in parallel, and delivers a `.pptx`

## Quick Start

```
/presentation how-it-works.md
```

Claude handles several input types:
- **No file / new file** → choose between a spec interview or a skeleton outline
- **Existing markdown** → choose between refining with a spec interview or building immediately
- **`.pptx` file** → extracts content and theme, then offers spec interview or build
- **`.pdf` file** → extracts text, then offers spec interview or build

## Spec Interview

Every invocation path offers the option to refine your presentation through a structured spec interview before building. When you choose the interview path, Claude delegates to the `/spec` skill with presentation-specific prompts that explore:

- **Slide-by-slide narrative flow** — produces structured `### Slide Title` headings
- **Visual style and color preferences** — feeds the design brief
- **Diagram and data visualization needs** — elicits `[viz: name]` references
- **Audience and delivery context** — shapes complexity and tone

After the interview, the refined document flows into the build pipeline automatically.

## PPTX/PDF Input

Start from an existing presentation instead of writing from scratch:

```
/presentation existing-deck.pptx
/presentation quarterly-report.pdf
```

**PPTX files** — Claude extracts slide text (via markitdown), theme colors and fonts (from theme1.xml), and generates a thumbnail grid for visual reference. The extracted content is written as skeleton-structured markdown.

**PDF files** — Claude extracts text content using its built-in PDF reader. No style extraction is available, so the presentation will be designed fresh.

After extraction, you choose whether to refine the content with a spec interview or build immediately.

## Input Format

Any prose document that describes a presentation. The more detail you provide, the better the output. You can include:

- **Title and purpose** — what the presentation is about
- **Audience** — who it's for and their familiarity level
- **Slide descriptions** — what each slide should show (text, diagrams, charts, data)
- **Diagram layouts** — ASCII art, flowchart descriptions, timeline specs
- **Style preferences** — color palette, text density, visual approach
- **Image references** — paths to existing images or charts to embed

### Example

```markdown
# Q4 Business Review

## Purpose
Present Q4 results to the leadership team.

## Audience
Executives. Keep it high-level with supporting detail available.

## Style Notes
Colors: Blue (#4C72B0) for revenue, Orange (#DD8452) for costs. Clean, minimal.

## Slides

### Title
- "Q4 Business Review"
- Subtitle: FY2025 Quarter 4 Results

### Revenue Overview
Show revenue growth YoY. Embed the revenue chart from first_doc_attempt/revenue.png.
Key points: 15% growth, North region outperformed, driven by enterprise customers.

### Process Flow
Diagram: Three-step horizontal flowchart — "Ingest" → "Analyze" → "Report".
Blue boxes with white text, connected by right-pointing arrows.

### Key Takeaways
- Revenue up 15%
- Enterprise customers up 42%
- Retention improved to 94%
```

## Design Phase

Before generating slides, Claude reads the full document and produces:
- A **slide plan** — structured spec for each slide
- A **design brief** — color palette, style rules, audience context
- A **customized template** — base template with your colors applied

This ensures visual coherence across all slides — consistent colors, terminology, and style.

## Diagram Support

Describe diagrams in natural language. Claude generates them as native, editable PowerPoint elements using a hybrid approach:
- Boxes, labels, backgrounds → HTML `<div>` elements (converted to native PPT shapes)
- Connectors, arrows, lines → PptxGenJS calls added after conversion

Provide as much detail as you want — ASCII layouts, color specs, structural notes. Richer descriptions produce better diagrams.

## Viz Integration

Reference visualizations from `.viz/` using `[viz: name]` anywhere in your document. The name is fuzzy-matched — `[viz: revenue]` matches `revenue-by-region.png`. Images are copied to the presentation's `assets/` directory.

## Output

```
presentations/
└── q4-business-review/
    ├── slides/
    │   ├── slide-0.html
    │   ├── slide-1.html
    │   └── ...
    ├── build.js
    ├── slides.pptx         # Final output
    └── assets/
```

Output: PPTX (default). Optional PDF export via LibreOffice after build.

## Requirements

- **document-skills:pptx** — must be installed; provides html2pptx, PptxGenJS, Playwright, thumbnail.py, and LibreOffice
- **spec skill** — needed for the spec interview workflow (optional — skeleton and direct build work without it)
- **markitdown** — needed for PPTX content extraction (`pip install markitdown`; optional — only for PPTX input)

## Troubleshooting

**Viz reference not found:** Check `.viz/` directory. The name is fuzzy-matched so partial names work.

**Diagram shapes misaligned:** Connector/arrow placement is validated after full assembly using thumbnail.py. The skill performs one rebuild pass to fix issues.

**PDF export:** LibreOffice must be installed and accessible via `libreoffice` on the PATH.
