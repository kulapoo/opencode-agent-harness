---
name: init-conventions-declaration
description: Detects the project's tech conventions and writes a
  `rules/tech-conventions.md` file so future sessions skip runtime detection.
  Run once when adopting the harness, and again whenever the conventions
  change. Triggers on "init conventions", "declare my conventions", "refresh
  conventions declaration".
---

# Init Conventions Declaration

Generates or refreshes `rules/tech-conventions.md` — the single source of
truth for the project's tech conventions. This file is injected into the
system prompt via `opencode.json` `instructions` and survives compaction.

## When to Use

- First time adopting this harness on a project
- Adding or removing a convention set (e.g. new frontend, dropped service)
- Drift detected ("declaration says rust, but .py files are being edited")
- Major refactor that restructured directories

## Steps

1. Run detect-conventions.md (manifest glob + proximity, Steps 1–3) from this
   skill's directory:
   `Read skills/init-conventions-declaration/detect-conventions.md`.
2. Map detected conventions to dir names (e.g. `Cargo.toml` → `rust`,
   `package.json` with `react` dep → `react`). Both the JS/TS framework
   table and the non-JS/TS manifest table live inline in
   detect-conventions.md — no external manifest map to consult.
3. Write the result to `rules/tech-conventions.md`:
   ```
   ## Conventions
   - rust
   - typescript
   - react
   ```
4. If AGENTS.md has no `instructions` block, add one:
   ```json
   "instructions": ["rules/tech-conventions.md"]
   ```
5. Show the user a diff before writing. Do not silently modify files.
6. Report which convention dirs load next session, and any that have no
   corresponding `conventions/<dir>/`.

## Output

A `rules/tech-conventions.md` file. Example:

```markdown
## Conventions
- rust
- react
```

And a `"instructions": ["rules/tech-conventions.md"]` entry in `opencode.json`.

## Notes

- Safe to re-run; idempotent.
- If detection finds nothing recognizable, write `## Conventions` with only
  `common` and warn the user.
- The detection machinery (`detect-conventions.md`) is a tool, not a runtime
  step.
