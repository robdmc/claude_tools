# Presentation Skill — pptx Migration Specification

## Overview

Replace the current Marp-based presentation pipeline with the `document-skills:pptx` skill. The new pipeline generates slide HTML in parallel agents, previews each slide via Playwright screenshot, assembles the full deck, and delegates final conversion to `document-skills:pptx`. Output is `.pptx` (with optional PDF via LibreOffice).

Marp is removed entirely. All Marp-specific infrastructure is deleted.

---

## Slug Derivation

The presentation slug is derived from the title `#` heading: lowercase, spaces replaced with hyphens, non-alphanumeric characters (except hyphens) removed. Example: `# Customer Growth Forecasting` → `customer-growth-forecasting`. All output paths use `presentations/<slug>/`.

---

## Sketch Format

The sketch format is simplified. The following components are **removed**:

- `[mermaid]...[/mermaid]` — dropped entirely
- `[two-col]...[---]...[/two-col]` — dropped entirely

The following components are **retained** (unchanged syntax):

| Component | Syntax |
|-----------|--------|
| Title | `# Title` — first `#` heading |
| Slide | `## Slide Title` — each `##` is one slide |
| Bullets | `- text` |
| Numbered list | `1. text` |
| Viz embed | `[viz: name]` — fuzzy-match against `.viz/*.png` |
| Image | `[image: path]` — any local image path |
| Callout box | `[callout: text]` — highlighted box for key stats or quotes |
| Table | standard markdown pipe table |
| Block quote | `> text` |
| Speaker notes | `[notes: text]` — hidden from audience |

The following component is **new**:

| Component | Syntax |
|-----------|--------|
| Diagram | `[diagram: description]` — generate a native PowerPoint diagram from a text description |

The `[diagram:]` tag is the replacement for `[mermaid]`. It accepts any freeform description — flowcharts, timelines, annotated diagrams, etc. Build-step agents translate the description into native PowerPoint shapes using a hybrid approach:

- **Boxes, labels, colored backgrounds** → HTML `<div>` and `<p>` elements (html2pptx converts these to native PowerPoint shape objects automatically)
- **Connectors, arrows, lines** → PptxGenJS `addShape()` and `addLine()` API calls added after html2pptx conversion

The result is a fully editable PowerPoint diagram — users can click individual boxes, arrows, and labels in PowerPoint and modify them. The description should be as detailed as needed; richer descriptions produce better diagrams.

---

## Spec-to-Sketch Conversion

### Detection

When the skill opens an existing file, it inspects the content heuristically to determine if it is a **sketch** or a **prose spec**. A file is treated as a prose spec if:

- Slide bodies contain full sentences or paragraphs rather than sketch syntax
- No sketch tags (`[image:]`, `[callout:]`, `[viz:]`, `[diagram:]`, etc.) are present
- Content reads as instructions for what a slide should contain rather than the slide content itself

If detection is ambiguous, the skill asks: "This looks like a spec rather than a sketch — should I convert it to sketch format first?" If the user says no, treat the file as a sketch and proceed to build.

### Conversion Workflow

When a prose spec is detected:

1. **Read the full spec** to understand the presentation's scope, audience, and slide structure
2. **Generate a sketch file** by replacing the input file's extension with `.sketch.md` (e.g., `presentation.md` → `presentation.sketch.md`, `deck.md` → `deck.sketch.md`), applying these rules per slide:
   - Condense verbose prose descriptions into bullet points suitable for a slide
   - Replace diagram descriptions (ASCII art, detailed layout specs, flowchart instructions) with `[diagram: <description>]` tags — preserving the full detail of the original description inside the tag
   - Replace references to pre-existing image files with `[image: path]` tags
   - Move implementation notes, rationale, and "to be created" instructions into `[notes:]` tags — they inform the presenter but don't belong on the slide
   - Preserve `##` slide headings unchanged
3. **Stop and tell the user:** "Sketch written to `<path>`. Review it, edit if needed, then run `/presentation <sketch-path>` to build."

### Diagram Tag Fidelity

The `[diagram:]` tag should receive the **full original description** from the spec — including ASCII layouts, color specifications, annotation details, and structural notes. This is what gives build-step agents the information needed to produce accurate diagrams. Do not summarize or abbreviate diagram descriptions when writing them into `[diagram:]` tags.

---

## Build Pipeline

### Step 1: Parse slides

Split the sketch on `##` headings. Each slide spec = heading + all content until the next `##` or EOF.

### Step 2: Resolve images

- Resolve `[viz: name]` — fuzzy-match against `.viz/*.png`; if ambiguous, list matches and ask before proceeding; if no match exists, warn and omit the image (build continues)
- If `.viz/` directory does not exist and the sketch contains `[viz:]` tags, warn and skip all viz embeds
- Copy all resolved images to `presentations/<slug>/assets/`

### Step 3: Generate all slides in parallel

Spawn a Task agent for **every** slide (`subagent_type: general-purpose`, `model: sonnet`). **CRITICAL: Launch ALL slide agents in a single message containing multiple Task tool calls. Do NOT spawn them one at a time across separate messages.**

Each agent receives:
- The slide spec (the `##` heading + its content)
- The slide index `n` (0-based)
- The presentation slug and assets path (`presentations/<slug>/assets/`)
- The built-in default HTML/CSS slide template (see **Slide Template** section below), inlined verbatim
- Instruction to follow the per-slide workflow below

Each agent's workflow:
1. **Generate HTML** — Translate the slide spec into a complete HTML slide document (full `<html>` with template CSS in `<head>`, slide content in `<body>`). Dimensions: `width: 720pt; height: 405pt`. Boxes, labels, and colored backgrounds in `[diagram:]` blocks become `<div>` elements positioned with CSS. Strip `[notes:]` content from the HTML body (it does not appear on the slide). Image paths use `./assets/<filename>`.
2. **Generate diagram snippet** — If the slide contains a `[diagram:]` block, also produce a PptxGenJS code snippet for connectors, arrows, and lines. The snippet operates on a variable named `slide` (the object returned by `html2pptx`). Example: `slide.addShape(pptx.shapes.RIGHT_ARROW, { x: 2, y: 1.5, w: 1, h: 0.5, fill: { color: "4472C4" } });`
3. **Preview** — Write the HTML to a temp file. Screenshot it at 720pt × 405pt using Playwright. Inspect the PNG for text overflow, clipping, and layout problems. **Limitation: PptxGenJS connector/arrow shapes from `[diagram:]` blocks are not visible in this preview** — they are added post-conversion and can only be validated after full assembly.
4. **Refine** — If the preview shows problems in the HTML portion, adjust and re-preview (up to 2 refinement passes).
5. **Return** — Return: (a) the path to the final HTML file written to `presentations/<slug>/slides/slide-<n>.html`, and (b) the PptxGenJS diagram snippet string if applicable (or `null`).

**Agent failure:** If an agent fails or returns malformed output, re-spawn a single replacement agent for that slide with the same inputs. If the retry also fails, abort the build and report which slide failed.

Collect all results in slide order before proceeding.

### Diagram validation (post-assembly)

After Step 5, run `thumbnail.py` on the assembled `slides.pptx` and inspect the full deck. This is when connector and arrow placement in `[diagram:]` slides is validated for the first time. If issues are found, apply targeted fixes to the relevant slides' PptxGenJS snippets in `build.js`, regenerate, and re-inspect. Limit to **1 rebuild pass** after initial assembly.

### Step 4: Assemble — write `build.js`

Write `presentations/<slug>/build.js`. This file runs from the `presentations/<slug>/` directory (all relative paths are relative to it). It:

1. Requires a single shared PptxGenJS instance: `const pptx = new pptxgen(); pptx.layout = 'LAYOUT_16x9';`
2. Requires html2pptx: `const html2pptx = require('<path-to-html2pptx.js>');` — path resolved by the pptx skill sub-agent at execution time
3. For each slide in order:
   ```javascript
   const { slide } = await html2pptx('slides/slide-<n>.html', pptx);
   // diagram snippet applied here if present, e.g.:
   slide.addShape(pptx.shapes.RIGHT_ARROW, { ... });
   ```
4. Saves: `await pptx.writeFile({ fileName: 'slides.pptx' });`

**Notes handling:** `[notes:]` content is stripped from HTML before agents write their slide files (step 3.1 above). No additional strip step needed in `build.js`.

### Step 5: Execute via document-skills:pptx sub-agent

Spawn a Task agent (`subagent_type: general-purpose`) and instruct it to invoke `document-skills:pptx`. The sub-agent:
- Has access to the pptx skill's html2pptx library, PptxGenJS, Playwright, and all dependencies
- Resolves the `html2pptx.js` path and updates the `require()` in `build.js`
- Runs `build.js` from `presentations/<slug>/`: `cd presentations/<slug> && node build.js`
- Returns the path to the output file: `presentations/<slug>/slides.pptx`

### Step 6: Deliver

1. Show the user the `.pptx` path
2. Ask: "Also export as PDF?"
3. If yes: `libreoffice --headless --convert-to pdf --outdir presentations/<slug>/ presentations/<slug>/slides.pptx`

---

## Slide Template

A single built-in default template is used for all presentations. It is defined in `references/template.html` and provides:

- Clean sans-serif typography (Arial/Helvetica)
- Slide dimensions: `width: 720pt; height: 405pt` (16:9, matching html2pptx's LAYOUT_16x9)
- `display: flex` on body (required by html2pptx to prevent margin collapse)
- Styles for: heading, body text, bullets, callout box, table, blockquote
- White background, dark text, subtle accent color for callouts

The template CSS is inlined into each agent's prompt verbatim — agents do not need to read a file.

---

## Component → HTML Mappings

Defined in `references/component-map.md`. Each sketch component maps to an HTML pattern:

| Sketch component | HTML output |
|-----------------|-------------|
| `## Slide Title` | `<h2 class="slide-title">...</h2>` |
| `- bullet` | `<ul><li>...</li></ul>` |
| `1. item` | `<ol><li>...</li></ol>` |
| `[callout: text]` | `<div class="callout"><p>...</p></div>` |
| `[viz: name]` / `[image: path]` | `<img src="./assets/..." />` |
| `> blockquote` | `<blockquote><p>...</p></blockquote>` |
| `\| table \|` | `<table>...</table>` |
| `[notes: text]` | stripped — does not appear in HTML |
| `[diagram: description]` | `<div>` boxes + `<p>` labels (→ native PPT shapes) + PptxGenJS snippet for connectors/arrows |

---

## File Changes

### Files to delete (Marp infrastructure)

- `skills/scripts/compile_marp.sh`
- `skills/references/template.md`
- `skills/references/marp-syntax.md`

### Files to create

- `skills/references/template.html` — default slide HTML/CSS template
- `skills/references/component-map.md` — updated sketch → HTML mappings (replaces old Marp mappings)

### Files to update

- `skills/SKILL.md` — full rewrite of the build pipeline section; update sketch component table; remove Marp references
- `README.md` — update to reflect new pipeline, output formats, and removed components

---

## Invocation

`/presentation <filename>`

- No filename → ask for one
- File does not exist → create skeleton sketch at that path, tell the user to fill it in and re-run, stop
- File exists and looks like a sketch → run build pipeline
- File exists and looks like a prose spec → run spec-to-sketch conversion, stop

Skeleton file (`references/skeleton.md`) requires no changes.

---

## Dependencies

- **document-skills:pptx** — must be installed; provides html2pptx, PptxGenJS, Playwright, thumbnail.py, and LibreOffice
- **Playwright** — for per-slide HTML preview during agent refinement (via pptx skill)
- **PptxGenJS** — for native shape/connector/arrow generation in diagrams (via pptx skill)
- **html2pptx.js** — for HTML-to-pptx slide conversion (via pptx skill)
- **thumbnail.py** — for post-assembly diagram validation (via pptx skill)
- **LibreOffice** — for optional PDF export (via pptx skill)

---

## Out of Scope

- Mermaid diagram support (replaced by `[diagram:]`)
- Two-column layouts
- User-provided `.pptx` theme templates
- Multiple output themes or styles
- Iterative sketch refinement (spec-to-sketch runs once; user edits manually if needed)
- Remembering PDF export preference across runs
