# Contributing

This is a configuration-only project (markdown, no application code).
Contributions that add or adjust skills, agents, commands, rules, or tech
conventions are all welcome.

## Layout recap

| Folder      | File shape                              |
| ----------- | --------------------------------------- |
| `agents/`   | `<name>.md` with YAML frontmatter.       |
| `commands/` | `<name>.md` with YAML frontmatter.       |
| `skills/`   | `<name>/SKILL.md` (extra files allowed). |
| `rules/`    | `*.md`, loaded on demand by commands.    |
| `tech/`     | `<lang>/*.md`, each with `paths:` frontmatter. |

## Adding things

### A skill

```
skills/<name>/SKILL.md
```

```markdown
---
name: <name>
description: One sentence covering WHAT it does AND WHEN to trigger it. Front-load literal keywords.
---

# <Name>
...
```

- `name` must match the folder name, lowercase-hyphenated.
- `description` is required — skills without one are filtered out.

### An agent

```
agents/<name>.md
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
commands/<name>.md
```

```markdown
---
description: One sentence describing what the command does.
---

# /<name>

(body is the prompt; $ARGUMENTS is the user input)
```

### Tech conventions

Each file under `tech/<lang>/` needs a `paths:` frontmatter so opencode loads
it when a matching file is edited:

```markdown
---
paths:
  - "**/*.rs"
---
# Rust Coding Style
```

`tech/common/` is the only folder without `paths:` — it's the glob-less
baseline referenced explicitly by other tech files.

## Rules of thumb

- **Restart opencode after config changes.** Config loads once at startup;
  a running session keeps the old config until you quit and restart.
- **Wire rules into the commands that own them.** If you add a checklist under
  `rules/`, point the relevant command at it (see how `/ship` Phase B cites
  the `*-checklist.md` files).
- **Don't auto-load every rule.** Keep `.opencode.jsonc` → `instructions`
  lean (currently just `rules/tech.md`). Standing checklists are loaded
  on demand by commands/agents, not forced into every session's context.
- **Reference real files.** Markdown cross-refs must point at files that
  exist. Before submitting, run:

  ```bash
  python3 scripts/check-refs.py
  ```

## Tech declaration

Only techs listed in `rules/tech.md` auto-load. To switch or add an active
stack, either edit that file or run the `init-tech-declaration` skill.
