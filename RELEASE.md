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
# Install into a throwaway dir, verify idempotency, then test divergence.
python3 install.py install --from .    # in a tmp project
python3 install.py status
# Re-running install is a no-op when files match:
python3 install.py install --from .
# Modify a file; plain install now aborts with an overwrite warning:
python3 install.py install --from .            # rc=1, lists the divergence
python3 install.py install --from . --force    # overwrites
python3 install.py install --from . --skip-existing   # keeps your edit
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

**Order matters:** version pins must be bumped *before* the release commit/tag,
so the tag at `vX.Y.Z` actually contains `vX.Y.Z` pins (the installer served at
that tag prints hints pointing at itself, not the previous release).

1. **Bump version pins** (`vOLD` → `vNEW`) in:
   - `install.py` → `INSTALLER_URL`
   - `README.md` → every one-liner tag (Quick start + Refreshing sections)
   - Verify nothing was missed: `rg -n 'vOLD' install.py README.md` → clean.
2. **CHANGELOG** — rename `## [Unreleased]` → `## [X.Y.Z] - YYYY-MM-DD` and add
   a fresh `## [Unreleased]` with `_Nothing yet._` above it.
3. **Re-run the gates** from §1 to confirm the version edits didn't break anything.
4. **Commit and tag** (separate from the feature commit):
   ```bash
   git add -A
   git commit -m "release: vX.Y.Z"
   git tag -a vX.Y.Z -m "vX.Y.Z — <one-line summary>"
   ```
5. **Push** main and the tag:
   ```bash
   git push origin main
   git push origin vX.Y.Z
   ```
6. **Publish the GitHub Release** (required, not optional — see note below).

**Publishing the GitHub Release is required, not optional.** The README's
install one-liner resolves from the tag via `raw.githubusercontent.com`
(works whether or not a Release object exists), but the Release itself is
what users see on the repo's home page and what `gh release view` / the
GitHub "Releases" sidebar surface. Skip it and the project looks unreleased.

Extract the top-most CHANGELOG section as the notes via the helper script
(`.opencode/harness/scripts/extract-release-notes.py`), then create the release.
The script keeps the shell command single-line and paste-safe — no inline
Python with parens that break on paste:

```bash
gh release create vX.Y.Z --title "vX.Y.Z — <summary>" \
  --notes "$(python3 .opencode/harness/scripts/extract-release-notes.py)"
```

(Substitute `vX.Y.Z` in the tag and title — those are the only edits.)

**Versioning:** breaking change (removed/renamed commands) = minor bump on 0.x
(`v0.3.0`); additive = patch (`v0.3.1`).

## 6. Verify the loop is closed

```bash
gh release list --limit 3                       # new release shows "Latest"
curl -fsSL …/vX.Y.Z/install.py | head           # serves the new installer
```
