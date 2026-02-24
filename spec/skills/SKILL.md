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
- **Hint text after filename** → use as orientation for warm-up (delegation from other skills)

Output is always a markdown specification document, not the artifact itself.

## The Interview Prompt

The heart of this skill is adapting a proven interview prompt to the user's specific domain. The inspiration:

> Read this spec and interview me in detail using AskUserQuestion about literally anything: technical implementation, UI & UX, concerns, tradeoffs, etc. but make sure the questions are not obvious. Be very in-depth and continue interviewing me continually until it's complete, then write the spec to the file.

That prompt works great for software. The job of Phase 1 is to figure out what the equivalent angles are for whatever the user actually wants to spec — a presentation, a curriculum, a threat model, anything — and write those as the companion interview prompt file.

## Workflow

### Phase 1 — Build the Interview Prompt

1-2 orientation questions using AskUserQuestion to understand the artifact and domain.

Then write `<filename>_interview_prompt.md` — a short, direct prompt that tells Claude how to interview for this specific artifact. It names the artifact, the key angles to probe (as suggestions, not limitations), and sets the tone. Keep it tight — a paragraph or two. Claude is smart; the prompt just needs to point it in the right direction.

Example for a data pipeline presentation:

> Interview me in detail about a Marp presentation explaining a forecasting pipeline to a technical audience. Probe narrative structure, how to present statistical models without losing the audience, diagram design, level of mathematical rigor, tradeoffs between completeness and slide count, what the audience must walk away understanding. Questions should be non-obvious and force real decisions.

Example for a threat model:

> Interview me in detail about a threat model for a patient-facing telehealth API. Probe attack surfaces, trust boundaries, data classification, authentication edge cases, third-party integration risks, incident response assumptions. Push on what I'm hand-waving.

This file is the primary output of Phase 1. If the session dies here, a fresh session can pick it up and run a good interview.

### Phase 2 — Interview

Run the interview prompt you just wrote. Use AskUserQuestion, 1-2 questions per round. The angles in the prompt are suggestions — follow the conversation wherever it leads. Probe deep, skip the obvious, force tradeoffs.

Stop when coverage feels complete. Trust your judgment.

### Phase 3 — Write the Spec

Write **`<filename>`** — clean specification document. No interview metadata, no /spec noise. Readable by anyone: humans, implementation agents, other tools.

Example: `/spec api_redesign.md` produces:
- `api_redesign.md` — the spec
- `api_redesign_interview_prompt.md` — the interview prompt

### Phase 4 — Critique

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

1. Look for companion `<filename>_interview_prompt.md` — this is your interview playbook, use it
2. Read the spec body to understand what's been covered
3. Ask what to refine or expand, then resume interviewing using the prompt's angles

## Delegation

Other skills invoke `/spec` by passing a hint: `/spec <filename> <hint text>`

Everything after the filename is the hint. Use it as orientation when building the interview prompt in Phase 1.

## Principles

- **The interview prompt is the skill** — Phase 1 adapts a generic "interview me deeply" prompt to the user's domain. Everything flows from that.
- **Angles are suggestions, not limitations** — the prompt names dimensions to explore, but the conversation leads. Follow it.
- **Minimal scaffolding** — Claude is smart. The prompt just points it in the right direction.
- **The spec stands alone** — the critique agent sees only the file; if something isn't clear from the document alone, that's a real problem.
- **Clean separation** — spec file is a clean document; the interview prompt is reusable interview instructions, not a decisions log.
