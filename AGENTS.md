# OpenCode Agent Harness

This file orients AI coding agents working in this repository. It is the
always-loaded **map**: project specifics plus the skill-driven workflow this
harness uses. Detail lives on-demand in the skills and rules — follow the
pointers, don't try to hold it all at once. Full background in
[README.md](README.md); how to extend the harness in
[CONTRIBUTING.md](CONTRIBUTING.md).

## Project Overview

An [opencode](https://opencode.ai)-native agent harness — skill-driven
workflows, subagent orchestration, standing rules, tech-aware conventions,
verification-first development. One harness, one target, no multi-harness
fragmentation.

## Commands

This is a markdown-first repo with three stdlib-Python validation gates:

```bash
python3 .opencode/harness/scripts/check-refs.py        # markdown reference integrity
python3 .opencode/harness/scripts/lint-frontmatter.py   # frontmatter + tech-dir consistency
python3 -m unittest discover -s tests -v                # installer tests
```

For the RED→GREEN test loop when this harness drives an actual codebase, see
`.opencode/harness/rules/verification-commands.md`.

## Tech

Markdown skills/rules/commands + the installer (`install.py`) and validators
under `.opencode/harness/scripts/`. Each downstream project declares
its own stack in `.opencode/harness/rules/tech.md`.

## Repo map

| Folder        | What it is                                                          | Read first when…                                          |
| ------------- | ------------------------------------------------------------------- | --------------------------------------------------------- |
| `.opencode/skills/`     | Lifecycle skills. Each is `.opencode/skills/<name>/SKILL.md`.                 | …doing that kind of task — load the matching skill first. |
| `.opencode/commands/`   | Slash entry points: `/adopt`, `/spec`, `/planning`, `/build`, `/test`, `/review`, `/code-simplify`, `/ship`, `/webperf`. | …invoking a workflow. See [README.md](README.md) § Commands. |
| `.opencode/agents/`     | Specialist subagents (`code-reviewer`, `security-auditor`, `test-engineer`, `web-performance-auditor`). | …fanning out a review. See [README.md](README.md) § Agents. |
| `.opencode/harness/rules/`      | Standing checklists + the tech declaration. Loaded on demand.       | …a command cites one. Only `.opencode/harness/rules/tech.md` is always loaded. |
| `.opencode/harness/tech/`       | Per-language conventions. Only stacks in `.opencode/harness/rules/tech.md` are active (lazy-loaded via the router). | …editing code — read the matching `.opencode/harness/tech/<name>/` files.   |
| `.opencode/harness/scripts/`    | `check-refs.py` + `lint-frontmatter.py` — validators.  | …you've added, renamed, or moved any `.md` file.          |
| `tests/`             | Installer unittest suite.                                           | …you've changed `install.py`.                             |
| `install.py`         | Installer (install/update/status) for adopting the harness into projects. | …distributing or updating the harness.  |

## Skill-Driven Execution

This project runs on a **skill-driven model**: if a task matches a skill, use
it. Skills live at `.opencode/skills/<name>/SKILL.md`. Don't implement directly when a
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

The workflow maps to slash commands (this harness ships `.opencode/commands/`) and the
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

- **Skills** (`.opencode/skills/<name>/SKILL.md`) — workflows with steps and exit criteria. The *how*. Mandatory when an intent matches.
- **Agents** (`.opencode/agents/<role>.md`) — specialist subagents with a perspective and output format. The *who*. opencode exposes each as a `mode: subagent` tool.
- **Commands** (`.opencode/commands/*.md`) — slash entry points. The *when*. The orchestration layer.

Composition rule: **the user (or a command) is the orchestrator. Agents do not invoke other agents.** An agent may invoke skills. The only multi-agent pattern this harness endorses is **parallel fan-out with a merge step** — used by `/ship`. See `.opencode/harness/rules/orchestration-patterns.md`.

## Boundaries

- Never auto-load every rule into `.opencode.jsonc` → `instructions` — the context budget is finite.
- Gotchas go in the code next to the trap (`/** GOTCHA */`), never accumulated here. See `documentation-and-adrs`.
- Restart opencode after any config change — config loads once at startup.
