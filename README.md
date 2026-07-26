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
| `.opencode/agents/`     | Specialist subagents (reviewer, security auditor, test engineer, web-perf auditor).              |
| `.opencode/commands/`   | Slash commands: `/adopt`, `/spec`, `/planning`, `/build`, `/test`, `/review`, `/code-simplify`, `/ship`, `/webperf`, `/how-to-guide`. |
| `.opencode/skills/`     | 25 skills covering the full lifecycle (spec, plan, build, test, review, ship, debug, secure, …). |
| `.opencode/harness/rules/`      | Standing checklists and the tech declaration — the launch bar and conventions.                   |
| `.opencode/harness/tech/`       | Per-language/framework conventions. A ready-made library; only declared techs lazy-load via the router.         |
| `.opencode/harness/references/` | Consolidated reference material that commands pull from conversationally (backs `/how-to-guide`). Never injected wholesale. |
| `.opencode.jsonc` | Project config: injects `.opencode/harness/rules/tech.md` (the tech router) into every session.    |

## Requirements

- [opencode](https://opencode.ai) installed and on `$PATH`.
- Python 3.8+ for the reference validator (`check-refs.py`) and installer.
- Node/npx only if you opt into the `chrome-devtools` MCP (see `/webperf` deep mode).

## Quick start

1. **Install the harness into your project.** From inside the target project:

   ```bash
   curl -fsSL https://raw.githubusercontent.com/kulapoo/opencode-agent-harness/v0.4.0/install.py \
     | python3 - install
   ```

   This fetches the installer pinned to tag `v0.4.0` and runs it once. It
   copies the `.opencode/` tree (agents, commands, skills, rules, tech,
   scripts) and writes a manifest used by `status` to report drift. The install
   set is gated by a `MANIFEST` — a file under `.opencode/` ships only if listed
   there, so stray maintainer-only files can't leak in.

   **Prefer to inspect first?** Cautious environments (corporate networks, audit
   requirements) — download, audit, then run:

   ```bash
   curl -fsSL https://raw.githubusercontent.com/kulapoo/opencode-agent-harness/v0.4.0/install.py -o install.py
   less install.py
   python3 install.py install
   ```

   **Air-gapped or want a local clone?** `git clone` this repo, then from your
   project: `python3 /path/to/opencode-agent-harness/install.py install --from /path/to/opencode-agent-harness`.

2. **Adopt.** Run `/adopt` in opencode — it detects your stack, writes the
   lazy-load tech router (`.opencode/harness/rules/tech.md`), wires your config,
   and scaffolds a project `AGENTS.md`. Prefer the manual route? Edit
   `.opencode/harness/rules/tech.md` and list the stacks you use, each matching
   a `.opencode/harness/tech/<name>/` folder.

3. **Restart opencode.** Config loads once at startup. After any change to
   config, an agent, a skill, or a command, quit and restart.

**Trust & pinning.** The one-liner executes remote code pinned to a tag — the
exact bytes a reviewer sees at that tag, frozen. Bump the tag in the URL when
you want a newer installer. For air-gapped or audited environments, use the
clone path above.

**Refreshing.** There is no `update` or `migrate` step — `install` is
idempotent and is the only command that writes files. To refresh a project
against a newer harness, re-run `install`; files that already match are left
untouched, and any local files that differ are reported with an overwrite
warning before anything happens. Overwriting is always your explicit decision
via `--force`. `install.py` lives in the harness source repo and is never
copied into your project (see [adopt.md](.opencode/commands/adopt.md) § manifest).

```bash
# one-liner users — re-run install (or status to inspect without writing):
curl -fsSL https://raw.githubusercontent.com/kulapoo/opencode-agent-harness/v0.4.0/install.py \
  | python3 - install      # or: ... | python3 - status

# clone users — invoke by absolute path:
python3 /path/to/opencode-agent-harness/install.py install
python3 /path/to/opencode-agent-harness/install.py status
```

`status` shows the installed version and any modified or missing files; it
changes nothing. It also reports **orphans** — files under `.opencode/` the
current harness no longer ships (e.g. a deprecated command from a prior
version). `install` lists the same orphans with a deprecation explanation; pass
`--prune-deprecated` to delete the deprecated ones.

## How the pieces fit

- **Auto-discovery.** opencode discovers `.opencode/agents/*.md`, `.opencode/commands/*.md`, and
  `.opencode/skills/*/SKILL.md` by convention — no per-file registration needed.
- **System context.** `.opencode.jsonc` → `instructions` lists files injected
  into every session's context. Today that's `.opencode/harness/rules/tech.md`. The other
  `.opencode/harness/rules/*-checklist.md` files are **load-on-demand**: agents and commands
  pull them in when relevant (e.g. `/ship` Phase B cites the security,
  performance, accessibility, and observability checklists).
- **Tech conventions (lazy router).** `.opencode/harness/rules/tech.md` is the
  always-injected router — it lists active stacks and tells the agent which
  `.opencode/harness/tech/<name>/*.md` files to Read before writing code. Tech
  files keep a `paths:` frontmatter glob for documentation and future
  cross-tool export, but opencode does not auto-inject on glob match.
- **Reference material.** `.opencode/harness/references/*.md` holds consolidated
  answers that commands surface conversationally — `/how-to-guide` picks the
  relevant slice and re-explains it in context rather than dumping the file.
  Like the checklists, references stay load-on-demand and are never injected
  wholesale into every session.
- **Subagents.** The four agents in `.opencode/agents/` are `mode: subagent`, so the
  CLI exposes each as a tool with the same name — that's what lets `/ship`
  and `/webperf` fan out to them in parallel.
- **MCP.** Optional — wire the `chrome-devtools` MCP server in your project's
  config if you use `/webperf` deep mode or the `browser-testing-with-devtools`
  skill. Not enabled by default.

## Commands

| Command           | What it does                                                                    |
| ----------------- | ------------------------------------------------------------------------------- |
| `/adopt`          | Adopt the harness into a project — detect tech, wire config, scaffold the agent map. Run once, re-run as a health check. |
| `/spec`           | Write a structured specification before code.                                   |
| `/planning`       | Break work into small, verifiable, dependency-ordered tasks.                    |
| `/build`          | Implement tasks incrementally (RED → GREEN → commit). `/build auto` runs all.   |
| `/test`           | TDD workflow; Prove-It pattern for bugs.                                        |
| `/review`         | Five-axis code review (correctness, readability, architecture, security, perf). |
| `/code-simplify`  | Reduce complexity without changing behavior.                                    |
| `/ship`           | Parallel fan-out review + go/no-go launch decision with rollback plan.          |
| `/webperf`        | Web performance audit (Core Web Vitals, Lighthouse/trace analysis).             |
| `/how-to-guide`   | Conversational FAQ — ask about workflow, artifacts, phases, methodology fit, or resuming work. |

## Agents

| Agent                   | Role                                                              |
| ----------------------- | ----------------------------------------------------------------- |
| `code-reviewer`         | Five-axis staff-level code review.                                |
| `security-auditor`      | Vulnerability detection, threat modeling, OWASP/LLM Top 10.       |
| `test-engineer`         | Test strategy, coverage analysis, gap finding.                    |
| `web-performance-auditor` | Core Web Vitals, loading/rendering/network optimization.        |

## Tech conventions

`.opencode/harness/tech/` ships conventions for 20 stacks (angular, arkts, cpp, csharp, dart,
fsharp, golang, java, kotlin, nuxt, perl, php, python, react, react-native,
ruby, rust, swift, typescript, vue, web) plus a `common` baseline. **Only the
techs listed in `.opencode/harness/rules/tech.md` are active** — the router tells the
agent to lazy-load the matching convention files. The rest stay dormant until you
opt them in. This keeps context lean for any single project while keeping the
full library one edit away.

## Validation

Four gates (all stdlib Python, no dependencies):

```bash
# 1. Markdown reference integrity
python3 .opencode/harness/scripts/check-refs.py

# 2. Frontmatter + tech-dir consistency
python3 .opencode/harness/scripts/lint-frontmatter.py

# 3. Manifest/deprecated consistency (ships vs. declared; no leaks)
python3 scripts/lint-manifest.py

# 4. Installer + manifest-validator tests
python3 -m unittest discover -s tests -v
```

CI runs all four on every push and PR.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add skills, agents,
commands, and tech conventions.

## License

[MIT](LICENSE).
