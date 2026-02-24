---
name: spec
description: "Universal artifact specification skill that interviews users to produce well-defined specification documents. Covers any artifact type — software, presentations, analyses, AI skills, threat models, curricula, etc. Invoke as '/spec filename' or '/spec filename hint'. Other skills can delegate specification work by passing a hint string after the filename. Use when the user wants to spec out, define, or plan any artifact before building it."
---

# /spec — Universal Artifact Specification

Interview users to produce well-defined specification documents for any artifact.

## Invocation

`/spec <filename> [hint]`

- **No filename** → ask for one
- **File exists with content** → resumption mode (see below)
- **New file** → begin interview
- **Hint text after filename** → use as orientation for warm-up and plan (delegation from other skills)

Output is always a markdown specification document, not the artifact itself.

## Workflow

### Phase 1 — Warm-Up

1-2 orientation questions using AskUserQuestion. Always run, even with rich initial context.

- What is this artifact? Who is it for?
- What's the most important thing it needs to get right?

### Phase 2 — Interview Plan

Generate a short list of dimensions the interview will cover, tailored to this artifact type. Fully dynamic — no fixed taxonomy.

Show the plan to the user. They can add, remove, or reorder dimensions before the interview begins. Keep it to a few bullet points.

### Phase 3 — Interview

Iterative deep interview using AskUserQuestion, 1-2 questions per round. Conversational pacing — each question builds on the previous answer.

Questions must be:
- **Non-obvious** — skip things the user already told you
- **Concrete** — force tradeoff decisions, not abstract preferences
- **Deep** — probe edge cases, failure modes, unconsidered angles

Stop when coverage feels complete. No explicit completeness tracking — trust your judgment.

### Phase 4 — Write the Spec

Write two files:

1. **`<filename>`** — clean specification document. No interview metadata, no /spec noise. Readable by anyone: humans, implementation agents, other tools.

2. **`<filename>_interview_prompt.md`** — companion interview prompt. A short, artifact-specific prompt — enough for a fresh session to resume interviewing about this spec. A few lines, like the original inspiration prompt, adapted to this artifact. Not a progress tracker or dimension checklist.

Example: `/spec api_redesign.md` produces:
- `api_redesign.md` — the spec
- `api_redesign_interview_prompt.md` — the resumption prompt

### Phase 5 — Critique

Always offer after writing. User can skip.

1. **Suggest 2-4 critique angles** based on artifact type (e.g., "as a developer implementing this," "as a user encountering an error," "as a maintainer in 6 months"). User can accept, modify, add, or remove.

2. **Spawn a fresh sub-agent** using the Task tool with `subagent_type: "general-purpose"`. Construct an ad-hoc critique prompt that:
   - Includes the selected critique angles
   - Instructs the agent to read ONLY the spec file — no interview history
   - Returns findings as a list of gaps, ambiguities, and questions

3. **Present findings as AskUserQuestion prompts** — "The spec doesn't address X. Should we add a section, or is it intentionally out of scope?"

4. **Revise the spec** based on user answers.

The critique loop can repeat if the user wants another round.

## Resumption

When `/spec` opens an existing file:

1. Look for companion `<filename>_interview_prompt.md` for artifact-specific interview guidance
2. Read the spec body to understand what's been covered
3. Enter warm-up with context: "I see you have a spec for X that covers Y and Z. What would you like to refine or expand?"

## Delegation

Other skills invoke `/spec` by passing a hint: `/spec <filename> <hint text>`

Everything after the filename is the hint. Use it the same way as the user's initial description — orientation for warm-up and plan generation. The hint orients the interview; it doesn't prescribe it.

## Principles

- **Minimal scaffolding** — light structure, heavy reliance on Claude's judgment
- **Everything is an interview** — warm-up, main interview, and critique all use AskUserQuestion
- **The spec stands alone** — the critique agent sees only the file; if something isn't clear from the document alone, that's a real problem
- **Clean separation** — spec file is a clean document; interview metadata lives in the companion prompt file
