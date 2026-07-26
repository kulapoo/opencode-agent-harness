# Changelog

All notable changes to this project are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/), and this project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

_Nothing yet._

## [0.4.1] - 2026-07-26

### Added
- **Color-coded orphan report** in `install` — the deprecated and untracked
  `.opencode/` file sections now render with prominent yellow+bold headers
  and yellow file paths, so the "no longer part of the harness; safe to
  remove" set actually stands out instead of blending into the install
  output. Color is auto-disabled when stdout isn't a TTY (pipes, logs,
  redirects, `curl | python3`), so captured output is unchanged. Honors the
  `NO_COLOR` and `CLICOLOR_FORCE` env vars per the de-facto standards.
- **`install --no-color` / `install --color`** flags — explicit overrides
  (`--no-color` wins when both are passed). Also accepted by `status`.
- **Closing hint for untracked orphans** — the "safe to remove" block now
  ends with `→ not shipped by the harness; safe to delete manually if not
  yours.`, closing the gap where that set listed files but gave no removal
  instruction.

### Changed
- `install.py` docstring `Flags:` section now lists `--prune-deprecated`,
  `--no-color`, and `--color`, and documents the auto-disable-on-pipe
  behavior.

## [0.4.0] - 2026-07-26

### Added
- **`MANIFEST`** — the install set as a hand-maintained, plain-text list of
  every shipped path (one per line). Install is now gated by it: a file under
  `.opencode/` ships only if listed. This structurally prevents the leak that
  let `extract-release-notes.py` escape into downstream installs in 0.3.x.
- **`DEPRECATED`** — a plain-text registry of removed files
  (`path ⇥ removed_in ⇥ reason[ ⇥ replacement]`). When `install` finds a
  downstream file that the current `MANIFEST` no longer tracks, it looks the
  path up here and prints a deprecation explanation instead of silence.
  Seeded with `migrate.md` (removed in 0.3.0) and the leaked
  `extract-release-notes.py`.
- **`scripts/lint-manifest.py`** — a fourth validation gate. Fails if `MANIFEST`
  doesn't exactly match the shippable `.opencode/` tree (catches both "forgot
  to declare a new file" and "declared a file that's gone"), if a path is in
  both `MANIFEST` and `DEPRECATED`, or if a `DEPRECATED` entry still exists in
  the source tree.
- **`install --prune-deprecated`** — opt-in flag that deletes deprecated orphan
  files (those `DEPRECATED` explains) after listing them. Unknown orphans are
  never touched. Default remains warn-only — overwriting and deletion are
  always your explicit decision.
- **Orphan detection** in `install`, `status`, and `/adopt`: files under
  `.opencode/` that the current harness no longer ships are reported.
  `install` gives the full deprecation explanation (it has the source
  `DEPRECATED`); `status` and `/adopt` report them self-contained (no source
  needed) as untracked.

### Changed
- **Install discovery is now MANIFEST-gated** (was: `rglob` over `.opencode/`
  with a skip-list). When a source has no `MANIFEST` (predates 0.4.0, e.g. an
  old `--tag`), install falls back to the `rglob` discoverer with a notice
  that leak protection is inactive — backward compatible.
- **Downstream manifest (`harness.json`) now records only the tracked install
  set**, not everything `rglob` finds on disk. This is what lets `status`
  detect leftover orphans (a file on disk that isn't in the manifest).
- `extract-release-notes.py` moved from `.opencode/harness/scripts/` to
  `scripts/` at the repo root — it is a maintainer-only release tool, never
  meant to ship downstream.

### Migration (from 0.3.0)
- If you have a stale `migrate.md` (or the leaked `extract-release-notes.py`)
  in an existing install, re-running `install` now reports it as a deprecated
  orphan with an explanation. Add `--prune-deprecated` to delete it, or remove
  it by hand. No file moves are required.

## [0.3.0] - 2026-07-26

### Removed
- **`install.py update`** — the sync step that upgraded, pruned, and resurrected
  files is gone. It was the source of two bugs: deleted files reappeared on the
  next run (the "migrate command keeps coming back" symptom), and any drift
  handling relied on a manifest that fought the user's intent.
- **`install.py migrate`** and its migration engine (`MIGRATIONS`, the legacy
  `.opencode/{rules,tech}` → `.opencode/harness/{rules,tech}` relocation
  logic). `install` now materializes the current layout; legacy layouts are not
  auto-relocated.
- **`/migrate` slash command** — it drove the removed engine.
- The migration engine's dedicated test suite (removed with the engine).

### Changed
- **`install` is now idempotent and is the only command that writes files.**
  Re-running it is the refresh path: files whose content already matches the
  harness are left untouched (no-op, not a conflict); any local files that
  differ are reported with a prominent overwrite warning and the run aborts
  unless you pass `--force` (overwrite) or `--skip-existing` (keep yours).
  Overwriting is always the user's explicit decision. There is no longer a
  separate guard that refuses to re-run when a manifest exists.
- `/adopt` dropped its legacy-layout detection step (it delegated to the removed
  `migrate`) and its manifest note no longer references `update`.
- `status` now reports "Newer harness available: \<tag\> (re-run install to
  refresh)" instead of "Update available".

### Migration (from 0.2.0)
- No file moves are required — the layout is unchanged. To refresh an existing
  install, re-run `install` from the same source. If you previously deleted
  shipped files (e.g. `migrate.md`) and want them gone for good, there is now
  no mechanism that brings them back; if any reappear during this one
  transition, delete them once more — future installs won't resurrect them.
- If you depended on `install.py update` or `install.py migrate` in scripts,
  replace those calls with `install.py install` (optionally `--force`).

## [0.2.0] - 2026-07-25

### Added
- **One-command install via `curl | python3`** — the installer is now
  reachable pinned to a tag at
  `https://raw.githubusercontent.com/kulapoo/opencode-agent-harness/v0.2.0/install.py`,
  so adopting the harness into a new project no longer requires `git clone`
  first. See README § Quick start. The same pattern works for `update` and
  `status`: `curl … | python3 - update`.
- **`install.py --version`** — prints the installer's own version
  (`git describe` of its source tree, e.g. `v0.1.0` or
  `v0.1.0-3-gabc123-dirty`; `unknown` outside a git repo). Helps debug a stale
  installer before an update fails confusingly.
- **Invocation-aware post-install hint** — after `install`, the output tells
  you exactly how to reach the installer again for `update`/`status`. If
  invoked from a file path (clone user), it prints
  `python3 /abs/path/install.py status`; if piped via stdin (`curl | python3 -`
  user), it prints the curl one-liner. Closes the "where is install.py later?"
  gotcha at the moment you need it.
- Test coverage for `--version` and both invocation modes (4 new unittests).
- **`/how-to-guide` command + consolidated FAQ reference** — a new conversational slash command that walks users through the harness's workflow, artifacts, and philosophy. Backed by `.opencode/harness/references/how-to-guide.md` (new `references/` dir) holding 9 distilled entries: resuming after a break, phase meaning, file roles, vertical slicing, methodology fit, `/spec` inputs, ROADMAP/VISION compatibility, commit-message convention, and OSS adoption. The command converses (offers categories, re-explains in its own words, offers follow-ups) rather than dumping the reference.

### Changed
- `/adopt` manifest guidance clarified: `install.py` lives in the harness source
  repo (never copied downstream), so `update`/`status` are run via its absolute
  path; a `local` version means a local-clone install, not an error.
- README § Quick start rewritten: one-liner is now the primary install path,
  with an inspect-first variant for cautious environments and the clone path
  retained as an auditable fallback. § Updating rewritten to cover both
  one-liner and clone re-invocation patterns.

### Fixed
- Directory sources now stamp a meaningful version (`git describe --tags --always
  --dirty`, e.g. `v0.1.0-3-gabc123`) into the manifest instead of the bare
  `local` label. Falls back to `local` when the source isn't a git repo.

## [0.1.0] - 2026-07-24

First tagged release. Breaking changes from the pre-release layout — see
migration notes below.

### Added
- **Installer** (`install.py`) — one-command install, manifest-tracked updates
  with drift preservation, and status reporting. Supports `--from <dir|tarball>`
  for offline/CI use.
- **Lazy-load tech router** — `.opencode/harness/rules/tech.md` is now a router
  that tells the agent which convention files to Read per stack, replacing the
  false `paths:` auto-load assumption. Tech conventions actually load now.
- **Frontmatter linter** (`.opencode/harness/scripts/lint-frontmatter.py`) —
  validates skill/agent/command frontmatter per opencode's documented rules and
  cross-checks detect-tech.md mappings against actual `tech/` directories.
- **Installer test suite** (`tests/`) — 14 unittest cases covering install,
  conflict detection, update drift preservation, and status reporting.
- **CI** (`.github/workflows/ci.yml`) — runs check-refs, lint-frontmatter, and
  tests on every push and PR.
- **Issue templates** — bug report, tech-convention proposal, skill proposal.
- **PR template** with validation checklist.
- Framework hints in detect-tech.md (FastAPI, Django, Flask, Rails, Laravel).
- Opt-in always-load for single-stack projects via `instructions` globs.
- `paths:` frontmatter added to all `tech/rust/*.md` files.

### Changed
- **Layout migration**: `agents/`, `commands/`, `skills/` moved under `.opencode/`;
  `rules/`, `tech/`, `scripts/` moved under `.opencode/harness/`. Root keeps only
  README, AGENTS.md, CONTRIBUTING, LICENSE, CHANGELOG, install.py.
- `/adopt` now handles all config filename variants (`opencode.json`,
  `opencode.jsonc`, `.opencode.jsonc`), detects legacy root-level layouts and
  offers migration, and includes manifest-aware health summary + post-adopt
  verification step.
- README, AGENTS.md, CONTRIBUTING.md, and tech/README.md corrected: no longer
  claim `paths:` frontmatter triggers opencode auto-loading.
- `chrome-devtools` MCP is no longer wired by default (opt-in per project).

### Migration (from pre-release root-level layout)
1. Run `python3 install.py install --from <this-repo>` to get the new layout.
2. Or manually: `git mv agents .opencode/agents` etc., then update path
   references and run `python3 .opencode/harness/scripts/check-refs.py`.
3. Run `/adopt` — it detects legacy layouts and offers migration.

> **Easier now:** if your project has `.opencode/rules/` or `.opencode/tech/`
> (the pre-harness-tree layout), run `/migrate` (or
> `python3 install.py migrate --from <this-repo> --dry-run`) — it handles the
> relocation, orphan cleanup, config path, and tech-router port in one shot.
