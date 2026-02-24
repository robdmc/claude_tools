# Spec

A universal artifact specification skill that interviews users to produce well-defined specification documents. Covers any artifact type — software, presentations, analyses, AI skills, threat models, curricula, etc.

## Usage

```
/spec <filename>            # Start a new spec
/spec <filename> <hint>     # Start with orientation context
/spec <existing_file>       # Resume/refine an existing spec
```

## How It Works

Spec runs a structured interview using AskUserQuestion to extract requirements, constraints, and design decisions. The interview is fully dynamic — questions are tailored to the artifact type, not drawn from a fixed template.

### Phases

1. **Warm-Up** — 1-2 orientation questions to understand the artifact and audience
2. **Interview Plan** — A short list of dimensions to cover, shown for user approval
3. **Interview** — Iterative deep-dive, 1-2 questions per round
4. **Write** — Produces a clean spec document and a companion interview prompt
5. **Critique** — Optional review by a fresh sub-agent that reads only the spec

## Output

Each spec produces two files:

| File | Purpose |
|------|---------|
| `<filename>` | Clean specification document, readable by anyone |
| `<filename>_interview_prompt.md` | Companion prompt for resuming the interview later |

## Delegation

Other skills can delegate specification work by passing a hint string:

```
/spec api_redesign.md "REST API for the billing service"
```

The hint orients the interview but doesn't constrain it.

## Installation

Use the `/install` command from the claude_tools repository:

```
/install
```
