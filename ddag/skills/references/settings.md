# Project Settings (ddag_settings.py)

A project can have a `ddag_settings.py` file in the project root — a plain Python module that defines shared configuration as a frozen dataclass. This is optional but recommended when multiple nodes share parameters that must stay in sync.

## File Structure

```python
"""Project-wide settings for the ddag pipeline.

Each field is a shared parameter used by multiple nodes. Every field MUST have:
- A type annotation
- A default value
- An inline comment explaining what it controls and why this default was chosen
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # Minimum group size for results to be reportable.
    # Below this threshold, statistical noise dominates and small-sample bias increases.
    min_group_size: int = 30

    # Confidence level for all confidence intervals and hypothesis tests.
    # 0.95 is standard for most reporting; tighten to 0.99 for high-stakes outputs.
    confidence_level: float = 0.95


settings = Settings()
```

## Documentation Requirements

**Every field must be documented.** Each setting needs:

1. A **type annotation** (int, float, str, bool, etc.)
2. A **default value**
3. An **inline comment block above the field** explaining:
   - What the setting controls
   - The rationale for the default value
   - When or why someone might change it

This matches the rigor applied to node-local `params` (which carry name, type, value, and description). A setting without explanation is as bad as an undocumented column — future readers (human or LLM) won't know whether it's safe to change.

## Accessing Settings in Transform Code

```python
def transform(sources, params, outputs):
    from ddag_settings import settings
    # settings.min_group_size, settings.confidence_level, etc.
```

Settings are completely separate from node-local `params` — no namespace collisions. The frozen dataclass prevents accidental mutation. Since it's a regular Python file in the project directory, it works in the project's Python environment with no path manipulation.

## Settings vs Node-Local Params

**Use settings when:** Parameters should be the same across multiple nodes — analysis thresholds, shared constants, study-wide settings. If changing the value on one node would require changing it everywhere, put it in settings.

**Use node-local params when:** Parameters are intentionally different per node — dataset names, output formats, node-specific filters.

## Creating or Updating Settings

Create or edit `ddag_settings.py` directly in the project root. The LLM manages this file — adding new fields when nodes need shared configuration, updating values when the user requests changes.

When adding a new field:

1. Choose a descriptive name that reads naturally as `settings.<name>` in transform code
2. Add a type annotation and sensible default
3. Write a comment block above the field explaining what it controls, why this default, and when someone might change it
4. If replacing a hardcoded value that already exists in node transforms, update those nodes to use `from ddag_settings import settings` and reference the new field
