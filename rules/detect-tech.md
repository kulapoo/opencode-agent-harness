# Detect the Project's Tech

Used ONLY by the `init-tech-declaration` skill to generate `rules/tech.md`.
Do NOT run this at session start — read `rules/tech.md` from the system
prompt instead.

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

## Step 2 — Map the manifest to a `tech/<dir>/`

"Deps" = a key in `package.json` `dependencies` / `devDependencies`.

### Non-JS/TS (1:1 with language)

See `tech/MANIFESTS.md` for the manifest → tech-dir table (`go.mod`→`golang`,
`Cargo.toml`→`rust`, `pyproject.toml`→`python`, `Gemfile`→`ruby`, etc.). It's
a flat 1:1 language mapping — load it when a non-JS/TS manifest is detected.

### JS/TS (framework-aware — check `deps` in priority order)

| Dep key (first match wins)   | Tech dir               | Notes                                  |
| ---------------------------- | ---------------------- | -------------------------------------- |
| `expo`, `react-native`         | `react-native`          | Also load `react/` for the web layer.   |
| `nuxt`                         | `nuxt`                  |                                        |
| `@angular/core`                | `angular`               |                                        |
| `vue`                          | `vue`                   |                                        |
| `next`, `remix`, `@remix-run` | `react` + `web`          | Next/Remix are React-meta; no own dir.  |
| `react`, `react-dom`            | `react`                 |                                        |
| `svelte`, `@sveltejs/kit`, `astro` | `web` (+ `typescript`)  | No dedicated dir; `web` is closest.    |
| none of the above, TS present   | `typescript`            |                                        |
| none of the above, JS only      | `typescript`            | Same file set as TS.                    |

**Always also load `common/`** — it holds the universal baselines every tech
dir extends.

---

## Step 3 — Polyglot resolution (proximity, not "pick one")

When multiple manifests exist, **do not pick a single global tech set.**
Resolve per file:

1. From the target file's directory, walk **up** until you find the nearest
   manifest. That manifest's tech (Step 2) wins for that file.
2. If editing root-level config / cross-cutting code with no nearer manifest,
   use the **primary language** = the language with the most source files in
   the repo (or the root manifest).
3. If a single task touches two tech sets (e.g. a Rust backend + React
   frontend endpoint), load **both** tech dirs and apply each to its own code.
   Do not mix conventions across the boundary.
