# Brainstorm Skill

A general-purpose Socratic brainstorm skill combining research-backed techniques from IDEO, HBR, and cognitive science.

## Trigger

This skill activates when:
- User invokes `/brainstorm`
- User says "help me brainstorm", "let's brainstorm", or similar
- User is exploring ideas, decisions, or creative challenges

## Context Awareness

**Scan recent context efficiently, don't process everything.**

Priority order for finding the brainstorm topic:
1. **Explicit prompt**: If user says `/brainstorm [topic]`, use that directly
2. **Last 3-5 messages**: Check recent exchanges for an obvious topic
3. **When unclear, ask**: "I see we've discussed [X] and [Y]. Which would you like to brainstorm, or something else?"

**Rules:**
- Don't summarize the entire conversation - just identify the likely topic
- If multiple plausible topics exist, ask the user to pick (use AskUserQuestion)
- If the topic is clear from recent messages, confirm briefly: "Brainstorming [topic] - sound right?" and proceed
- Skip questions already answered in context, but don't dig through long histories to find them

**Starting point heuristics:**
| Context State | Action |
|---------------|--------|
| `/brainstorm [topic]` provided | Start Phase 1 with that topic |
| Clear topic in last few messages | Confirm and start Phase 1 |
| Multiple recent topics | Ask user to pick one |
| No clear topic / long divergent chat | Ask "What would you like to brainstorm?" |

## Core Principles

1. **Question-first approach** - Better questions unlock better answers
2. **Defer judgment** - No critiquing during divergent phase; use "and" not "but"
3. **Encourage wild ideas** - Wild ideas spark creative leaps
4. **Divergent then convergent** - Generate many options first, then narrow down
5. **Socratic questioning** - Surface assumptions and explore implications

## Four-Phase Process

### Phase 1: Frame the Challenge

Start by understanding the challenge clearly:

1. Ask the user to state their challenge or idea in one sentence
2. Reframe using "How might we...?" to open possibilities
3. Clarify success criteria: "What does success look like?"
4. Identify constraints: "What are the boundaries or limitations?"

**Rules for Phase 1:**
- Ask ONE question at a time
- Prefer multiple-choice options when feasible (reduces cognitive load)
- Use AskUserQuestion tool for structured choices
- Don't move forward until the challenge is clearly framed

### Phase 2: Diverge - Generate Possibilities

This is where AI excels. Generate many options freely:

1. **Defer ALL judgment** - Never say "but", only "and"
2. **Go for quantity** - Generate 8-15 ideas minimum, including wild ones
3. **Number all ideas** for easy reference (idea #1, idea #2, etc.)
4. **Use Socratic probes** to surface hidden assumptions:
   - "What are you assuming here?"
   - "What if that weren't true?"
   - "What would happen if...?"
5. **Build on each idea** before moving to the next
6. **Don't rush to Phase 3** - Dwell in divergence; more raw material means better outcomes
7. **Always invite user contribution** before converging - their ideas matter

**Optional: Parallel Perspective Agents**

When the user requests "diverse perspectives", "different viewpoints", or "multiple angles", spawn three parallel agents using the Task tool:

| Agent | File | Focus |
|-------|------|-------|
| Pragmatic Explorer | `{AGENTS_DIR}/pragmatic-explorer.md` | Practical, implementable approaches |
| Creative Challenger | `{AGENTS_DIR}/creative-challenger.md` | Wild, unconventional "what if" ideas |
| Devil's Advocate | `{AGENTS_DIR}/devils-advocate.md` | Failure modes, hidden assumptions |

To spawn agents, use the Task tool with `subagent_type: "general-purpose"` and include the agent's instructions from their respective files in the prompt. Run all three in parallel for efficiency.

After agents return, synthesize the best ideas from all three perspectives.

**Collaborative Ideation Loop**

After generating initial ideas (and optionally gathering agent perspectives), shift into collaborative mode. The user has domain knowledge and creative instincts - draw them out.

**The Loop:**
1. Present your ideas (numbered for reference)
2. Invite contribution: "What does this spark for you? Any ideas from your experience?"
3. When user shares an idea, respond with ONE of:
   - **Riff**: "Building on that - what if we also [variation]?"
   - **Callback**: "That connects nicely with idea #3 - together they could [synthesis]"
   - **Synthesis**: "Combining your idea with the earlier ones, I see a pattern: [new framing]"
4. After responding, invite again: "What else? Or shall we start narrowing down?"

**Rules for the loop:**
- Stay in divergence mode - no critiquing, no "but"
- Match the user's energy - if they're generating freely, keep pace
- Reference ideas by number to build connections
- Offer to summarize the idea pool periodically ("We have 12 ideas now - want a quick recap?")
- Only exit when user explicitly signals readiness ("let's narrow down", "I think we have enough", etc.)

**Prompts to invite contribution:**
- "What ideas does this spark for you?"
- "Any approaches you've seen work in similar situations?"
- "What would you try if resources weren't a constraint?"
- "Is there an angle we haven't explored yet?"

**Example exchange:**
```
Claude: [Presents 8 initial ideas, numbered #1-#8]
        What does this spark for you? Any ideas from your experience?

User: What about partnering with universities? They have research capacity.

Claude: Nice - that opens up a whole channel. Riffing on that: what if we
        structured it as a sponsored research program where we get first
        access to findings? That pairs with idea #4 (the pilot program) -
        universities could be the pilot cohort. That's idea #9.

        What else comes to mind? Or ready to start narrowing?

User: I like the university angle. What about community colleges too?

Claude: Yes - community colleges have workforce development mandates, so
        there's built-in alignment. And they're often more agile than
        research universities. That's idea #10 now.

        We're at 10 ideas. Want a quick recap, or keep going?

User: Let's narrow down.

Claude: [Moves to Phase 3]
```

### Phase 3: Converge - Evaluate & Select

This is where human judgment excels. Help the user choose:

1. **Present 2-4 strongest options** with clear trade-offs
2. **Lead with your recommended option** and explain the rationale
3. Ask: "Which resonates with you? What's missing?"
4. Apply YAGNI: "What's the simplest version that would work?"

**Present options using AskUserQuestion** when possible, with:
- Clear labels for each option
- Brief description of trade-offs
- Your recommendation marked as "(Recommended)"

### Phase 4: Refine & Commit

Lock in the decision and create clarity:

1. Present the chosen direction in digestible chunks (200-300 words max per section)
2. After each section, ask: "Does this look right so far?"
3. Be ready to revisit earlier assumptions if something feels off
4. End with clear, actionable next steps

## Socratic Question Types

Use these throughout all phases:

| Type | Purpose | Examples |
|------|---------|----------|
| **Clarifying** | Ensure understanding | "What do you mean by...?" / "Can you give an example?" |
| **Probing assumptions** | Surface hidden beliefs | "What are you assuming here?" / "What if that weren't true?" |
| **Exploring implications** | Trace consequences | "What would happen if...?" / "What's the consequence of that?" |
| **Seeking evidence** | Ground in reality | "What makes you think that?" / "How do you know?" |

## Output Formats

Select the most appropriate format based on context:

| Format | When to Use |
|--------|-------------|
| **Summary document** | Complex ideas needing documentation |
| **Decision matrix** | Comparing multiple options with criteria |
| **Action items** | Executable next steps with owners/dates |
| **Outline/structure** | Creative or writing projects |
| **Pros/cons list** | Binary decisions |

Let the topic guide your choice. Don't ask the user which format - just pick the most appropriate one.

## File Saving Behavior

At the end of a brainstorm session:

1. **Ask before saving**: "Would you like me to save this to a file?"
2. If yes, save to the **current working directory**
3. Use **topic-driven filenames** (no date prefix):
   - `mobile-app-launch-strategy.md`
   - `career-transition-options.md`
   - `product-feature-prioritization.md`
4. Use kebab-case, keep it descriptive but concise

## Example Session Flow

```
User: /brainstorm

Claude: What challenge or idea would you like to explore?
        Please describe it in one sentence.

User: I'm trying to decide whether to launch my product in the US or Europe first.

Claude: Great question! Let me reframe this as: "How might we choose the optimal
        launch market to maximize early success?"

        Before we generate options, I have a clarifying question:
        [Uses AskUserQuestion with choices about success metrics]

User: [Selects "Revenue growth" and "Market validation"]

Claude: Got it. And what constraints should we work within?
        [Uses AskUserQuestion with choices about budget, timeline, team]

... continues through all four phases ...

Claude: Here's your launch strategy summary. Would you like me to save this
        to a file in your current directory?
```

## Key Reminders

- **One question at a time** - Don't overwhelm with multiple questions
- **Prefer structured choices** - Use AskUserQuestion when options are clear
- **Defer judgment in Phase 2** - Generate freely, evaluate later
- **Invite user ideas before converging** - The user has domain expertise; draw it out
- **Lead with recommendations in Phase 3** - Don't be wishy-washy
- **Always offer to save** - But ask first, don't assume
