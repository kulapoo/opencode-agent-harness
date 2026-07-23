# <PROJECT_NAME>

<!--
  This is the always-loaded map for AI coding agents working in this
  repository. It follows the agents.md standard and the OpenCode Agent
  Harness skill-driven model. /adopt fills the <PLACEHOLDER>s; downstream
  projects derive their AGENTS.md from this file.
-->

This file orients AI coding agents working in this repository. It is the
always-loaded **map**: project specifics plus the skill-driven workflow this
project uses. Detail lives on-demand in the skills and rules — follow the
pointers, don't try to hold it all at once.

## Project Overview

<PROJECT_OVERVIEW — one paragraph: what this project is and who it's for.>

## Commands

Fill with full commands, not tool names: <BUILD_COMMAND>, <TEST_COMMAND>,
<LINT_COMMAND>, <DEV_COMMAND>. The project uses the OpenCode Agent Harness —
for the RED→GREEN test loop and quiet-verification defaults, see
`rules/verification-commands.md`.

## Tech

Declared in `rules/tech.md` (injected into every session). Each entry maps to
`tech/<name>/` — read the matching folder before editing that stack's code.

## Skill-Driven Execution

This project runs on a **skill-driven model**: if a task matches a skill, use
it. Skills live at `skills/<name>/SKILL.md`. Don't implement directly when a
skill applies; follow its workflow exactly — no partial application.

### Intent → Skill

| If the task is… | Use this skill |
| --- | --- |
| New feature / functionality | `spec-driven-development` → `incremental-implementation` + `test-driven-development` |
| Planning / breakdown | `planning-and-task-breakdown` |
| Bug / failure / unexpected behavior | `debugging-and-error-recovery` |
| Code review | `code-review-and-quality` |
| Refactor / simplification | `code-simplification` |
| API / interface design | `api-and-interface-design` |
| UI / frontend | `frontend-ui-engineering` |
| Security hardening | `security-and-hardening` |
| Docs / decisions | `documentation-and-adrs` |

More skills exist — reach for the matching one before inventing a process.

### Lifecycle

The workflow maps to slash commands (this harness ships `commands/`) and the
skills behind them:

```
DEFINE → /spec        spec-driven-development
PLAN   → /planning    planning-and-task-breakdown
BUILD  → /build       incremental-implementation + test-driven-development
VERIFY → /test        debugging-and-error-recovery
REVIEW → /review      code-review-and-quality
SHIP   → /ship        shipping-and-launch
```

### Anti-rationalization

These thoughts are wrong — ignore them:

- "This is too small for a skill."
- "I can just quickly implement this."
- "I'll gather context first."

Correct behavior: always check for and use a skill first, even for small tasks.

## Orchestration

Three composable layers — different jobs, don't confuse them:

- **Skills** (`skills/<name>/SKILL.md`) — workflows with steps and exit criteria. The *how*. Mandatory when an intent matches.
- **Agents** (`agents/<role>.md`) — specialist subagents with a perspective and output format. The *who*. opencode exposes each as a `mode: subagent` tool.
- **Commands** (`commands/*.md`) — slash entry points. The *when*. The orchestration layer.

Composition rule: **the user (or a command) is the orchestrator. Agents do not invoke other agents.** An agent may invoke skills. The only multi-agent pattern this harness endorses is **parallel fan-out with a merge step** — used by `/ship`. See `rules/orchestration-patterns.md`.

## Boundaries

<PROJECT_BOUNDARIES — always do / ask first / never do, project-specific.>

Harness defaults (apply unless the project overrides):

- Rules are load-on-demand — only `rules/tech.md` sits in every session. Keep `.opencode.jsonc` → `instructions` lean.
- Gotchas go in the code next to the trap (`/** GOTCHA */`), never accumulated here. See `documentation-and-adrs`.
- Restart opencode after any config change — config loads once at startup.
