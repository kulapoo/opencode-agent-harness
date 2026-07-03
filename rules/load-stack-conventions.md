# Load Stack Conventions First

Skills in this harness are language-agnostic: their *principles* are universal,
but the *syntax* for declaring contracts, errors, validation, variant types,
formatting, testing, etc. depends on the project's stack. Before writing or
reviewing code as part of any skill, follow these steps **in order**.

---

## Step 1 — Detect candidate manifests

Find every manifest in the repo (root + subdirectories): `package.json`,
`go.mod`, `Cargo.toml`, `pyproject.toml` / `requirements.txt` / `setup.py`,
`Gemfile`, `composer.json`, `pubspec.yaml`, `Package.swift`, `pom.xml`,
`build.gradle` / `build.gradle.kts`, `*.csproj` / `*.fsproj`, `CMakeLists.txt`,
`build.zig`, `mix.exs`, etc.

If more than one manifest exists → this is a **polyglot repo**. Resolve with
Step 3, not by guessing.

---

## Step 2 — Map the manifest to a `stacks/<dir>/`

Use the file the skill is acting on to pick the row. "Deps" = a key in
`package.json` `dependencies` / `devDependencies`.

### Non-JS/TS (1:1 with language)

| Manifest / signal            | Stack dir    |
| ---------------------------- | ------------ |
| `go.mod`                       | `golang`      |
| `Cargo.toml`                   | `rust`        |
| `pyproject.toml` / `requirements.txt` / `setup.py` | `python` |
| `Gemfile`                       | `ruby`        |
| `composer.json`                 | `php`         |
| `pubspec.yaml` (Flutter/Dart)    | `dart`        |
| `Package.swift`                  | `swift`       |
| `*.csproj` (C#)                | `csharp`      |
| `*.fsproj` or `.fs` files (F#)  | `fsharp`      |
| `CMakeLists.txt` / `.c` / `.cpp` / `.h` | `cpp`   |
| `build.gradle` + `.java`          | `java`        |
| `build.gradle.kts` + `.kt`        | `kotlin`      |
| HarmonyOS project (`oh-package.json5`, `.ets` files) | `arkts` |
| `Makefile.PL` / `cpanfile` / `.pl` | `perl`      |

### JS/TS (framework-aware — check `deps` in priority order)

| Dep key (first match wins)   | Stack dir             | Notes                                  |
| ---------------------------- | --------------------- | -------------------------------------- |
| `expo`, `react-native`         | `react-native`         | Also load `react/` for the web layer.   |
| `nuxt`                         | `nuxt`                 |                                        |
| `@angular/core`                | `angular`              |                                        |
| `vue`                          | `vue`                  |                                        |
| `next`, `remix`, `@remix-run` | `react` + `web`         | Next/Remix are React-meta; no own dir.  |
| `react`, `react-dom`            | `react`                |                                        |
| `svelte`, `@sveltejs/kit`, `astro` | `web` (+ `typescript`) | No dedicated dir; `web` is closest. |
| none of the above, TS present   | `typescript`           |                                        |
| none of the above, JS only      | `typescript`           | Same file set as TS.                    |

**Always also load `common/`** — it holds the universal baselines every stack
extends.

---

## Step 3 — Polyglot resolution (proximity, not "pick one")

When multiple manifests exist, **do not pick a single global stack.** Resolve
per file the skill is editing:

1. From the target file's directory, walk **up** until you find the nearest
   manifest. That manifest's stack (Step 2) wins for that file.
2. If editing root-level config / cross-cutting code with no nearer manifest,
   use the **primary language** = the language with the most source files in
   the repo (or the root manifest).
3. If a single task touches two stacks (e.g. a Rust backend + React frontend
   endpoint), load **both** stack dirs and apply each to its own code. Do not
   mix conventions across the boundary.

---

## Step 4 — Pick the stack files the *skill* needs

Different skills read different stack files. Do **not** blindly read
`patterns.md` for every skill — load what the task actually needs:

| Skill                               | Stack file(s) to read                                            |
| ----------------------------------- | ---------------------------------------------------------------- |
| `api-and-interface-design`            | `<stack>/patterns.md`, `common/patterns.md`                         |
| `test-driven-development`             | `<stack>/testing.md`, `common/testing.md`                           |
| `browser-testing-with-devtools`       | `<stack>/testing.md`                                              |
| `code-review-and-quality`             | `<stack>/coding-style.md`, `<stack>/testing.md`, `common/code-review.md` |
| `code-simplification`                 | `<stack>/coding-style.md`, `common/code-smells.md`                  |
| `security-and-hardening`              | `<stack>/security.md`, `common/security.md`                         |
| `ci-cd-and-automation`                | `<stack>/hooks.md`                                                 |
| `git-workflow-and-versioning`         | `common/git-workflow.md`                                           |
| `frontend-ui-engineering`             | `web/design-quality.md`, `web/coding-style.md`, `<framework>/coding-style.md` |
| `performance-optimization`            | `web/performance.md` (web), `<stack>/patterns.md` (otherwise)      |
| `deprecation-and-migration`           | `<stack>/patterns.md`                                              |
| `observability-and-instrumentation`   | `<stack>/patterns.md`                                              |
| All others                            | `<stack>/coding-style.md` if writing code; else none               |

`<framework>` for frontend skills = the framework dir from Step 2 (`react`,
`vue`, `angular`, `svelte`→`web`, etc.).

---

## Step 5 — Missing stack fallback

If a stack dir listed in Step 2 **does not exist** in this repo:

1. Use the closest present substitute from the table's "Notes" column
   (e.g. Svelte → `web` + `typescript`).
2. If no substitute fits, read `common/` only and write in the target
   language's idioms.
3. Never invent a stack dir or silently proceed with zero stack context.

---

## Quick check

Before producing code, confirm:

- [ ] Manifest(s) detected (Step 1)
- [ ] Each edited file mapped to a stack dir via Step 2
- [ ] Polyglot conflicts resolved by proximity (Step 3)
- [ ] The *skill-specific* stack file(s) loaded — not always `patterns.md` (Step 4)
- [ ] `common/` baselines loaded where the table lists them
