---
description: Adopt the harness into a project — detect tech, wire config, scaffold the agent map. Run once on setup, re-run as a health check
---

# /adopt

The front door. Bring the harness into a project (or reconcile an existing
setup), then hand off to `/spec`. Idempotent — safe to re-run; it fills gaps
and reports drift rather than overwriting.

> Named `/adopt`, not `/init`: opencode ships a built-in `/init`, and a custom
> command of the same name would shadow it with no way back. `/adopt` is the
> harness-specific equivalent.

## What it reconciles

Three things make a project harness-ready. Fill each, never silently overwrite
(the `init-tech-declaration` rule: show a diff first):

1. **Tech declaration** — orchestrate the `init-tech-declaration` skill:
   detect manifests, map to `tech/<dir>/`, write `rules/tech.md`. This is the
   single source of truth injected into every session.
2. **Config wiring** — ensure `.opencode.jsonc` has
   `"instructions": ["rules/tech.md"]` (the skill's step 4 handles this).
   Leave every other key (MCP, agents, models) untouched.
3. **Agent map** — scaffold the project `AGENTS.md` from
   `skills/init-tech-declaration/AGENTS.template.md`, following the
   [agents.md](https://agents.md/) standard. Kept as a lean index (see
   `context-engineering` § Rules File Lifecycle).

## AGENTS.md handling (non-destructive)

- **Absent** → scaffold a project map from the template; fill the
  `<PLACEHOLDER>`s by asking the user for the project name, build/test/lint
  commands, and boundaries.
- **Present + matches the stock-harness signature** (H1 `# OpenCode Agent
  Harness` together with the phrase `no multi-harness fragmentation`) → it's
  the harness's own map, not this project's. Offer to replace it with a
  project map; show the diff; write only on explicit confirmation.
- **Present + already customized** → preserve it. Note any missing
  agents.md-standard sections; do not rewrite.

## Steps

1. **Guard.** Confirm the harness folders are present (`skills/`, `rules/`,
   `commands/`). If not, stop — `/adopt` configures an *existing* harness, it
   doesn't fetch one. Point the user to `README.md` § Quick start.
2. **Tech + config.** Run `init-tech-declaration` (detect-tech →
   `rules/tech.md` → `.opencode.jsonc` wiring), following its diff-first rule.
3. **Agent map.** Reconcile `AGENTS.md` per the handling above. When
   scaffolding, ask the user for the project name, build/test/lint commands,
   and any hard boundaries, then fill the template.
4. **Health summary.** Report: tech detected; `tech/<dir>/` dirs that exist vs
   missing (missing → falls back to `common/`); `.opencode.jsonc` wiring
   present; `AGENTS.md` status.
5. **Hand off.** Suggest `/spec` to define what to build, or `/planning` if a
   spec already exists. Run `python3 scripts/check-refs.py` if any `.md` was
   added or moved.
