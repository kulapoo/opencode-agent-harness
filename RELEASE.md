# Release Checklist

Pre-tag ritual for maintainers. opencode behavior is LLM-driven and can't be
fully CI-tested — the steps marked **[manual]** require human or LLM verification.

## 1. Automated gates (must pass)

```bash
python3 .opencode/harness/scripts/check-refs.py
python3 .opencode/harness/scripts/lint-frontmatter.py
python3 -m unittest discover -s tests -v
```

All three must exit 0.

## 2. Installer self-test [automated]

```bash
# Install into a throwaway dir, verify, then update with a modified file
python3 install.py install --from .    # in a tmp project
python3 install.py status
# modify a file, then:
python3 install.py update --from .     # should preserve the modification
```

## 3. opencode discovery smoke test [manual]

In a scratch project with an installed harness:

- [ ] `/adopt`, `/spec`, `/build`, `/review`, `/ship` appear in the `/` command list
- [ ] `@code-reviewer`, `@security-auditor`, `@test-engineer` appear in `@` autocomplete
- [ ] Skills are discoverable (the agent cites them when relevant)
- [ ] `.opencode/harness/rules/tech.md` router content is visible in a new session
- [ ] Editing a Rust file triggers the agent to Read `tech/rust/*.md` (router compliance)

## 4. Dogfood check [manual]

- [ ] `/adopt` runs cleanly on at least 2 real projects (different stacks)
- [ ] No context-budget regressions (router stays lean)
- [ ] `/ship` fan-out works (parallel subagent dispatch)

## 5. Tag and release

```bash
# Update CHANGELOG date, then:
git add -A && git commit -m "release: v0.1.0"
git tag v0.1.0
git push origin main --tags
# Create GitHub release from the tag, pasting the CHANGELOG entry.
```

**Publishing the GitHub Release is required, not optional.** The README's
install one-liner resolves from the tag via `raw.githubusercontent.com`
(works whether or not a Release object exists), but the Release itself is
what users see on the repo's home page and what `gh release view` / the
GitHub "Releases" sidebar surface. Skip it and the project looks unreleased.

```bash
gh release create v0.1.0 --title "v0.1.0 — <summary>" \
  --notes "$(git tag -l --format='%(contents:subject)' v0.1.0)"
```

After publishing, bump the `INSTALLER_URL` constant in `install.py` and the
tag in the README one-liner to point at the new tag, so documentation and the
post-install hint stay in sync with what users actually run.
