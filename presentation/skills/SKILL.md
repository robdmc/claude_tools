---
name: presentation
description: Build a presentation from a document, PPTX, or PDF. Invoke as "/presentation <filename>". Supports spec-driven refinement via /spec delegation, PPTX/PDF content extraction, skeleton creation, and full build pipeline.
---

# Presentation Skill

Build professional PPTX presentations from prose documents. Reads a document describing a presentation (spec, outline, notes, or any structured description), designs the deck holistically, generates HTML slides in parallel, and assembles a `.pptx` via `document-skills:pptx`.

## Invocation

`/presentation <filename>`

1. **No filename provided** → ask for one (unchanged)

2. **`.pptx` file** → extract content, then offer choice
   a. Extract content via `python -m markitdown <file>` → slide text as markdown
   b. Extract theme/colors via `unpack.py` + `theme1.xml` parsing (see PPTX/PDF Input below)
   c. Generate thumbnail grid for visual reference
   d. Write skeleton-structured markdown to `<basename>.md`
   e. Ask: **"Refine with spec interview?"** or **"Build now?"**
      - Spec path → delegate to `/spec` (see Spec Integration below), then continue to build pipeline
      - Build path → enter build pipeline with the extracted markdown

3. **`.pdf` file** → extract content, then offer choice
   a. Extract text via the Read tool (handles PDFs natively; use `pages` parameter for >10 pages)
   b. No style extraction — Style Notes says "No source style available — will be designed fresh."
   c. Write skeleton-structured markdown to `<basename>.md`
   d. Ask: **"Refine with spec interview?"** or **"Build now?"**
      - Spec path → delegate to `/spec`, then continue to build pipeline
      - Build path → enter build pipeline with the extracted markdown

4. **File doesn't exist** (`.md` or no extension) → offer choice
   a. Ask: **"Start with a spec interview?"** or **"Create a skeleton outline?"**
   b. Spec path → delegate to `/spec`, then continue to build pipeline
   c. Skeleton path → create from `references/skeleton.md`, then stop — user fills it in and re-runs

5. **File exists** (markdown) → offer choice
   a. Ask: **"Refine with spec interview?"** or **"Build now?"**
   b. Spec path → delegate to `/spec`, then continue to build pipeline
   c. Build path → enter build pipeline

---

## Spec Integration

When the user chooses the spec interview path, invoke:

```
/spec <filename> This spec is for a slide presentation. Angles to explore: slide-by-slide narrative flow and structure, visual style and color preferences, diagram and data visualization needs (reference available visualizations as [viz: name] where appropriate), audience and delivery context.
```

The hint text suggests four angles that produce content the build pipeline's design phase needs:
1. **Slide-by-slide structure** → produces `### Slide Title` headings
2. **Visual style/color** → feeds `## Style Notes` and the design brief
3. **Diagrams and viz** → elicits `[viz: name]` references the pipeline resolves
4. **Audience/delivery** → feeds the design brief's audience context

The spec skill is invoked as-is — it is never modified by this skill. After spec completes and the user has a refined document, the presentation skill continues to the build pipeline.

---

## PPTX/PDF Input

### PPTX Extraction

Tools (resolved via Glob under `~/.claude/`):

| Tool | Purpose | Resolution |
|------|---------|------------|
| `markitdown` | PPTX → markdown content | `python -m markitdown <file>` (pip package) |
| `unpack.py` | Extract XML for theme parsing | Glob: `**/pptx/ooxml/scripts/unpack.py` under `~/.claude/` |
| `thumbnail.py` | Visual grid of source slides | Glob: `**/pptx/scripts/thumbnail.py` under `~/.claude/` |

Sequence:
1. Resolve `unpack.py` and `thumbnail.py` via Glob (warn and continue if not found)
2. Run `python -m markitdown input.pptx` → slide text content
3. Run `unpack.py input.pptx /tmp/extract_<slug>` → read `ppt/theme/theme1.xml`
4. Parse `<a:clrScheme>` for colors (accent1–6, dk1/dk2, lt1/lt2) and `<a:fontScheme>` for fonts
5. Run `thumbnail.py input.pptx /tmp/thumbnails_<slug>` → read grid image for visual reference
6. Assemble extracted content into skeleton-structured markdown (see format below)

### PDF Extraction

1. Read PDF via the built-in Read tool (handles PDFs natively; use `pages` parameter for >10 pages)
2. No style extraction — Style Notes says "No source style available — will be designed fresh."
3. Assemble extracted content into skeleton-structured markdown (see format below)

### Extracted Content Format

Follows the skeleton structure so it works with both spec refinement and direct build:

```markdown
# [Title from source]

## Purpose
[Inferred or placeholder: "Update with presentation purpose."]

## Audience
[Inferred or placeholder: "Update with target audience."]

## Slides

### [Slide 1 Title]
[Extracted content — bullet points, text, table descriptions]

### [Slide 2 Title]
[...]

## Style Notes
[PPTX: extracted colors and fonts from theme]
[PDF: "No source style available — will be designed fresh."]
```

---

## Slug Derivation

Derived from the title `#` heading: lowercase, spaces → hyphens, non-alphanumeric (except hyphens) removed. Example: `# Customer Growth Forecasting` → `customer-growth-forecasting`. All output paths use `presentations/<slug>/`.

---

## Build Pipeline

### Step 1: Design phase

Read the full input document. Analyze it holistically to produce three outputs:

**Slide plan** — an ordered list of slide specs. For each slide:
- Slide number (0-based) and title
- Content: what text, data, or visual elements appear on the slide
- Diagram description: if the slide needs a diagram, the full description from the source document (preserve all detail — ASCII layouts, color specs, structural notes, inter-slide references). Do NOT summarize.
- Asset references: any images to embed. Resolve paths relative to the input file's directory.
- Notes: speaker notes (stripped from visible slide content)

**Design brief** — shared context for all slide agents:
- Color palette: primary, secondary, and accent colors. Extract from the document's style notes if present; otherwise choose a cohesive palette appropriate to the subject matter.
- Style rules: text density preferences, diagram style, terminology consistency, any presentation principles stated in the document.
- Audience context: who the presentation is for, what level of complexity is appropriate.
- Cross-slide consistency notes: color coding conventions (e.g., "blue = monthly plan throughout"), recurring visual motifs, terminology definitions.

**Customized template** — take the base template (see **Slide Template** below) and replace the default accent color (`#4472C4`) with the primary color from the design brief. Adjust `.callout` border color, `th` background, and any other accent uses. This produces a deck-specific template that all slide agents share.

### Step 2: Resolve assets

- Resolve image paths from the slide plan. Paths in the source document are relative to the input file's directory — resolve them to absolute paths, then copy to `presentations/<slug>/assets/`.
- If the document references `[viz: name]` patterns, fuzzy-match against `.viz/*.png`; if ambiguous, list matches and ask; if no match, warn and omit (build continues).
- If `.viz/` does not exist and the document references viz embeds, warn and skip.

### Step 3: Generate all slides in parallel

Spawn a Task agent for **every** slide (`subagent_type: general-purpose`, `model: sonnet`). **CRITICAL: Launch ALL slide agents in a single message containing multiple Task tool calls. Do NOT spawn them one at a time across separate messages.**

Each agent receives:
- Its slide spec from the slide plan (title, content, diagram description, asset references, notes)
- The slide index `n` (0-based)
- The presentation slug and assets path (`presentations/<slug>/assets/`)
- The design brief (color palette, style rules, audience context, cross-slide consistency notes)
- The customized HTML/CSS template, inlined verbatim
- The html2pptx constraints (see **html2pptx Constraints** below), inlined verbatim
- The Playwright preview script (see workflow step 3 below)
- The slide element patterns from `references/component-map.md`, inlined verbatim
- Instruction to follow the per-slide workflow below

Each agent's workflow:
1. **Generate HTML** — Translate the slide spec into a complete HTML slide document (full `<html>` with customized template CSS in `<head>`, slide content in `<body>`). Follow all html2pptx constraints strictly. Follow the design brief for color usage, style, and audience-appropriate complexity. Dimensions: `width: 720pt; height: 405pt`. If the slide has a diagram, render boxes/labels/backgrounds as `<div>` elements with all text wrapped in `<p>` tags. Strip notes content — it does not appear on the slide. Image paths use `./assets/<filename>`.
2. **Generate diagram snippet** — If the slide contains a diagram, also produce a PptxGenJS code snippet for connectors, arrows, and lines. The snippet operates on a variable named `slide` (the object returned by `html2pptx`). **Colors must omit the `#` prefix** — use `"4C72B0"` not `"#4C72B0"` (incorrect format corrupts the file). Example: `slide.addShape(pptx.ShapeType.rightArrow, { x: 2, y: 1.5, w: 1, h: 0.5, fill: { color: "4C72B0" } });`
3. **Preview** — Write the HTML to `presentations/<slug>/slides/slide-<n>.html`, then screenshot it by writing and running this Node.js script:
   ```javascript
   const { chromium } = require('playwright');
   (async () => {
     const browser = await chromium.launch();
     const page = await browser.newPage();
     await page.setViewportSize({ width: 960, height: 540 });
     await page.goto('file://' + require('path').resolve(process.argv[2]));
     await page.screenshot({ path: process.argv[3] });
     await browser.close();
   })();
   // Run: node preview.js <html-path> <png-path>
   ```
   The 960×540 viewport matches 720pt × 405pt at screen resolution (1pt = 4/3 px). Inspect the PNG for text overflow, clipping, and layout problems. **PptxGenJS connector/arrow shapes from diagrams are not visible in this preview** — they are added post-conversion and validated after assembly.
4. **Refine** — If the preview shows problems in the HTML portion, adjust and re-preview (up to 2 refinement passes).
5. **Return** — Return: (a) the path to the final HTML file at `presentations/<slug>/slides/slide-<n>.html`, and (b) the PptxGenJS diagram snippet string if applicable (or `null`).

**Agent failure:** If an agent fails or returns malformed output, re-spawn a single replacement agent for that slide with the same inputs. If the retry also fails, abort the build and report which slide failed.

Collect all results in slide order before proceeding.

### Step 4: Resolve pptx skill paths and assemble `build.js`

Before writing `build.js`, resolve paths to `html2pptx.js` and `thumbnail.py` from the installed `document-skills:pptx` skill:

```
Glob pattern: "**/pptx/scripts/html2pptx.js" under ~/.claude/
Glob pattern: "**/pptx/scripts/thumbnail.py"  under ~/.claude/
```

If either file is not found, abort and tell the user: "document-skills:pptx is required but html2pptx.js / thumbnail.py was not found. Install the pptx skill first."

Write `presentations/<slug>/build.js` with the resolved `html2pptx.js` **absolute path** baked in. This file runs from `presentations/<slug>/` (all relative paths are relative to it):

```javascript
const pptxgen = require('pptxgenjs');
const html2pptx = require('/absolute/path/to/html2pptx.js');  // resolved absolute path

const pptx = new pptxgen();
pptx.layout = 'LAYOUT_16x9';

(async () => {
  // Slide 0
  const { slide: slide0 } = await html2pptx('slides/slide-0.html', pptx);
  // [diagram snippet for slide 0, if present]

  // Slide 1
  const { slide: slide1 } = await html2pptx('slides/slide-1.html', pptx);
  // [diagram snippet for slide 1, if present]

  // ... repeat for all slides

  await pptx.writeFile({ fileName: 'slides.pptx' });
})();
```

Notes content is stripped from HTML by agents (step 3.1) — no additional strip step needed in `build.js`.

### Step 5: Execute and validate

Spawn a Task agent (`subagent_type: general-purpose`, `model: sonnet`) with these explicit inputs:
- The absolute path to `build.js`: `presentations/<slug>/build.js`
- The absolute path to `thumbnail.py` (resolved in Step 4)
- The `presentations/<slug>/` directory path

The sub-agent's workflow:
1. **Build**: `cd presentations/<slug> && node build.js`
2. **Generate thumbnail grid**: `python <thumbnail.py absolute path> presentations/<slug>/slides.pptx presentations/<slug>/thumbnails`
3. **Inspect** the thumbnail grid for layout issues — especially connector/arrow placement in diagram slides (this is the first time those elements are visible)
4. **If diagram issues are found**: edit the relevant PptxGenJS snippets in `build.js`, re-run `node build.js`, and re-generate thumbnails. **Limit: 1 rebuild pass.**
5. **Return** the path to the final output: `presentations/<slug>/slides.pptx`

### Step 6: Deliver

1. Show the user the `.pptx` path
2. Ask: "Also export as PDF?"
3. If yes: `libreoffice --headless --convert-to pdf --outdir presentations/<slug>/ presentations/<slug>/slides.pptx`

---

## Slide Template

This is the base template. During the design phase (Step 1), the default accent color (`#4472C4`) is replaced with the primary color from the design brief. The customized template is then inlined verbatim into each slide agent's prompt.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      display: flex;
      flex-direction: column;
      width: 720pt;
      height: 405pt;
      padding: 36pt 48pt;
      font-family: Arial, Helvetica, sans-serif;
      font-size: 18pt;
      color: #1a1a1a;
      background: #ffffff;
      overflow: hidden;
    }
    .slide-title { font-size: 28pt; font-weight: bold; color: #1a1a1a; margin-bottom: 20pt; line-height: 1.2; }
    p { font-size: 18pt; line-height: 1.5; margin-bottom: 8pt; }
    ul, ol { padding-left: 24pt; margin-bottom: 12pt; }
    li { font-size: 18pt; line-height: 1.5; margin-bottom: 6pt; }
    .callout { background: #f0f4ff; border-left: 4pt solid #4472C4; padding: 16pt 20pt; margin: 16pt 0; border-radius: 4pt; }
    .callout p { font-size: 20pt; font-weight: 600; color: #2c3e50; margin: 0; }
    table { border-collapse: collapse; width: 100%; margin: 12pt 0; }
    th, td { border: 1pt solid #d0d0d0; padding: 8pt 12pt; text-align: left; font-size: 15pt; }
    th { background: #4472C4; color: white; font-weight: bold; }
    tr:nth-child(even) { background: #f5f7fa; }
    blockquote { border-left: 4pt solid #888; padding: 8pt 16pt; margin: 12pt 0; font-style: italic; color: #444; }
    blockquote p { font-size: 18pt; }
    img { max-width: 100%; max-height: 280pt; object-fit: contain; }
  </style>
</head>
<body>
  <!-- slide content goes here -->
</body>
</html>
```

The canonical base template is also saved at `{SKILL_DIR}/references/template.html`.

---

## html2pptx Constraints

Inline these rules verbatim into each slide agent's prompt alongside the template. html2pptx.js validates these strictly — violations cause build failures.

- **No CSS gradients** — rasterize to a PNG background image if needed
- **No backgrounds, borders, or shadows on text elements** (`<p>`, `<h1>`-`<h6>`, `<span>`, etc.) — only on `<div>` elements (which become PowerPoint shapes)
- **No unwrapped text in `<div>`** — all text must be in `<p>`, `<h1>`-`<h6>`, `<ul>`, or `<ol>` tags
- **No inline margins on `<b>`, `<i>`, `<u>`, `<span>`** — not supported in PowerPoint
- **No manual bullet symbols** (like `•` or `–`) — use `<ul>`/`<ol>` instead
- **Web-safe fonts only** — Arial, Helvetica, Times New Roman, Georgia, Courier New, Verdana, Tahoma, Trebuchet MS, Impact, Comic Sans MS
- **PptxGenJS color values: no `#` prefix** — use `"4472C4"` not `"#4472C4"` (incorrect format corrupts the output file)

---

## References

- `references/skeleton.md` — Template used when creating a new presentation outline (also the target format for PPTX/PDF extraction)
- `references/component-map.md` — HTML patterns for common slide elements
- `references/template.html` — Base slide HTML/CSS template (customized per-deck in design phase)
- **Spec skill** — Used for spec-driven refinement when user chooses the interview path (`/spec <filename> <hint>`)
