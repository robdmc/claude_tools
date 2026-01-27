# Presentation Skill Development Guide

Instructions for Claude sessions working on this skill.

## Before Making Changes

1. **Invoke the skill-creator skill** for guidance on skill development best practices:
   ```
   /document-skills:skill-creator
   ```

2. **Read the current skill files** to understand the existing structure:
   - `skills/SKILL.md` - Main skill definition (Claude reads this)
   - `skills/references/workflows.md` - Detailed workflow examples
   - `skills/references/marp-syntax.md` - Marp syntax reference
   - `skills/references/chart-styling.md` - Graph styling guidelines
   - `skills/scripts/compile_marp.sh` - Compilation script

## Skill Architecture

```
presentation/
├── README.md                       # Human documentation
├── CLAUDE.md                       # This file - development instructions
└── skills/
    ├── SKILL.md                    # Main skill definition (required)
    ├── scripts/
    │   └── compile_marp.sh         # Marp compilation wrapper
    └── references/
        ├── workflows.md            # Detailed workflow documentation
        ├── marp-syntax.md          # Marp syntax reference
        └── chart-styling.md        # Matplotlib styling for graphs
```

## Key Design Decisions

These decisions were made intentionally - preserve them unless explicitly changing:

- **Terminology**: User says "chart" for slides, "graph" for visualizations
- **Location**: All presentations in `presentations/` folder at project root
- **Self-contained**: Each presentation has its own `assets/` directory
- **Viz integration**: Copy images from `.viz/` into `assets/` for portability
- **Slide reference**: By title (more stable than numbers)
- **Blank canvas**: Title-only slides when creating from outline
- **CSS**: Embedded in each presentation's frontmatter (self-contained)
- **Context tracking**: Skill infers active presentation and focused slide from conversation

## Making Changes

### Updating SKILL.md

This is what Claude reads when the skill is triggered. Keep it:
- Concise but complete
- Focused on "what Claude needs to do"
- Well-organized with clear sections

### Updating references/

These provide detailed examples and reference material:
- `workflows.md` - Add new workflow examples here
- `marp-syntax.md` - Marp-specific syntax details
- `chart-styling.md` - Matplotlib styling for presentation graphs

### Updating scripts/

The `compile_marp.sh` script:
- Accepts presentation slug as first argument
- Compiles from `presentations/<slug>/slides.md`
- Outputs to same directory

## Updating README.md

After making changes to the skill, update `README.md` to reflect those changes. The README is for humans and should:

1. Explain what the skill does in plain language
2. Show the project structure
3. Provide quick start examples
4. Document all three workflows with user-facing examples
5. List available commands/operations
6. Include troubleshooting tips

Keep the README in sync with SKILL.md - if you change functionality in SKILL.md, update the corresponding section in README.md.

## Testing Changes

After modifying the skill:

1. Create a test presentation using the blank canvas workflow
2. Add content to individual slides
3. Import a viz graph and verify it copies to assets/
4. Compile to PDF and verify output
5. Test context inference (focus shifting, active deck)
6. Test the context synthesis workflow

## Integration Points

This skill integrates with:

- **Viz skill**: Outputs to `.viz/`, presentation copies to `assets/`
- **Scribe skill**: Notes in `.scribe/` can be source material for context synthesis

When modifying integration behavior, consider impacts on these skills.
