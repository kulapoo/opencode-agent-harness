# Tech Resolution

This file has been replaced. Tech resolution is now declaration-first:

1. **`rules/tech.md`** — the single source of truth. Lists the project's tech
   (e.g. `rust`, `react`). Injected into the system prompt via `opencode.json`
   `instructions`, so it survives compaction.

2. **Each skill's `## Tech Context` section** — maps the skill to the
   `tech/<name>/` files it needs. The agent reads `rules/tech.md` → substitutes
   `<name>` → reads the listed tech files on demand.

3. **`AGENTS.md`** — includes a re-read guard: before writing code, confirm
   the relevant tech is in context; if not, re-read.

The old manifest-detection machinery (`rules/detect-tech.md`) is now a tool
consumed by the `init-tech-declaration` skill only — use it to generate or
refresh `rules/tech.md`, not at session start.
