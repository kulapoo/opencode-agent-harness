# Stacks

Codable rulesets for the OpenCode Agent Harness. A **common** baseline of
universal principles plus **language/framework-specific** stacks that extend it
with idioms, tooling, and code examples.

## Structure

```
stacks/
├── common/          # Language-agnostic baselines + workflow rules (always install)
│   # ── Baseline files (single-concern, referenced by stacks) ──
│   ├── principles.md          # Boy Scout, KISS/DRY/YAGNI, Law of Demeter, emergence
│   ├── naming.md              # Intention-revealing names
│   ├── functions.md           # Small, do-one-thing, argument discipline
│   ├── formatting.md          # Vertical/horizontal formatting, file org
│   ├── comments.md            # Self-documenting code; good vs bad comments
│   ├── error-handling.md      # Signal over return codes, boundaries
│   ├── code-smells.md         # Heuristics catalog
│   # ── Workflow & domain rules ──
│   ├── coding-style.md        # Thin index → the baselines above
│   ├── code-review.md         # Consolidated Code Quality Checklist
│   ├── testing.md             # Coverage, TDD, F.I.R.S.T.
│   ├── patterns.md            # SRP, DI, boundaries, repository
│   ├── git-workflow.md
│   ├── security.md
│   ├── development-workflow.md
│   └── agents.md
│
├── typescript/      # TypeScript / JavaScript
├── react/           # React
├── react-native/    # React Native / Expo
├── vue/             # Vue 3
├── nuxt/            # Nuxt 4
├── angular/         # Angular
├── web/             # Web / frontend (framework-agnostic)
├── python/          # Python (+ FastAPI)
├── golang/          # Go
├── rust/            # Rust
├── ruby/            # Ruby / Rails
├── php/             # PHP
├── java/            # Java
├── kotlin/          # Kotlin
├── swift/           # Swift
├── arkts/           # HarmonyOS / ArkTS
├── csharp/          # C# / .NET
├── fsharp/          # F#
├── cpp/             # C / C++
├── dart/            # Dart / Flutter
└── perl/            # Perl
```

- **common/** holds universal principles — no language-specific code examples.
- **Each stack** ships a consistent set of five files:
  `coding-style.md`, `testing.md`, `patterns.md`, `hooks.md`, `security.md`.
- A few stacks add domain-specific extras, e.g. `python/fastapi.md`,
  `react-native/{accessibility,performance,production-readiness}.md`,
  `web/{design-quality,performance}.md`.

## Installation

There is no install script — copy the directories you need. Pick a destination
that matches how you want the rules consumed (project-local vs. user-global).

> **Important:** Copy entire directories — do NOT flatten with `/*`. Common and
> stack directories contain files with the same names; flattening lets a stack
> overwrite the common rules and breaks the relative `../common/` references
> each stack uses.

### Project-local (recommended for this harness)

Place rules alongside the agent config so they travel with the repo:

```bash
# Common is required by every stack
mkdir -p .opencode/rules
cp -r stacks/common .opencode/rules/

# Then add the stacks your project actually uses
cp -r stacks/typescript .opencode/rules/
cp -r stacks/rust      .opencode/rules/
```

### User-global

Share rules across all your OpenCode projects from a single namespace:

```bash
mkdir -p ~/.opencode/rules
cp -r stacks/common    ~/.opencode/rules/
cp -r stacks/typescript ~/.opencode/rules/
```

> Configure according to your actual project requirements; the examples above
> are for reference only.

## Rules vs Skills

This harness pairs two kinds of guidance:

- **Stacks** (this directory) define standards, conventions, and checklists that
  apply broadly within a language/framework (e.g. "80% test coverage", "no
  hardcoded secrets").
- **Skills** (`skills/` at the repo root) provide deep, task-oriented workflows
  loaded on demand via the skill tool — e.g. `test-driven-development`,
  `frontend-ui-engineering`, `security-and-hardening`,
  `performance-optimization`, `code-review-and-quality`.

Stack files reference relevant skills where appropriate. Rules tell you _what_
to do; skills tell you _how_ to do it.

## Rule Priority

When a stack and `common/` conflict, **the stack wins** (specific overrides
general) — the same layered-precedence pattern as CSS specificity or
`.gitignore`.

- `stacks/common/` defines universal defaults.
- `stacks/<lang>/` overrides those defaults wherever language idioms differ.

### Example

`common/coding-style.md` recommends immutability as a default. A stack may
override it:

> Idiomatic Go uses pointer receivers for struct mutation — see
> [common/coding-style.md](common/coding-style.md) for the general principle,
> but Go-idiomatic mutation is preferred here.

### Common rules with override notes

Baselines in `common/` that languages may legitimately override are marked:

> **Language note**: This rule may be overridden by language-specific rules for
> languages where this pattern is not idiomatic.

## Composition — Referencing Baselines

The baseline files in `common/` (`principles.md`, `naming.md`, `functions.md`,
`formatting.md`, `comments.md`, `error-handling.md`, `code-smells.md`) hold
universal guidance. **Stack files reference them instead of restating them**,
then add only their deltas (tooling, idioms, conventions).

A stack file declares which baselines are **RELEVANT** in a header block, then
continues with language-specific content:

```md
# Rust Coding Style

> **RELEVANT baselines** (apply universally — do not restate):
>
> - [../common/principles.md](../common/principles.md)
> - [../common/naming.md](../common/naming.md)
> - [../common/functions.md](../common/functions.md)
> - [../common/formatting.md](../common/formatting.md)
> - [../common/error-handling.md](../common/error-handling.md)
> - [../common/code-smells.md](../common/code-smells.md)
>
> This file adds **Rust-specific deltas** on top of those baselines.

## Naming
...language-specific casing conventions...
```

See [`rust/coding-style.md`](rust/coding-style.md) for the reference implementation.

### Rules of thumb

- **Link, don't duplicate.** If a rule applies universally, it belongs in a
  baseline; the stack links to it. The stack restates only what is genuinely
  different in that language.
- **Deltas are idiomatic.** A casing convention, a formatter command, an error
  type, a borrow-checker idiom — these are deltas. "Functions should be small"
  is not; it lives in `common/functions.md`.
- **Specific overrides general.** When a baseline and a language idiom genuinely
  conflict, the stack wins (see Rule Priority above).
- **Common rules with override notes**: baseline files that stacks may override
  are marked with the `Language note` callout shown above.

## Adding a New Stack

To add support for a new language or framework (e.g. `elixir/`):

1. Create a `stacks/elixir/` directory.
2. Add the standard five files, each extending the common rules:
   - `coding-style.md` — formatter, idioms, error-handling patterns
   - `testing.md` — test framework, coverage tools, test organization
   - `patterns.md` — language-specific design patterns
   - `hooks.md` — PostToolUse hooks for formatters, linters, type checkers
   - `security.md` — secret management, security scanning tools
3. Each file starts with a **RELEVANT baselines** header linking the baselines
   it depends on (see "Composition — Referencing Baselines" above), then adds
   only language-specific deltas.
4. Reference existing skills if available, or propose new ones under `skills/`.
5. Add the new directory to the tree listing at the top of this README.

For non-language domains (like `web/`), follow the same layered pattern when
there is enough reusable domain-specific guidance to justify a standalone
stack.
