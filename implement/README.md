# Implement — Parallel Plan Execution

Implement is a Claude Code skill that executes implementation plans using parallel worker agents. Give it a plan file or description, and it coordinates multiple agents to build your feature concurrently while respecting task dependencies.

## What It Does

- **Breaks plans into tasks** — Analyzes your plan and creates discrete, trackable tasks
- **Manages dependencies** — Ensures tasks run in the right order (parallel when possible, sequential when required)
- **Spawns parallel workers** — Up to 3 agents work simultaneously on independent tasks
- **Runs tests once** — Verification happens after all tasks complete, not per-agent
- **Supports resume** — Pick up where you left off if a session is interrupted

## Requirements

- Claude Code with Task primitives (TaskCreate, TaskUpdate, TaskList, TaskGet)

## Installation

Use the `/install` command from the claude_tools repository:

```
/install
```

Or manually place the files:

```
~/.claude/skills/implement/
├── SKILL.md
└── (no scripts — uses native Task primitives)

~/.claude/agents/
└── task-worker.md
```

## Usage

### From a Plan File

```
/implement path/to/plan.md
```

The plan file should describe what to build, with enough detail to break into tasks. Plans from `/implementation-plan` or similar planning skills work well.

### From a Description

```
/implement "Add user authentication with JWT tokens and refresh flow"
```

The skill will ask clarifying questions and break the description into tasks.

### Resume a Session

```
/implement --resume path/to/implementation-plans/feature-name.md
```

Continues from where execution left off, using the execution log to track progress.

## How It Works

### 1. Plan Analysis

The skill reads your plan and identifies:
- Discrete tasks (each one atomic and implementable)
- Dependencies between tasks
- Phases (groups of tasks that can run in parallel)

### 2. Task Creation

Each task is created with:
- A clear subject ("Implement AuthService")
- Full description with context and requirements
- Dependencies on upstream tasks

### 3. Parallel Execution

The orchestrator spawns up to 3 worker agents simultaneously:
- Each worker claims one task
- Workers follow the task-worker protocol (read CLAUDE.md, implement, mark complete)
- Workers never run tests or linters — only the orchestrator does that

### 4. Verification

Only after all tasks complete:
- Tests run once (detected from CLAUDE.md or project config)
- Linting runs once
- Results reported to user

## Example Session

```
> /implement add-caching.md

Created 6 tasks in 3 phases

Phase 1: Starting 3 parallel tasks...
  task-1 completed (CacheService interface created)
  task-2 completed (Redis client wrapper created)
  task-3 completed (Cache key generator created)

Phase 2: Starting 2 parallel tasks...
  task-4 completed (CacheService implementation created)
  task-5 completed (Cache middleware created)

Phase 3: Starting 1 task...
  task-6 completed (Integration with existing services)

All 6 tasks completed
Running tests... PASSED
Running lint... CLEAN
```

## Generated Files

The skill creates a tracking file at `implementation-plans/<name>.md`:

```markdown
# Implementation: Add Caching

*Generated: 2026-01-26T14:30:00*
*Tasks: 6 | Phases: 3*

## Tasks

### Phase 1: Foundation (parallel)
- [x] `task-1` Create CacheService interface
- [x] `task-2` Create Redis client wrapper
- [x] `task-3` Create cache key generator

### Phase 2: Implementation (blocked by Phase 1)
- [x] `task-4` Implement CacheService
- [x] `task-5` Create cache middleware

### Phase 3: Integration (blocked by Phase 2)
- [x] `task-6` Integrate with existing services

---

## Execution Log

14:30:15 - Phase 1 started (3 tasks)
14:31:42 - task-1 completed
14:32:01 - task-2 completed
...

## Summary

Completed: 2026-01-26T14:35:00
Tasks: 6 completed, 0 failed
Tests: PASSED
Lint: CLEAN
```

## Worker Agent Protocol

Each worker agent follows a strict protocol defined in `task-worker.md`:

**Do:**
- Read CLAUDE.md for project patterns
- Read files before editing
- Follow existing code style
- Mark task complete when done

**Don't:**
- Run tests (orchestrator handles this)
- Run linters (orchestrator handles this)
- Spawn sub-agents (workers are leaf nodes)
- Modify other tasks (only your assigned task)
- Commit to git (user/orchestrator decides)

## Error Handling

**If a worker fails:**
- The orchestrator detects the stuck task
- Asks you: "Task X failed. Retry? (y/n/skip)"
- Retry spawns a new worker for the same task
- Skip marks the task complete with a note

**If tests fail:**
- Results are reported with details
- You can review and fix before continuing

## Parallelism

- **Default: 3 parallel workers** — Balances speed with resource usage
- **Maximum: 5** — Beyond this, diminishing returns
- **Dependencies respected** — Blocked tasks always wait

## Tips

- **Write good plans** — More detail in the plan means better task breakdown
- **Use phases wisely** — Independent work should be in the same phase
- **Let workers focus** — Each task should be completable without cross-task coordination
- **Review the execution log** — It's your record of what happened

## Files

| File | Purpose |
|------|---------|
| `skills/SKILL.md` | Orchestrator instructions for Claude |
| `agents/task-worker.md` | Worker protocol (included in agent prompts) |
