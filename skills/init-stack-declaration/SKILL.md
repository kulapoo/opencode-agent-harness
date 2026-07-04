---
name: init-stack-declaration
description: Detects the project's stack(s) and writes a `## Stack` section
  into AGENTS.md so future sessions skip manifest detection (Step 0 fast path).
  Run once when adopting the harness, and again whenever the stack changes.
  Triggers on "init stack", "declare my stack", "refresh stack declaration".
---

# Init Stack Declaration

Generates or refreshes the `## Stack` declaration in AGENTS.md. Pays the
detection cost once so every future session skips `rules/detect-stack.md`.

## When to Use

- First time adopting this harness on a project
- Adding or removing a stack (e.g. new frontend, dropped service)
- After Step 0's sanity check flags drift ("declaration says rust, edited a .py")
- Major refactor that restructured directories

## Steps

1. Run `rules/detect-stack.md` (manifest glob + proximity, Steps 1–3).
2. Decide output format based on what was detected:
   - **One stack** → single line: `rust`
   - **Multiple, separable by path** → path-mapped:
     ```
     - rust:    src/**, crates/**
     - react:   web/**, app/**
     ```
   - **Multiple, interleaved** → list only: `stacks: rust, react`
3. Embed a fingerprint comment listing the **relevant** manifests detected.
   Skip manifests in ancillary directories — `vendor/`, `node_modules/`,
   `third_party/`, `examples/`, `demo/`, `fixtures/`, etc. — they cause false
   drift signals later.
   ```
   <!-- manifests: Cargo.toml, web/package.json -->
   ```
4. If AGENTS.md already has a `## Stack` section, replace it (preserving the
   fingerprint comment). Else append a new section.
5. Show the user a diff before writing. Do not silently modify AGENTS.md.
6. Report which stack dirs will load on next session, and any stacks that
   have no corresponding `stacks/<dir>/` (Step 2 fallback will apply).

## Output

A `## Stack` section in AGENTS.md. Example:

````markdown
## Stack
- rust:    src/**, crates/**
- react:   web/**

<!-- manifests: Cargo.toml, web/package.json -->
````

## Notes

- Safe to re-run; idempotent.
- The fingerprint comment lets a future session detect drift with one glob.
- If detection finds nothing recognizable, write `## Stack` with `common/`
  only, and warn the user that no stack-specific conventions will apply.
