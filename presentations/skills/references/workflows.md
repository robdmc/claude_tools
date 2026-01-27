# Presentation Workflows

Detailed workflow documentation for the three presentation creation patterns.

## Workflow 1: Blank Canvas (Sketch-First)

Use this workflow when you have completed analysis and know the structure you want.

### Example Session

**User:** Create a presentation called q4-review with these slides: Title, Executive Summary, Revenue Analysis, Customer Growth, Challenges, Next Steps

**Claude:** Creates `presentations/q4-review/slides.md`:

```markdown
---
marp: true
theme: default
paginate: true
style: |
  [standard CSS here]
---

<!-- _class: title -->

# Q4 Review

---

## Executive Summary

---

## Revenue Analysis

---

## Customer Growth

---

## Challenges

---

## Next Steps
```

**User:** Let's work on Revenue Analysis

**Claude:** (Now focused on Revenue Analysis slide)

**User:** Add three bullets about our growth metrics

**Claude:** Updates the Revenue Analysis slide:

```markdown
---

## Revenue Analysis

- Total revenue increased 23% YoY to $4.2M
- Recurring revenue now represents 78% of total
- Average deal size grew from $12K to $18K
```

**User:** Include the revenue graph from viz

**Claude:**
1. Copies `.viz/revenue_trend.png` to `presentations/q4-review/assets/revenue_trend.png`
2. Updates slide:

```markdown
---

## Revenue Analysis

![w:700](./assets/revenue_trend.png)

- Total revenue increased 23% YoY to $4.2M
- Recurring revenue now represents 78% of total
- Average deal size grew from $12K to $18K
```

**User:** Now let's do Customer Growth

**Claude:** (Focus shifts to Customer Growth slide)

**User:** Move Challenges before Next Steps

**Claude:** Reorders slides in the markdown file.

**User:** Add a slide called Appendix after Next Steps

**Claude:** Adds new slide at the end:

```markdown
---

## Appendix
```

**User:** Generate a PDF

**Claude:** Runs compilation, outputs `presentations/q4-review/slides.pdf`

---

## Workflow 2: Analysis-Driven (Incremental)

Use this workflow when building a presentation while doing analysis.

### Example Session

**User:** [Working on data analysis, generates a revenue graph using viz skill]

**User:** Add this graph to the q4-review presentation as a new slide called Revenue Trends

**Claude:**
1. Copies `.viz/revenue_trends.png` to `presentations/q4-review/assets/revenue_trends.png`
2. Adds new slide to `slides.md`:

```markdown
---

## Revenue Trends

![w:700](./assets/revenue_trends.png)
```

**User:** [Continues analysis, discovers insight]

**User:** Update the Revenue Trends slide with a bullet about 15% YoY growth

**Claude:** Updates the slide:

```markdown
---

## Revenue Trends

![w:700](./assets/revenue_trends.png)

- Revenue grew 15% YoY, exceeding our 12% target
```

**User:** [Updates the graph in viz with new data]

**User:** Replace the graph with the updated version from viz

**Claude:**
1. Re-copies `.viz/revenue_trends.png` to `presentations/q4-review/assets/revenue_trends.png` (overwrites)
2. No markdown changes needed since filename is unchanged

---

## Workflow 3: Context Synthesis (One-Shot)

Use this workflow when you want Claude to generate a presentation from available context.

### Example Session

**User:** Create a presentation about the Q4 analysis we've been working on

**Claude:** I see we have:
- Conversation context with Q4 analysis findings
- Viz outputs in `.viz/`: revenue_trend.png, customer_growth.png, churn_analysis.png
- No scribe notes tagged for presentation

Based on our analysis, I'd propose this structure:

1. **Title** - Q4 2024 Business Review
2. **Executive Summary** - Key wins and challenges
3. **Revenue Performance** - Could include revenue_trend.png
4. **Customer Metrics** - Could include customer_growth.png
5. **Churn Analysis** - Could include churn_analysis.png
6. **Next Steps** - Recommendations

Does this structure work? Would you add, remove, or reorder anything?

**User:** Looks good, but add a Competitive Landscape slide after Customer Metrics

**Claude:** Updated structure:

1. Title
2. Executive Summary
3. Revenue Performance
4. Customer Metrics
5. **Competitive Landscape** (new)
6. Churn Analysis
7. Next Steps

Let me start with the slides. For the **Executive Summary**, I'm thinking:

- Q4 exceeded revenue targets by 8%
- Customer base grew 23% with improved retention
- Key challenge: increased competition in enterprise segment

What would you adjust?

**User:** Add a bullet about the new product launch

**Claude:** Got it. Moving to **Revenue Performance** - I'll include the revenue_trend.png graph. For the key points:

- Total revenue: $4.2M (+15% YoY)
- Recurring revenue: 78% of total
- Enterprise segment: 45% of new deals

Should I add the graph and these points?

**User:** Yes, that works

**Claude:** [Continues slide by slide...]

### Key Behaviors

1. **Propose titles first** - Get approval on structure before content
2. **Walk through slide by slide** - Don't fill everything at once
3. **Prompt at each step** - "What would you adjust?" / "Should I add X?"
4. **Mention available sources** - "I see viz outputs we could use..."

---

## Context Inference Rules

### Active Presentation

The skill tracks which presentation you're currently working on:

| Trigger | Example |
|---------|---------|
| Create presentation | "Create a presentation called q4-review" → active = q4-review |
| Open/switch | "Let's work on the product-launch deck" → active = product-launch |
| Inference | "Add a slide about pricing" (if only one presentation exists) |
| Ambiguous | "Add a slide" (multiple presentations) → Ask which one |

### Focused Slide

The skill tracks which slide you're currently editing:

| Trigger | Example |
|---------|---------|
| Explicit focus | "Let's work on the Summary slide" → focus = Summary |
| After edit | "Add a bullet about growth" → focus stays on that slide |
| Navigation | "Next slide" / "Previous slide" → focus shifts |
| Relative | "Now let's do Customer Growth" → focus = Customer Growth |
| Implicit | "Add another bullet" → applies to last-edited slide |

---

## Viz Integration Patterns

### Adding a New Graph

```
User: "Add the revenue graph to this slide"

Claude actions:
1. Identify source: .viz/revenue_graph.png (from context or ask)
2. Copy: cp .viz/revenue_graph.png presentations/<slug>/assets/
3. Add to slide: ![w:700](./assets/revenue_graph.png)
```

### Updating an Existing Graph

```
User: "Update the graph with the new version"

Claude actions:
1. Identify which graph (from context or ask)
2. Re-copy: cp .viz/revenue_graph.png presentations/<slug>/assets/ (overwrite)
3. No markdown changes if filename unchanged
```

### Adding Graph to New Slide

```
User: "Add this as a new slide called Revenue Trends"

Claude actions:
1. Copy graph to assets/
2. Create new slide:
   ---

   ## Revenue Trends

   ![w:700](./assets/revenue_graph.png)
```

---

## Scribe Integration Patterns

### Using Scribe Notes as Source

```
User: "Create a presentation from my scribe notes"

Claude actions:
1. List files in .scribe/ directory
2. Read relevant entries
3. Synthesize into proposed slide structure
4. Follow context synthesis workflow
```

### Using Tagged Entries

```
User: "Create a presentation from entries tagged 'quarterly-review'"

Claude actions:
1. Search .scribe/ for files containing "quarterly-review" tag
2. Read matching entries
3. Synthesize into proposed slide structure
4. Follow context synthesis workflow
```

### Scribe Entry Format

Scribe entries typically live at `.scribe/<date>-<topic>.md` and may contain YAML frontmatter with tags:

```markdown
---
tags: [quarterly-review, presentation-material]
date: 2024-01-15
---

# Key Finding: Revenue Growth

Analysis shows 15% YoY growth...
```

---

## Slide Operations Reference

### Add Slide

```
"Add a slide called [Title]"
"Add a slide called [Title] after [Existing Title]"
"Insert a new slide before [Existing Title]"
```

### Delete Slide

```
"Remove the [Title] slide"
"Delete the Challenges slide"
```

### Reorder Slides

```
"Move [Title] before [Other Title]"
"Move [Title] after [Other Title]"
"Move [Title] to the end"
"Swap [Title A] and [Title B]"
```

### Edit Slide Content

```
"Add a bullet about [topic]"
"Add three points about [topic]"
"Remove the second bullet"
"Change the title to [new title]"
"Add speaker notes: [notes]"
```

### Focus/Navigation

```
"Let's work on [Title]"
"Focus on [Title]"
"Next slide"
"Previous slide"
"Go to the first slide"
```
