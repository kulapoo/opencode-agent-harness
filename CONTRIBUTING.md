# Contributing

This is a markdown-first project — skills, agents, commands, rules, and tech
conventions are all markdown. The only executables are `install.py` (the
installer) and two stdlib-only Python validators under
`.opencode/harness/scripts/`. Contributions that add or adjust any of these
are welcome.

## Layout recap

| Folder      | File shape                              |
| ----------- | --------------------------------------- |
| `.opencode/agents/`   | `<name>.md` with YAML frontmatter.       |
| `.opencode/commands/` | `<name>.md` with YAML frontmatter.       |
| `.opencode/skills/`   | `<name>/SKILL.md` (extra files allowed). |
| `.opencode/harness/rules/`    | `*.md`, loaded on demand by commands.    |
| `.opencode/harness/tech/`     | `<lang>/*.md`, each with `paths:` frontmatter. |
| `.opencode/harness/scripts/`  | `check-refs.py`, `lint-frontmatter.py` (stdlib Python). |
| `tests/`     | Installer unittest suite. |

## Adding things

### A skill

```
.opencode/skills/<name>/SKILL.md
```

```markdown
---
name: <name>
description: One sentence covering WHAT it does AND WHEN to trigger it. Front-load literal keywords.
---

# <Name>
...
```

- `name` must match the folder name, lowercase-hyphenated (`^[a-z0-9]+(-[a-z0-9]+)*$`).
- `description` is required (1–1024 chars) — skills without one are filtered out.

### An agent

```
.opencode/agents/<name>.md
```

```markdown
---
name: <name>
description: ...
mode: subagent
---
```

- Use `mode: subagent` for specialists that other commands fan out to.
- The file body becomes the agent's prompt.

### A command

```
.opencode/commands/<name>.md
```

```markdown
---
description: One sentence describing what the command does.
---

# /<name>

(body is the prompt; $ARGUMENTS is the user input)
```

### Tech conventions

Each file under `.opencode/harness/tech/<lang>/` needs a `paths:` frontmatter
glob for documentation and future cross-tool export:

```markdown
---
paths:
  - "**/*.rs"
---
# Rust Coding Style
```

`.opencode/harness/tech/common/` is the only folder without `paths:` — it's
the baseline referenced explicitly by other tech files. opencode does not
auto-inject on glob match; the `.opencode/harness/rules/tech.md` router drives
lazy loading instead.

When adding a new `<lang>/` dir, also add a mapping row in
`.opencode/skills/init-tech-declaration/detect-tech.md` so `/adopt` can detect
it. The consistency checker (below) validates this bidirectionally.

## Rules of thumb

- **Restart opencode after config changes.** Config loads once at startup;
  a running session keeps the old config until you quit and restart.
- **Wire rules into the commands that own them.** If you add a checklist under
  `.opencode/harness/rules/`, point the relevant command at it (see how `/ship`
  Phase B cites the `*-checklist.md` files).
- **Don't auto-load every rule.** Keep the config `instructions` lean
  (currently just `.opencode/harness/rules/tech.md`). Standing checklists are
  loaded on demand by commands/agents, not forced into every session's context.
- **Reference real files.** Markdown cross-refs must point at files that exist.

## Validation

Before submitting, all three gates must pass:

```bash
python3 .opencode/harness/scripts/check-refs.py
python3 .opencode/harness/scripts/lint-frontmatter.py
python3 -m unittest discover -s tests -v
```

CI runs all three automatically on push and PR.

## Tech declaration

Only techs listed in `.opencode/harness/rules/tech.md` are active — the router
lazy-loads their conventions. To switch or add an active stack, either edit
that file or run the `init-tech-declaration` skill.
