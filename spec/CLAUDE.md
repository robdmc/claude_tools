# Spec Skill Development Guide

Instructions for Claude sessions working on this skill.

## Before Making Changes

1. **Invoke the skill-creator skill** for guidance on skill development best practices:
   ```
   /skill-creator
   ```

2. **Read the current skill files** to understand the existing structure:
   - `skills/SKILL.md` - Main skill definition (Claude reads this)

## Skill Architecture

```
spec/
├── README.md              # Human documentation
├── CLAUDE.md              # This file - development instructions
└── skills/
    └── SKILL.md           # Skill definition for Claude
```

## Key Design Decisions

These decisions were made intentionally — preserve them unless explicitly changing:

- **Pure interview skill**: No scripts, no runners, no code generation. The skill's only output is markdown specification documents.
- **Fully dynamic interview**: Questions are generated based on the artifact type, not drawn from a fixed taxonomy or checklist. No hardcoded dimensions.
- **AskUserQuestion throughout**: Warm-up, interview, and critique all use AskUserQuestion. This is the skill's primary interaction mechanism.
- **Clean spec separation**: The spec file is a standalone document with no interview metadata. Anyone (human or agent) should be able to read it without context about the interview process.
- **Companion prompt file**: Interview resumption context lives in `<filename>_interview_prompt.md`, not in the spec itself. This keeps the spec clean while enabling resumption.
- **Critique via fresh sub-agent**: The critique agent reads only the spec file — no interview history. If something isn't clear from the document alone, that's a real gap.
- **Lean SKILL.md**: The skill has no scripts or references. All behavior is defined in SKILL.md. If the skill grows complex enough to need references, factor them out then.

## Making Changes

### SKILL.md changes

The entire skill logic lives in SKILL.md. Changes here affect the interview flow, output format, and critique process. Keep it focused on workflow and principles — avoid prescribing specific questions or dimensions.

### Adding references

If the skill grows to need detailed guidance (e.g., spec templates for common artifact types, critique angle libraries), create `skills/references/` and move that content there. Keep SKILL.md as the lean orchestration layer.

## Testing Changes

No dedicated test suite. Test by running the skill end-to-end:

1. Invoke `/spec test_spec.md` and complete a short interview
2. Verify the output spec is clean and self-contained
3. Verify the companion prompt file enables meaningful resumption
4. Test resumption by invoking `/spec test_spec.md` on the existing file
5. Test delegation by invoking `/spec test_spec.md "some hint text"`

## Integration Points

- **Invocation**: Users invoke directly with `/spec`, or other skills delegate via `/spec <filename> <hint>`
- **Output**: Produces markdown files in the user's working directory
- **No external dependencies**: The skill uses only AskUserQuestion and the Task tool (for critique sub-agents)
