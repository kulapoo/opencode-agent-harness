# OpenCode Agent Harness

An [opencode](https://opencode.ai)-native agent harness. It bundles the
patterns that make coding agents effective — skill-driven workflows,
subagent orchestration, standing rules, tech-aware conventions, and
verification-first development — into one drop-in configuration.

One harness, one target, no multi-harness fragmentation.

## Inspiration & credits

This project stands on the shoulders of two excellent works, and consolidates
their patterns into a single opencode-native harness:

- **[agent-skills](https://github.com/addyosmani/agent-skills)** by
  [@addyosmani](https://github.com/addyosmani) — a cross-framework library of
  reusable agent skills. The skill-driven workflow thinking and the breadth of
  the lifecycle coverage here are drawn directly from it.
- **[ecc](https://github.com/affaan-m/ecc)** by
  [@affaan-m](https://github.com/affaan-m) — an opinionated engineering
  culture and conventions kit. The standing-rules, tech-aware conventions, and
  verification-first stance trace back to ecc.

The goal of this harness is to bring those ideas together in one place,
purpose-built for [opencode](https://opencode.ai): one set of skills, agents,
commands, and tech conventions — no multi-harness fragmentation. Full credit
to both original projects for the underlying patterns; this repo is an
opencode-native consolidation, not a replacement for either.

## What's in the box

| Folder        | Purpose                                                                                          |
| ------------- | ------------------------------------------------------------------------------------------------ |
| `agents/`     | Specialist subagents (reviewer, security auditor, test engineer, web-perf auditor).              |
| `commands/`   | Slash commands: `/spec`, `/planning`, `/build`, `/test`, `/review`, `/code-simplify`, `/ship`, `/webperf`. |
| `skills/`     | 25 skills covering the full lifecycle (spec, plan, build, test, review, ship, debug, secure, …). |
| `rules/`      | Standing checklists and the tech declaration — the launch bar and conventions.                   |
| `tech/`       | Per-language/framework conventions. A ready-made library; only declared techs auto-load.         |
| `.opencode.jsonc` | Project config: injects `rules/tech.md` into context and wires the `chrome-devtools` MCP.    |

## Requirements

- [opencode](https://opencode.ai) installed and on `$PATH`.
- Node/npx available if you want the `chrome-devtools` MCP (used by `/webperf` deep mode and the browser-testing skill).

## Quick start

1. **Use this repo as your project's opencode config.** Either clone it into
   your project root, or copy the top-level folders (`agents/`, `commands/`,
   `skills/`, `rules/`, `tech/`) and `.opencode.jsonc` into your repo.

2. **Declare your tech.** Edit `rules/tech.md` and list the stacks you use,
   each matching a `tech/<name>/` folder:
   ```markdown
   ## Tech
   - python
   - react
   - rust
   ```
   Or run the `init-tech-declaration` skill — it detects stacks from your
   manifest files and writes the declaration for you.

3. **Restart opencode.** Config is loaded once at startup. After any change
   to `.opencode.jsonc`, an agent file, a skill, or a command, quit and
   restart opencode for the change to take effect.

## How the pieces fit

- **Auto-discovery.** opencode discovers `agents/*.md`, `commands/*.md`, and
  `skills/*/SKILL.md` by convention — no per-file registration needed.
- **System context.** `.opencode.jsonc` → `instructions` lists files injected
  into every session's context. Today that's `rules/tech.md`. The other
  `rules/*-checklist.md` files are **load-on-demand**: agents and commands
  pull them in when relevant (e.g. `/ship` Phase B cites the security,
  performance, accessibility, and observability checklists).
- **Tech conventions.** Each `tech/<name>/*.md` file declares a `paths:`
  glob. When you edit a matching file, opencode loads that tech's
  conventions into context. `tech/common/` is the glob-less baseline.
- **Subagents.** The four agents in `agents/` are `mode: subagent`, so the
  CLI exposes each as a tool with the same name — that's what lets `/ship`
  and `/webperf` fan out to them in parallel.
- **MCP.** `.opencode.jsonc` wires the `chrome-devtools` MCP server
  (`chrome-devtools-mcp`), used by `/webperf` deep mode and the
  `browser-testing-with-devtools` skill.

## Commands

| Command           | What it does                                                                    |
| ----------------- | ------------------------------------------------------------------------------- |
| `/spec`           | Write a structured specification before code.                                   |
| `/planning`       | Break work into small, verifiable, dependency-ordered tasks.                    |
| `/build`          | Implement tasks incrementally (RED → GREEN → commit). `/build auto` runs all.   |
| `/test`           | TDD workflow; Prove-It pattern for bugs.                                        |
| `/review`         | Five-axis code review (correctness, readability, architecture, security, perf). |
| `/code-simplify`  | Reduce complexity without changing behavior.                                    |
| `/ship`           | Parallel fan-out review + go/no-go launch decision with rollback plan.          |
| `/webperf`        | Web performance audit (Core Web Vitals, Lighthouse/trace analysis).             |

## Agents

| Agent                   | Role                                                              |
| ----------------------- | ----------------------------------------------------------------- |
| `code-reviewer`         | Five-axis staff-level code review.                                |
| `security-auditor`      | Vulnerability detection, threat modeling, OWASP/LLM Top 10.       |
| `test-engineer`         | Test strategy, coverage analysis, gap finding.                    |
| `web-performance-auditor` | Core Web Vitals, loading/rendering/network optimization.        |

## Tech conventions

`tech/` ships conventions for 20 stacks (angular, arkts, cpp, csharp, dart,
fsharp, golang, java, kotlin, nuxt, perl, php, python, react, react-native,
ruby, rust, swift, typescript, vue, web) plus a `common` baseline. **Only the
techs listed in `rules/tech.md` auto-load** — the rest stay dormant until you
opt them in. This keeps context lean for any single project while keeping the
full library one edit away.

## Validation

Check internal markdown references — verifies that links and backtick paths pointing into the harness's own directories resolve to real files:

```bash
python3 scripts/check-refs.py
```

Exits non-zero if any reference is broken.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add skills, agents,
commands, and tech conventions.

## License

[MIT](LICENSE).
