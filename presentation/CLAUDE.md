# Presentation Skill Development Guide

Instructions for Claude sessions working on this skill.

## Before Making Changes

Read the current skill files to understand the existing structure:
- `skills/SKILL.md` — Main skill definition (Claude reads this)
- `skills/references/component-map.md` — HTML patterns for slide elements
- `skills/references/template.html` — Base slide HTML/CSS template
- `skills/references/skeleton.md` — Template for new presentation outlines

## Skill Architecture

```
presentation/
├── README.md                       # Human documentation
├── CLAUDE.md                       # This file - development instructions
└── skills/
    ├── SKILL.md                    # Main skill definition (required)
    └── references/
        ├── skeleton.md             # Skeleton for new presentation outlines
        ├── template.html           # Base slide HTML/CSS template
        └── component-map.md        # HTML patterns for slide elements
```

## Key Design Decisions

These decisions were made intentionally — preserve them unless explicitly changing:

- **No sketch format**: Input is any prose document. No intermediate sketch conversion step.
- **Design phase**: The main agent reads the full document and produces a slide plan, design brief, and customized template before any slides are generated. This ensures cross-slide coherence.
- **Template customization**: The base template has a default accent color (#4472C4) that gets replaced with the primary color from the design brief during the design phase.
- **Pipeline**: Design phase → parallel HTML-generating agents → document-skills:pptx → PPTX output.
- **Diagram approach**: Hybrid — HTML `<div>` elements for boxes/labels (html2pptx converts natively), PptxGenJS snippets for connectors/arrows/lines.
- **Slug**: Derived from the `#` title heading — lowercase, spaces → hyphens, non-alphanumeric removed.
- **Location**: All presentations in `presentations/<slug>/` at project root.
- **Self-contained**: Each presentation has its own `assets/` directory.
- **Asset resolution**: Image paths from the source document are resolved relative to the input file's directory, not the output directory.
- **Model**: All sub-agents (slide agents and pptx execution agent) use `model: sonnet`.
- **Spec integration**: Via `/spec <filename> <hint>` — the spec skill is never modified by this skill. The hint text steers the interview toward presentation-relevant angles (structure, style, viz, audience).
- **PPTX/PDF extraction**: Binary inputs are extracted to skeleton-structured markdown before entering the normal flow. The build pipeline always reads markdown — extraction is a pre-processing step.
- **Always-offer choice**: Every invocation path (PPTX, PDF, new file, existing file) lets the user choose between spec interview and immediate action. No path forces either workflow.
- **Agents write to disk, never return content**: Slide agents MUST write HTML and diagram snippets to files and return only a short status string (`OK: slide-N` or `WRITE_FAILED: slide-N`). This prevents context bloat in the orchestrator — returning full HTML from N parallel agents would degrade quality. If agents can't write (permission denied), they report failure rather than dumping content.
- **Diagram snippets on disk**: Agents write PptxGenJS snippets to `slide-<n>.diagram.js` files. The assembly agent reads these files when building `build.js`. The orchestrator never sees snippet code.
- **Assembly is agentified**: Step 4 (build.js assembly) is a separate agent that reads HTML paths and diagram snippet files from disk. This keeps the orchestrator's context clean — it only passes the slug, slide count, and resolved tool paths.
- **Permission warm-up**: Step 2 creates the output directory structure and writes a placeholder file before agents spawn. This establishes write permissions early so parallel agent writes are more likely to be auto-approved.
- **Validate-first, build-once**: The Step 5 agent reads ALL slide HTML files and fixes all html2pptx constraint violations before running `build.js`. This avoids the costly serial loop of build → error on slide N → fix → rebuild → error on slide N+1. One validation pass + one build is far faster than N incremental rebuilds.
- **Dependencies pre-installed**: The assembly agent (Step 4) runs `npm install pptxgenjs sharp` after writing `build.js`. The Step 5 agent never hunts for dependencies.
- **No reading html2pptx.js**: The validation agent applies constraint rules from the skill document. Reading the converter source code wastes turns and context without helping fix violations.

## Making Changes

### Updating SKILL.md

This is what Claude reads when the skill is triggered. Keep it:
- Complete — covers all invocation paths, build steps, and edge cases
- Accurate — the HTML template block in SKILL.md must match `references/template.html`

SKILL.md contains inlined sections that slide agents receive in their prompts:
1. The customized HTML/CSS template — base matches `references/template.html`, accent color replaced per-deck in design phase
2. The html2pptx constraints — derived from the pptx skill's `html2pptx.md`; if the pptx skill updates its validation rules, update the constraints section in SKILL.md
3. The Playwright preview script — self-contained, no external dependencies beyond Playwright
4. The slide element patterns from `references/component-map.md`

When changing the base template, update **both** `SKILL.md` (the inlined block) and `references/template.html`.

### Updating references/

- `template.html` — Update when changing base slide styling. Mirror changes into SKILL.md.
- `component-map.md` — Update when adding HTML patterns or changing output conventions. All `<div>` examples must wrap text in `<p>` tags (html2pptx constraint).
- `skeleton.md` — Update when changing the outline template for new presentations.

## Updating README.md

After making changes to the skill, update `README.md` to reflect those changes. Keep it in sync with `SKILL.md`.

## Integration Points

This skill integrates with:
- **document-skills:pptx** — Required for html2pptx.js, PptxGenJS, Playwright, thumbnail.py, and LibreOffice. Paths resolved via Glob at build time. Also provides `unpack.py` (via `**/pptx/ooxml/scripts/unpack.py`) and `thumbnail.py` used for PPTX input extraction.
- **Spec skill** — Used for spec-driven refinement when user chooses the interview path. Invoked as `/spec <filename> <hint>` with presentation-specific angles. The spec skill is never modified.
- **Viz skill** — Outputs to `.viz/`, presentation copies to `assets/`
