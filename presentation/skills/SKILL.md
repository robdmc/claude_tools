---
name: presentation
description: Build a Marp presentation from a sketch file. Invoke as "/presentation <filename>". If no filename is given, ask for one. If the file does not exist, create a skeleton sketch at that path. If the file exists, build and compile the presentation from it.
---

# Presentation Skill

Build professional Marp presentations from a structured sketch file.

## Invocation

`/presentation <filename>`

- **No filename provided** → ask for one
- **File does not exist** → create a skeleton sketch at that path (use `references/skeleton.md` as the template), then stop — user fills it in and re-runs
- **File exists** → build the presentation from the sketch

## Sketch Format

Standard markdown plus custom tags:

| Component | Syntax |
|-----------|--------|
| Title | `# Title` — first `#` heading; becomes presentation title and slug |
| Slide | `## Slide Title` — each `##` is one slide |
| Bullets | `- text` |
| Numbered list | `1. text` |
| Viz embed | `[viz: name]` — fuzzy-match against `.viz/*.png` (no extension needed) |
| Image | `[image: path]` — any local image path, referenced in-place |
| Callout box | `[callout: text]` — highlighted box for key stats or quotes |
| Two-column | `[two-col]` ... `[---]` ... `[/two-col]` |
| Table | standard markdown pipe table |
| Block quote | `> text` |
| Speaker notes | `[notes: text]` — hidden from audience |

See `references/component-map.md` for exactly how each component renders in Marp.

## Building the Presentation

1. Parse sketch top-to-bottom
2. Map each component to Marp markdown per `references/component-map.md`
3. Resolve `[viz: name]` — fuzzy-match against `.viz/*.png`; if ambiguous, list matches and ask before proceeding
4. Copy all resolved images to `presentations/<slug>/assets/`
5. Write `presentations/<slug>/slides.md` using the CSS from `references/template.md`
6. Compile: `{SKILL_DIR}/scripts/compile_marp.sh <slug> pdf`

Output: `presentations/<slug>/slides.pdf`

## References

- `references/skeleton.md` — Template used when creating a new sketch file
- `references/component-map.md` — Sketch component → Marp markdown mappings
- `references/template.md` — Standard CSS template for slides.md
- `references/marp-syntax.md` — Full Marp syntax reference
- `references/chart-styling.md` — Matplotlib graph styling for viz outputs
