# Rules

## Structure

Rules are organized into a **common** layer plus **language-specific** directories:

```
rules/
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
│   ├── performance.md
│   ├── security.md
│   ├── development-workflow.md
│   ├── hooks.md
│   └── agents.md
├── typescript/      # TypeScript/JavaScript specific
├── angular/         # Angular specific
├── vue/             # Vue 3 specific
├── nuxt/            # Nuxt 4 specific
├── python/          # Python specific
├── golang/          # Go specific
├── web/             # Web and frontend specific
├── react-native/    # React Native / Expo specific
├── swift/           # Swift specific
├── php/             # PHP specific
├── ruby/            # Ruby / Rails specific
└── arkts/           # HarmonyOS / ArkTS specific
```

- **common/** contains universal principles — no language-specific code examples.
- **Language directories** extend the common rules with framework-specific patterns, tools, and code examples. Each file references its common counterpart.

## Installation

### Option 1: Install Script (Recommended)

```bash
# Install common + one or more language-specific rule sets
./install.sh typescript
./install.sh angular
./install.sh vue
./install.sh nuxt
./install.sh python
./install.sh golang
./install.sh web
./install.sh react-native
./install.sh swift
./install.sh php
./install.sh ruby
./install.sh arkts

# Install multiple languages at once
./install.sh typescript python
```

### Option 2: Manual Installation

> **Important:** Copy entire directories — do NOT flatten with `/*`.
> Common and language-specific directories contain files with the same names.
> Flattening them into one directory causes language-specific files to overwrite
> common rules, and breaks the relative `../common/` references used by
> language-specific files.
>
> Use the ECC-owned namespace below for user-level opencode installs. Flat
> package-level destinations can collide with non-ECC rule packs and do not
> match the main README guidance.

```bash
# Create the ECC rule namespace once.
mkdir -p ~/.opencode/rules/ecc

# Install common rules (required for all projects)
cp -r rules/common ~/.opencode/rules/ecc/

# Install language-specific rules based on your project's tech stack
cp -r rules/typescript ~/.opencode/rules/ecc/
cp -r rules/angular ~/.opencode/rules/ecc/
cp -r rules/vue ~/.opencode/rules/ecc/
cp -r rules/nuxt ~/.opencode/rules/ecc/
cp -r rules/python ~/.opencode/rules/ecc/
cp -r rules/golang ~/.opencode/rules/ecc/
cp -r rules/web ~/.opencode/rules/ecc/
cp -r rules/react-native ~/.opencode/rules/ecc/
cp -r rules/swift ~/.opencode/rules/ecc/
cp -r rules/php ~/.opencode/rules/ecc/
cp -r rules/ruby ~/.opencode/rules/ecc/
cp -r rules/arkts ~/.opencode/rules/ecc/

# Attention ! ! ! Configure according to your actual project requirements; the configuration here is for reference only.
```

For project-local rules, use the same namespace under the project root:

```bash
mkdir -p .opencode/rules/ecc
cp -r rules/common .opencode/rules/ecc/
cp -r rules/typescript .opencode/rules/ecc/
```

## Rules vs Skills

- **Rules** define standards, conventions, and checklists that apply broadly (e.g., "80% test coverage", "no hardcoded secrets").
- **Skills** (`skills/` directory) provide deep, actionable reference material for specific tasks (e.g., `python-patterns`, `golang-testing`).

Language-specific rule files reference relevant skills where appropriate. Rules tell you _what_ to do; skills tell you _how_ to do it.

## Adding a New Language

To add support for a new language (e.g., `rust/`):

1. Create a `rules/rust/` directory
2. Add files that extend the common rules:
   - `coding-style.md` — formatting tools, idioms, error handling patterns
   - `testing.md` — test framework, coverage tools, test organization
   - `patterns.md` — language-specific design patterns
   - `hooks.md` — PostToolUse hooks for formatters, linters, type checkers
   - `security.md` — secret management, security scanning tools
3. Each file should start with a **RELEVANT baselines** header that links
   the baselines it depends on (see "Composition — Referencing Baselines"
   below), then add only language-specific deltas.
4. Reference existing skills if available, or create new ones under `skills/`.

For non-language domains like `web/`, follow the same layered pattern when there is enough reusable domain-specific guidance to justify a standalone ruleset.

## Rule Priority

When language-specific rules and common rules conflict, **language-specific rules take precedence** (specific overrides general). This follows the standard layered configuration pattern (similar to CSS specificity or `.gitignore` precedence).

- `rules/common/` defines universal defaults applicable to all projects.
- `rules/golang/`, `rules/python/`, `rules/swift/`, `rules/php/`, `rules/typescript/`, `rules/react-native/`, etc. override those defaults where language idioms differ.

### Example

`common/coding-style.md` recommends immutability as a default principle. A language-specific `golang/coding-style.md` can override this:

> Idiomatic Go uses pointer receivers for struct mutation — see [common/coding-style.md](../common/coding-style.md) for the general principle, but Go-idiomatic mutation is preferred here.

### Common rules with override notes

Rules in `rules/common/` that may be overridden by language-specific files are marked with:

> **Language note**: This rule may be overridden by language-specific rules for languages where this pattern is not idiomatic.

## Composition — Referencing Baselines

The baseline files in `common/` (`principles.md`, `naming.md`, `functions.md`,
`formatting.md`, `comments.md`, `error-handling.md`, `code-smells.md`) hold
universal guidance. **Language-specific files reference them instead of restating
them**, then add only the deltas (tooling, idioms, conventions).

A language-specific file declares which baselines are **RELEVANT** in a header
block, then continues with language-specific content:

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
  conflict, the language rule wins (see Rule Priority above).
- **Common rules with override notes**: baseline files that languages may
  override are marked with the `Language note` callout shown above.
