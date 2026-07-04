# Conventions Resolution

This file has been replaced. Convention resolution is now declaration-first:

1. **`rules/tech-conventions.md`** — the single source of truth. Lists the
   project's tech conventions (e.g. `rust`, `react`). Injected into the system
   prompt via `opencode.json` `instructions`, so it survives compaction.

2. **Each skill's `## Conventions Context` section** — maps the skill to the
   `conventions/<name>/` files it needs. The agent reads
   `rules/tech-conventions.md` → substitutes `<name>` → reads the listed
   convention files on demand.

3. **`AGENTS.md`** — includes a re-read guard: before writing code, confirm
   conventions are in context; if not, re-read.

The manifest-detection machinery
(`skills/init-conventions-declaration/detect-conventions.md`) is a tool
consumed by the `init-conventions-declaration` skill only — use it to
generate or refresh `rules/tech-conventions.md`, not at session start.
