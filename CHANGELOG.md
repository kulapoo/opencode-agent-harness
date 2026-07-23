# Changelog

All notable changes to this project are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/), and this project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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
