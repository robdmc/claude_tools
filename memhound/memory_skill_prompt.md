# Handoff: Corpus Navigation Skill v1 — Interview and Spec Generation

## What this document is

You (Claude Code) are being handed off from a design conversation that happened in Claude.ai. The user has designed a corpus navigation system across an extensive conversation and now wants to build the first implementation as a Claude Code skill.

Your job is to:

1. Read this document for context on what's been designed
2. Interview the user to fill in the implementation details that weren't settled in the design conversation
3. Produce a concrete spec markdown file (`skill-spec.md`) that defines how the skill should be built
4. After the spec is written, the user will direct you to actually build the skill

This is **specification work**, not implementation work. Don't start building the skill until the spec is complete and the user has confirmed it.

---

## Context from the design conversation

### What the system is

A corpus navigation substrate that lets an agent answer questions about a collection of documents by decomposing them into atomic, decontextualized **Notes** and navigating those Notes via a grep-like iterative loop (specifically: the way Claude uses the grep tool in Claude Code to navigate codebases — iteratively, with each query informing the next, reading source when needed).

### The Note schema (settled)

```
Note
├── id
├── text                  decontextualized, self-contained content
├── kind                  thesis | claim | decision | proposal | question |
│                         task | constraint | spec | reference | note | 
│                         document_summary
├── nouns                 list of noun phrases (entities and concepts)
├── prior_refs            list of note_ids (optional)
├── source_refs           list of source locations
│   └── each entry:
│       ├── document_id
│       └── paragraph_range
└── document_metadata
    ├── document_title
    ├── document_kind
    ├── date
    └── author
```

Key properties:
- `text` is aggressively decontextualized — pronouns resolved, proper nouns pulled in, self-contained
- `nouns` are noun phrases (entities AND concepts like "the migration plan"), not just proper nouns
- `kind` values map to specific query patterns
- `prior_refs` captures explicit cross-references the extractor saw in the source
- `source_refs` is a list to support document_summary Notes that span a whole document

### The ingestion pipeline (settled in shape, needs detail)

1. Segment document by structural boundaries (fall back to paragraph clusters)
2. Extract Notes from each segment via LLM call with a carefully crafted prompt
3. Extract nouns in a unified pass across all Notes from a document
4. Produce a document_summary Note for the whole document
5. Index

### The retrieval primitives (settled)

- `find(text, nouns, filters, limit)` — hybrid search returning hits with total_count
- `fetch(source_ref)` — read source text for a specific location

### The agent navigation pattern (settled)

Grep-loop style: start broad, narrow with filters based on what appears, fetch source when something looks promising, iterate. The agent drives with its own reasoning; the substrate stays simple and fast.

### What's in v1 scope

- Ingesting documents into Notes
- Answering questions by navigating the Notes
- A user-triggered introspection feature that captures suggestions for improving the system (schema gaps, extraction issues, retrieval patterns that felt awkward)
- Reviewing accumulated introspections to identify patterns

### What's out of scope for v1

- Question-Notes that capture prior queries and their answers (this is v2)
- Automatic discovery of cross-Note links beyond what's explicit in sources
- Grouping abstractions
- Agent reasoning storage beyond the narrow introspection mechanism
- Access control

### Important design principles

- **Simplicity in the substrate.** Complexity lives in the agent's reasoning and the extraction prompt, not in the schema or primitives.
- **Decontextualization is load-bearing.** The whole system's quality depends on `text` being self-contained enough that answers live in Note text.
- **Source grounding always.** Every Note traces back to source that can be fetched and read.
- **The extraction prompt is the single biggest quality lever.** Most v1 effort goes into getting it right.

### Why this is being built as a Claude Code skill first

The user wants to validate the design at small scale before committing to a production implementation. Claude Code provides:
- File-based storage (Notes as files, inspectable via `ls` and `cat`)
- Claude's reasoning as the navigation agent (grep loop via Claude's own tool use)
- No backend infrastructure needed
- Tight iteration loop for extraction prompt tuning

At personal-corpus scale (hundreds to low thousands of Notes), grep-based navigation by Claude is adequate. Beyond that scale, a proper retrieval substrate would be needed, but that's future work.

---

## Your task: interview the user and produce a spec

### Interview approach

Ask questions **one topic at a time**. Don't dump all questions at once — work through them in conversation. Group related questions together, but let the user answer and refine before moving to the next topic.

If the user says "use your judgment" or "I don't care" for some question, note that in the spec and move on. If a question turns out to depend on an earlier answer, skip ahead or circle back as needed.

The questions below are organized by topic. Move through them in roughly this order, but adapt based on the user's answers.

### Questions to work through

#### Topic 1: The reference project (START HERE)

1. What is the reference project? The user will point you at it. Ask what it is in general (another skill? a template? docs?) and what specifically they want this skill to inherit from it — Python environment handling was mentioned, but ask about SKILL.md conventions, file organization, naming patterns, and how scripts get invoked.

2. Should you read the reference project before continuing the interview? (Probably yes, once you know where it is.)

#### Topic 2: The target corpus

3. What corpus will this skill operate on first? (Personal notes, a specific document collection, something else?)
4. What file types are in it? (Markdown, PDF, DOCX, mixed?)
5. Rough scale? (Tens, hundreds, thousands of documents?)
6. Where does the corpus live? (Directory structure, single vs multiple locations)
7. Does the corpus persist across Claude Code sessions, or is it per-session?

#### Topic 3: Scope and invocation

8. Which capabilities are in v1? Confirm: ingest, navigate, introspect, review introspections. Anything deferred?
9. How are capabilities invoked? Natural language only? Specific commands? A mix?
10. Is ingestion explicit (user asks) or automatic (skill notices new documents)?

#### Topic 4: Note storage format

11. File format for Notes? (YAML frontmatter + markdown body was the default assumption — confirm or adjust.)
12. File naming convention? (Sequential IDs, content-based, human-readable derivation?)
13. How are Notes organized on disk? (Flat directory, by source document, by date?)
14. Is there a separate index file, or is everything derived from scanning Notes?

#### Topic 5: Extraction process

15. Does extraction happen in one invocation or incrementally across sessions?
16. Where does Python come in? (Document parsing? File ops? Orchestrating the extraction calls?)
17. How does extraction fail gracefully? (Skip + log? Retry? Minimal fallback Note?)
18. How is the extraction prompt organized? (Single big file in the skill? Multiple files?)

#### Topic 6: Navigation and queries

19. How does the skill know to activate when a question comes in? (Always loaded in corpus-work sessions? Triggered by question content?)
20. Output format for answers? (Natural prose, explicit citations, what level of provenance?)
21. Should the skill narrate its process? ("I searched for X, found Y..." — always? optional? never?)
22. Explicit commands or natural language only?

#### Topic 7: Introspection

23. Trigger mechanism? (Specific phrase like "introspect," natural language like "what would have made that easier," or both?)
24. What does introspection look at? (Most recent query, a pointed-at query, session-wide patterns?)
25. How are introspections stored? (One file per introspection, appended to a log, something else?)
26. Is pattern detection across introspections automatic or a separate review command?

#### Topic 8: Skill structure and conventions

27. SKILL.md structural conventions from the reference project?
28. File naming conventions (dashes vs underscores, extensions, casing)?
29. Self-contained or allowed to depend on external Python libraries?

#### Topic 9: Polish and naming

30. How polished does v1 need to be? (Personal use vs shareable?)
31. Anything from the design you want to revisit now that it's getting concrete?
32. Skill name?

### What to produce

After the interview, write a file called `skill-spec.md` in the user's project directory (or wherever they direct you). The spec should contain:

1. **Overview** — what the skill does, in one or two paragraphs
2. **Reference project** — what the user pointed you at and what's being inherited
3. **Corpus assumptions** — where it lives, what file types, scale expectations
4. **Directory layout** — where the skill puts Notes, introspections, logs, etc.
5. **Note schema** — the full schema as files, with format specifics (YAML+markdown, naming, organization)
6. **Ingestion pipeline** — step-by-step what happens when documents are ingested, including what Python does vs what Claude does, and the extraction prompt strategy
7. **Navigation pattern** — how Claude answers questions using the grep-loop, how the skill activates, output format
8. **Introspection feature** — trigger mechanism, what gets captured, storage format, review mechanism
9. **Skill file organization** — what files are in the skill, what each contains
10. **Activation conditions** — what goes in SKILL.md's description to make Claude load it correctly
11. **Open questions / deferred decisions** — anything the user explicitly deferred or that will need iteration
12. **Explicit non-goals** — things the skill won't do in v1, to prevent scope creep

The spec should be concrete enough that building the skill is clearly-scoped work, not another design problem.

### After the spec is done

Confirm with the user that the spec captures their intent. Offer to refine it. Only move to implementation after they approve.

---

## One more note

The design conversation that produced this context was long and iterative. If the user mentions something that seems to contradict what's in this document, **trust the user** — they have the latest context. This document is a faithful summary but may not capture every nuance of what they decided.

Also: the user is thoughtful and will push back on assumptions. If they ask you to justify something, it's because they want the reasoning made explicit, not because you're wrong. Engage with the reasoning.

Good luck. Start by asking about the reference project.
