# Agentic Development Orchestration Patterns for Solo Founders (2025-2026)

> Research compiled 2026-04-01 from 20+ sources. Focus: actionable patterns for a solo developer using Claude Code to burn through a P0 backlog with parallel subagents.

---

## Executive Summary

The 2025-2026 shift in AI-assisted development is from **conversation-based coding** to **autonomous workflow orchestration**. The winning pattern for solo founders is:

1. **Human stays above the loop** -- write specs, approve plans, review diffs
2. **Agents execute in parallel** -- scoped to bounded tasks with clear file boundaries
3. **Verification gates are non-negotiable** -- lint/typecheck/test between every agent handoff
4. **Everything persists to disk** -- so context resets don't kill momentum

Key benchmark: Multi-agent systems score **72.2% on SWE-bench Verified** vs ~65% for single agents using the same model. The gains come from specialization and cross-validation, not from using a better model.

---

## Pattern 1: The Four-Phase Loop (Spec -> Plan -> Execute -> Verify)

**Source**: vibecoding.app, George Violaris, PromptLayer, multiple practitioners

This is the universal pattern every successful agentic workflow converges on:

```
Spec -> Plan -> Execute -> Verify -> Ship
  ^                                    |
  +-------- Next iteration -----------+
```

### How to implement in Claude Code:

| Phase | Who | Tool | Output |
|-------|-----|------|--------|
| **Spec** | Human | Write markdown in `docs/specs/` | Acceptance criteria, constraints, affected files |
| **Plan** | Planner agent OR human | `/gsd:plan-phase` or manual | Task breakdown with file assignments |
| **Execute** | Coder subagents (parallel) | `Task` tool / `.claude/agents/` | Code changes in isolated branches or worktrees |
| **Verify** | Reviewer agent + human | Lint + typecheck + test + AI review + human diff | Merged or sent back |

### The critical insight from George Violaris:
> "The agent doesn't replace engineering discipline. It demands it. You can't be lazy about specs when your implementer is a literal machine that will do exactly what you said -- including the parts you got wrong."

### Spec format that works (structured ticket):
```
Task: [What to change]
Acceptance: [Observable behavior when done]
Files: [Specific files/modules involved]
Constraints: [What NOT to touch, backward compat, budget]
```

---

## Pattern 2: Parallel Subagent Orchestration

**Source**: ClaudeLab, ClaudeFast, Tim Dietrich, turion.ai

### The Three Dispatch Modes

Configure these in your `CLAUDE.md` so the central agent makes correct routing decisions:

**Parallel dispatch** (ALL conditions must be met):
- 3+ unrelated tasks or independent domains
- No shared state between tasks
- Clear file boundaries with no overlap

**Sequential dispatch** (ANY condition triggers):
- Tasks have dependencies (B needs output from A)
- Shared files or state (merge conflict risk)
- Unclear scope (need to understand before proceeding)

**Background dispatch**:
- Research or analysis tasks (not file modifications)
- Results aren't blocking your current work
- Press `Ctrl+B` to background any running subagent

### Domain-Based Splitting (for TMC-style full-stack projects):

```
## Domain Parallel Patterns (add to CLAUDE.md)

When implementing features across domains, spawn parallel agents:

- **Frontend agent**: React components, pages, UI state (tmc-redacao/src/)
- **Backend agent**: Azure Functions, services, business logic (FeedRSS/tmc-rss-collector/)
- **Database agent**: Migrations, queries, schema changes (migrations/)
- **Test agent**: Unit tests, integration tests, audit scripts (tests/, scripts/)

Each agent owns their domain. No file overlap.
```

### Cost Optimization:
- Run main session on **Opus** for complex reasoning
- Run subagents on **Sonnet** for focused execution tasks
- Set `CLAUDE_CODE_SUBAGENT_MODEL="claude-sonnet-4-5"` in environment
- Use `--max-budget-usd` per subagent invocation

### Isolation Strategies (pick one per task):

| Strategy | Best For | Risk |
|----------|----------|------|
| **Git worktrees** (one per agent) | Large changes, multi-file refactors | Merge conflicts at integration |
| **Branch-per-agent** | Medium changes | Branch management overhead |
| **File-level scoping** | Small fixes, non-overlapping files | Agent drift if scope is vague |

---

## Pattern 3: The Invocation Quality Protocol

**Source**: ClaudeFast, Adnan Masood PhD

> "Most sub-agent failures aren't execution failures -- they're invocation failures."

The #1 mistake: spawning a subagent with "Fix authentication" instead of giving it full context. Subagents have temporary context windows and CANNOT ask clarifying questions.

### Every subagent invocation MUST include:

1. **Specific scope**: Exact files, functions, or modules to modify
2. **Context**: Why this change is needed, what the current behavior is
3. **Success criteria**: What "done" looks like, how to verify
4. **Constraints**: What NOT to change, performance requirements, style conventions

### Bad vs Good invocation:

```
# BAD: Vague, no context
"Fix the scoring bug"

# GOOD: Dense context, clear scope, verifiable
"Fix the editorial scoring bug where articles with impacto='high' 
receive 0 points instead of 30. The bug is in 
FeedRSS/tmc-rss-collector/services/scoring_service.py in the 
calculate_score() function. The impacto signal mapping should be:
high=30, medium=15, low=0. After fixing, run pytest tests/test_scoring.py 
to verify. Do NOT modify the denormalized score columns in database.py."
```

---

## Pattern 4: TDD with Agentic AI (Test-Driven Agent Development)

**Source**: Emily Bache, Latent.Space (Anita Kirkovska), TDFlow (CMU), DeveloperToolkit

### The 2026 TDD Evolution:

Classic TDD: Red -> Green -> Refactor (human writes tests first)
Agentic TDD: **Spec -> Test+Code -> Verify -> Refactor** (agent writes both, human verifies)

Key finding from Emily Bache's practitioner interviews:
> "The TDD practitioners reported that the quality they get in the end is as good or even better than what they would have written by themselves."

### How experienced practitioners do it:

1. **Spec as test list**: Write a markdown spec document (replaces the paper test list). The spec IS the test driver.
2. **Agent writes test+code together**: Agents struggle with red-green separately (training data has almost no "failing test" snapshots). Let them produce both in one step.
3. **Steps stay short**: Commit every few minutes. Small diffs are reviewable. Large diffs are not.
4. **Human reads ALL code**: Code quality remains a concern. Short steps = small diffs = reviewable.
5. **Mutation testing as refactor signal**: Agents routinely use mutation testing, property-based testing, and approval testing as additional feedback loops during refactoring.

### TDFlow Pattern (from CMU research):

```
1. Generate tests from spec (acceptance + unit)
2. Run tests (they fail - RED)
3. Agent implements code to pass tests (GREEN)
4. Agent refactors with passing tests as safety net
5. Human reviews diff against spec
```

### Practical TDD workflow for P0 fixes:

```
For each P0 bug:
1. Write a failing test that reproduces the bug (or have the agent write it from a bug report)
2. Ask the agent: "Make this test pass. Only modify [specific file]. Run the full test suite after."
3. Review the diff -- is it minimal? Does it only fix what was asked?
4. If the fix touches unexpected files, reject and re-scope
```

---

## Pattern 5: GSD (Get Shit Done) Framework

**Source**: aiproductivity.ai, GSD GitHub (23k stars), multiple practitioner reports

GSD is a spec-driven development system built entirely on Claude Code's native capabilities. No external runtime.

### Core architecture:
- **50 Markdown files** in `.claude/commands/gsd/`
- **29 skills**, **12 custom agents**, **2 hooks**
- Everything persists to `.planning/` directory
- Git commits after each step

### The 6-command workflow:

| Command | Purpose |
|---------|---------|
| `/gsd:new-project` | Capture idea, generate specs |
| `/gsd:discuss-phase` | Clarify details, resolve ambiguity |
| `/gsd:plan-phase` | Break work into tasks with verification criteria |
| `/gsd:execute-phase` | Run tasks in parallel via subagents |
| `/gsd:verify-work` | Validate output against spec |
| `/gsd:complete-milestone` | Archive and release |

### Fan-out/Fan-in Pattern (GSD's parallel research):

```
Research Phase:
  Agent 1 -> Tech stack analysis     -> results/tech.md
  Agent 2 -> Feature investigation   -> results/features.md
  Agent 3 -> Architecture review     -> results/arch.md
  Agent 4 -> Risk/pitfall analysis   -> results/risks.md
                    |
            Synthesizer Agent (sequential)
                    |
            Roadmapper Agent -> final plan
```

### Context Recovery (solving the biggest solo-founder pain):

GSD records everything to `.planning/`:
- `PROJECT.md` -- project definition
- `ROADMAP.md` -- phase breakdown
- `STATUS.md` -- current state
- Per-phase `PLAN.md` files

`/gsd:resume-work` reads state back. You can pick up after any context reset.

---

## Pattern 6: The 4S Loop (Lightweight SDD for Solo Founders)

**Source**: Adrian Del Campo, PromptLayer

A minimal spec-driven loop when GSD feels too heavy:

```
Specify -> Solve -> Synthesize -> Ship
    ^                              |
    +--------- iterate -----------+
```

1. **Specify**: Write a 1-page spec with acceptance criteria
2. **Solve**: Agent implements against the spec
3. **Synthesize**: Agent writes tests, human reviews diff
4. **Ship**: Merge, deploy, move to next spec

---

## Pattern 7: Three Modes of Claude Code Usage

**Source**: coSPEC, multiple practitioners

| Mode | Trigger | Human Role | Best For |
|------|---------|------------|----------|
| **Interactive** | Developer at terminal | In the loop, real-time | Debugging, exploration, complex reasoning |
| **Scripted** | Git hooks, CI steps | Reviews output | Pre-commit review, PR descriptions, lint fixes |
| **Background (Autonomous)** | Webhooks, schedules, ticket assignment | Reviews PRs | Dependency updates, bug triage, routine maintenance |

### For P0 backlog burning, use Interactive + Scripted:
- **Interactive**: For each P0, write the spec, review the plan, approve the diff
- **Scripted**: Automated test runs, lint checks, build verification after each change
- **Background**: Save for later (dependency updates, monitoring)

---

## Pattern 8: Verification Gates (Non-Negotiable)

**Source**: All sources converge on this

> "Without verification gates, errors compound across handoffs and you ship worse code than a single agent would produce."

### Three-Layer Verification:

**Layer 1 -- Automated (fast, deterministic):**
```bash
npm run lint          # or pylint/flake8
npm run typecheck     # or mypy
npm test              # unit tests
npm run build         # compilation
```
If ANY check fails, route back to the coder agent with the error. Do NOT proceed.

**Layer 2 -- AI Review (medium, catches logic errors):**
- Reviewer agent reads the diff
- Checks: logic errors, security issues, architectural problems, style violations
- Can be a separate Claude Code subagent with reviewer role

**Layer 3 -- Human Review (thorough, final approval):**
- Focus on business logic correctness
- Edge cases agents might have missed
- Unexpected changes (agents sometimes "improve" things you didn't ask about)
- Catches the ~13% of failures that are reasoning-action mismatches

### Verification in CLAUDE.md:
```
## Verification Protocol (add to CLAUDE.md)

After EVERY code change:
1. Run `npm run lint && npm run build` (frontend)
2. Run `pytest tests/` (backend)  
3. If any check fails, fix before proceeding
4. Never skip verification, even for "small" changes

Before EVERY commit:
1. Run full test suite
2. Verify the change matches the spec
3. Check that no unrelated files were modified
```

---

## Pattern 9: Persistent Agent Definitions

**Source**: ClaudeFast, ClaudeLab, GSD

Instead of ad-hoc Task tool invocations, define reusable specialist agents as Markdown files:

### `.claude/agents/reviewer.md`:
```yaml
---
name: CodeReviewer
description: Reviews diffs against specs for logic errors, security issues, and style violations
tools: Read, Grep, Glob
---

You are a code reviewer. Given a diff and a spec:
1. Check every change traces back to a spec requirement
2. Flag silent assumptions (error handling, defaults, security boundaries)
3. Flag unexpected file modifications
4. Verify naming conventions and architectural boundaries
5. Output: APPROVE, REQUEST_CHANGES (with specific issues), or BLOCK (with critical issues)
```

### `.claude/agents/fixer.md`:
```yaml
---
name: BugFixer  
description: Fixes bugs from spec with minimal changes
tools: Read, Edit, Bash, Grep, Glob
---

You are a bug fixer. Given a bug report:
1. Read the bug description and acceptance criteria
2. Locate the relevant code
3. Write a failing test that reproduces the bug
4. Make the MINIMAL change to fix it
5. Run the test suite to verify no regressions
6. Report what you changed and why
```

---

## Recommended Orchestration Setup for TMC P0 Backlog

Based on all research, here is the concrete setup for burning through P0 fixes:

### Step 1: Prepare CLAUDE.md additions

Add sub-agent routing rules, verification protocol, and domain boundaries (see Patterns 2 and 8 above).

### Step 2: Create specialist agents in `.claude/agents/`

- `fixer.md` -- Bug fixes with minimal changes + test
- `reviewer.md` -- Diff review against spec
- `researcher.md` -- Codebase exploration (read-only, backgroundable)

### Step 3: For each P0 fix, follow this loop:

```
1. SPEC (you, 2-5 min):
   Write a structured ticket in the chat:
   - What's broken (observable behavior)
   - What should happen (acceptance criteria)  
   - Files likely involved
   - Constraints (what NOT to touch)

2. PLAN (agent, auto):
   Agent reads spec, explores code, proposes a plan.
   You approve or adjust.

3. EXECUTE (subagent):
   Spawn a fixer subagent with the full spec context.
   If the fix spans frontend+backend, spawn two parallel subagents
   (one per domain).

4. VERIFY (automated + you):
   - Agent runs lint + build + tests
   - Agent spawns reviewer subagent on the diff
   - You review the final diff (focus: minimal change, matches spec, no surprises)

5. COMMIT + NEXT:
   Atomic commit with conventional message.
   Move to next P0.
```

### Step 4: Cost control

- Set `CLAUDE_CODE_SUBAGENT_MODEL=claude-sonnet-4-5` for subagents
- Use `--max-budget-usd 5` per subagent invocation
- Main session stays on Opus for orchestration
- Track token usage with `/stats`

### Step 5: Context recovery

- Keep `STATUS.md` updated after each P0 fix
- Use `/compact` between fixes to free context
- If context gets stale, start a new session and read STATUS.md

---

## Anti-Patterns to Avoid

| Anti-Pattern | Why It Fails | Fix |
|-------------|-------------|-----|
| **Over-parallelizing** | 10 agents for a simple fix wastes tokens and creates coordination overhead | Group related micro-tasks; use 2-3 agents max per feature |
| **Vague invocations** | "Fix the bug" gives the agent nothing to work with | Include file paths, function names, expected behavior, constraints |
| **Skipping verification** | Errors compound across handoffs silently | Lint+test after EVERY agent output, no exceptions |
| **Giant agent diffs** | Unreviewable; hide regressions | Keep steps small; commit every few minutes |
| **No context persistence** | Context resets kill momentum | Write STATUS.md, persist specs to disk, use `/compact` |
| **Agent writes spec** | Agents are good at executing, bad at deciding what to build | Human writes spec; agent executes |
| **Trusting agent self-reports** | Agents don't flag uncertainty like humans do | Always verify with deterministic checks (tests, lint, build) |

---

## Key Sources

1. ClaudeFast -- Sub-Agent Best Practices, Async Workflows, Agent Teams Workflow (2026-03)
2. VibeCoding.app -- Multi-Agent Dev Loop, Multi-Agent vs Single-Agent Comparison (2026-03)
3. ClaudeLab -- Advanced Multi-Agent Guide, Autonomous Workflows 2026 (2026-03)
4. Emily Bache -- Test-Driven Development with Agentic AI (2026-03)
5. George Violaris -- The Agentic Development Loop (2026-03)
6. Adnan Masood -- Agentic Software Development: The Complete Playbook (2026-03)
7. AI Productivity -- GSD Framework Technical Breakdown (2026-03)
8. Tim Dietrich -- Claude Code Sub-Agents for Parallel Work (2026-01)
9. PromptLayer -- Claude Code Spec Workflow (2026-01)
10. coSPEC -- Claude Code in Development Workflows (2026-03)
11. Adrian Del Campo -- The 4S Loop for Vibecoding (2026-02)
12. TDFlow (CMU) -- Agentic Workflows for Test Driven Software Engineering (2025-09)
13. Latent.Space -- AI Agents Meet TDD (2025-04)
