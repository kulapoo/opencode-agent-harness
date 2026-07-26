"""Installer test suite — validates install, idempotency, and conflict behavior.

Run:  python3 -m pytest tests/test_installer.py
  or:  python3 -m unittest tests.test_installer
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

INSTALLER = Path(__file__).resolve().parent.parent / "install.py"


def make_source(base: Path, name: str = "source") -> Path:
    """Create a minimal harness source with .opencode/ structure."""
    src = base / name
    oc = src / ".opencode"

    (oc / "agents").mkdir(parents=True)
    (oc / "agents" / "reviewer.md").write_text("---\ndescription: test\n---\nbody v1")

    (oc / "commands").mkdir(parents=True)
    (oc / "commands" / "ship.md").write_text("---\ndescription: test\n---\nbody v1")

    (oc / "skills" / "spec-driven-development").mkdir(parents=True)
    (oc / "skills" / "spec-driven-development" / "SKILL.md").write_text(
        "---\nname: spec-driven-development\ndescription: test\n---\nbody v1"
    )

    (oc / "harness" / "rules").mkdir(parents=True)
    (oc / "harness" / "rules" / "tech.md").write_text("## Tech\n- python\n")

    # Local-only scaffolding at the .opencode/ root that must never ship.
    (oc / ".gitignore").write_text("node_modules\n")
    (oc / "package.json").write_text('{"dependencies": {}}\n')
    (oc / "package-lock.json").write_text("{}\n")
    (oc / "bun.lock").write_text("{}\n")

    # v0.4.0+: the source declares its install set via MANIFEST. Listing the
    # four shippable files above makes the manifest-gated path the default for
    # every test. (Legacy sources without MANIFEST are covered by
    # TestLegacyFallback.)
    (src / "MANIFEST").write_text(
        ".opencode/agents/reviewer.md\n"
        ".opencode/commands/ship.md\n"
        ".opencode/skills/spec-driven-development/SKILL.md\n"
        ".opencode/harness/rules/tech.md\n"
    )
    return src


class InstallerTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.target = self.tmp / "project"
        self.target.mkdir()
        self.source = make_source(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _run(self, *args: str, env: dict | None = None) -> tuple[int, str, str]:
        full_env = None
        if env is not None:
            full_env = {**os.environ, **env}
        result = subprocess.run(
            [sys.executable, str(INSTALLER), *args],
            cwd=self.target,
            capture_output=True,
            text=True,
            env=full_env,
        )
        return result.returncode, result.stdout, result.stderr

    def _manifest(self) -> dict:
        p = self.target / ".opencode/harness/harness.json"
        self.assertTrue(p.exists(), "manifest not written")
        return json.loads(p.read_text())


class TestFreshInstall(InstallerTestCase):
    def test_installs_files(self):
        rc, out, _ = self._run("install", "--from", str(self.source))
        self.assertEqual(rc, 0, out)
        self.assertTrue((self.target / ".opencode/agents/reviewer.md").exists())
        self.assertTrue((self.target / ".opencode/commands/ship.md").exists())
        self.assertTrue(
            (self.target / ".opencode/skills/spec-driven-development/SKILL.md").exists()
        )

    def test_writes_manifest(self):
        self._run("install", "--from", str(self.source))
        m = self._manifest()
        self.assertEqual(m["version"], "local")
        self.assertGreater(len(m["files"]), 0)
        for rel in m["files"]:
            self.assertTrue(
                (self.target / rel).exists(), f"manifest references missing file: {rel}"
            )

    def test_skips_local_tooling_files(self):
        rc, out, _ = self._run("install", "--from", str(self.source))
        self.assertEqual(rc, 0, out)
        for name in (".gitignore", "package.json", "package-lock.json", "bun.lock"):
            self.assertFalse(
                (self.target / ".opencode" / name).exists(),
                f"tooling file {name} leaked into install",
            )
        m = self._manifest()
        leaked = [
            p
            for p in m["files"]
            if Path(p).name
            in (".gitignore", "package.json", "package-lock.json", "bun.lock")
        ]
        self.assertEqual(leaked, [], f"tooling files leaked into manifest: {leaked}")

    def test_status_clean(self):
        self._run("install", "--from", str(self.source))
        rc, out, _ = self._run("status")
        self.assertEqual(rc, 0)
        self.assertIn("clean", out)


class TestConflictDetection(InstallerTestCase):
    def test_aborts_on_conflict(self):
        existing = self.target / ".opencode/agents/reviewer.md"
        existing.parent.mkdir(parents=True)
        existing.write_text("user content")

        rc, out, _ = self._run("install", "--from", str(self.source))
        self.assertEqual(rc, 1)
        self.assertIn("overwrite", out.lower())
        self.assertEqual(existing.read_text(), "user content")

    def test_no_partial_install_on_conflict(self):
        (self.target / ".opencode/agents/reviewer.md").parent.mkdir(parents=True)
        (self.target / ".opencode/agents/reviewer.md").write_text("user content")

        self._run("install", "--from", str(self.source))
        # Other files should NOT exist (pre-flight abort)
        self.assertFalse((self.target / ".opencode/commands/ship.md").exists())

    def test_skip_existing(self):
        existing = self.target / ".opencode/agents/reviewer.md"
        existing.parent.mkdir(parents=True)
        existing.write_text("user content")

        rc, out, _ = self._run("install", "--from", str(self.source), "--skip-existing")
        self.assertEqual(rc, 0)
        self.assertEqual(existing.read_text(), "user content")
        self.assertTrue((self.target / ".opencode/commands/ship.md").exists())

    def test_force_overwrites(self):
        existing = self.target / ".opencode/agents/reviewer.md"
        existing.parent.mkdir(parents=True)
        existing.write_text("user content")

        rc, out, _ = self._run("install", "--from", str(self.source), "--force")
        self.assertEqual(rc, 0)
        self.assertIn("body v1", existing.read_text())


class TestIdempotency(InstallerTestCase):
    """Re-running install is the refresh path: matching files are no-ops,
    divergent files are reported with an overwrite warning before any action."""

    def test_rerun_after_install_is_noop(self):
        self._run("install", "--from", str(self.source))
        reviewer = (self.target / ".opencode/agents/reviewer.md").read_text()
        rc, out, _ = self._run("install", "--from", str(self.source))
        self.assertEqual(rc, 0, out)
        # Content unchanged on the second run.
        self.assertEqual(
            (self.target / ".opencode/agents/reviewer.md").read_text(), reviewer
        )
        # Every shipped file matched → reported up-to-date, nothing overwritten.
        self.assertIn("Up-to-date", out)
        self.assertIn("Overwritten: 0", out)

    def test_matching_content_is_not_a_conflict(self):
        # Pre-place a file whose content matches the source byte-for-byte.
        f = self.target / ".opencode/agents/reviewer.md"
        f.parent.mkdir(parents=True)
        f.write_text((self.source / ".opencode/agents/reviewer.md").read_text())
        rc, out, _ = self._run("install", "--from", str(self.source))
        self.assertEqual(rc, 0, out)
        self.assertIn("Up-to-date", out)

    def test_warns_and_aborts_on_divergence(self):
        f = self.target / ".opencode/agents/reviewer.md"
        f.parent.mkdir(parents=True)
        f.write_text("user content")
        rc, out, _ = self._run("install", "--from", str(self.source))
        self.assertEqual(rc, 1)
        # Prominent overwrite warning naming the divergent file.
        self.assertIn("overwrite", out.lower())
        self.assertIn(".opencode/agents/reviewer.md", out)
        # Nothing written — divergent file preserved, absent files stay absent.
        self.assertEqual(f.read_text(), "user content")
        self.assertFalse((self.target / ".opencode/commands/ship.md").exists())

    def test_force_overwrites_divergent_on_rerun(self):
        self._run("install", "--from", str(self.source))
        f = self.target / ".opencode/agents/reviewer.md"
        f.write_text("user edit")
        rc, out, _ = self._run("install", "--from", str(self.source), "--force")
        self.assertEqual(rc, 0, out)
        self.assertIn("body v1", f.read_text())
        self.assertIn("Overwritten: 1", out)

    def test_skip_existing_keeps_divergent_on_rerun(self):
        self._run("install", "--from", str(self.source))
        f = self.target / ".opencode/agents/reviewer.md"
        f.write_text("user edit")
        rc, out, _ = self._run("install", "--from", str(self.source), "--skip-existing")
        self.assertEqual(rc, 0, out)
        self.assertEqual(f.read_text(), "user edit")
        self.assertIn("Kept 1 divergent", out)


class TestStatusDrift(InstallerTestCase):
    def setUp(self):
        super().setUp()
        self._run("install", "--from", str(self.source))

    def test_reports_modified(self):
        (self.target / ".opencode/agents/reviewer.md").write_text("changed")
        rc, out, _ = self._run("status")
        self.assertEqual(rc, 1)
        self.assertIn("modified", out)

    def test_reports_missing(self):
        (self.target / ".opencode/agents/reviewer.md").unlink()
        rc, out, _ = self._run("status")
        self.assertEqual(rc, 1)
        self.assertIn("missing", out)


class TestConfigBootstrap(InstallerTestCase):
    def test_writes_default_config_on_fresh_install(self):
        rc, out, _ = self._run("install", "--from", str(self.source))
        self.assertEqual(rc, 0, out)
        cfg = self.target / "opencode.jsonc"
        self.assertTrue(cfg.exists(), "opencode.jsonc not written")
        m = json.loads(cfg.read_text())
        self.assertIn(
            ".opencode/harness/rules/tech.md",
            m.get("instructions", []),
            "tech router not wired into instructions",
        )
        self.assertIn("Wrote default config", out)

    def test_does_not_overwrite_existing_config(self):
        existing = self.target / "opencode.jsonc"
        existing.write_text('{"instructions": ["my-own.md"]}\n')
        rc, out, _ = self._run("install", "--from", str(self.source))
        self.assertEqual(rc, 0, out)
        self.assertEqual(existing.read_text(), '{"instructions": ["my-own.md"]}\n')
        self.assertNotIn("Wrote default config", out)

    def test_respects_all_config_variants(self):
        for variant in ("opencode.json", ".opencode.jsonc"):
            with self.subTest(variant=variant):
                tgt = self.tmp / f"proj-{variant.replace('.', '')}"
                tgt.mkdir()
                (tgt / variant).write_text('{"instructions": ["mine.md"]}\n')
                result = subprocess.run(
                    [
                        sys.executable,
                        str(INSTALLER),
                        "install",
                        "--from",
                        str(self.source),
                    ],
                    cwd=tgt,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                # neither opencode.jsonc created nor the existing variant touched
                self.assertFalse((tgt / "opencode.jsonc").exists())
                self.assertEqual(
                    (tgt / variant).read_text(), '{"instructions": ["mine.md"]}\n'
                )

    def test_install_writes_config_if_missing(self):
        self._run("install", "--from", str(self.source))
        (self.target / "opencode.jsonc").unlink()
        rc, out, _ = self._run("install", "--from", str(self.source))
        self.assertEqual(rc, 0, out)
        self.assertTrue((self.target / "opencode.jsonc").exists())
        self.assertIn("Wrote default config", out)


class TestVersionLabel(unittest.TestCase):
    """A directory source that is a git repo stamps a meaningful version
    (via `git describe`) instead of the bare 'local' label."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.target = self.tmp / "project"
        self.target.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _git(self, *args: str, cwd: Path):
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
        )

    def test_git_repo_source_stamps_describe_version(self):
        source = make_source(self.tmp, "src")
        self._git("init", "-q", cwd=source)
        self._git("add", "-A", cwd=source)
        self._git("commit", "-qm", "init", cwd=source)
        self._git("tag", "v9.9.9", cwd=source)

        result = subprocess.run(
            [sys.executable, str(INSTALLER), "install", "--from", str(source)],
            cwd=self.target,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        m = json.loads((self.target / ".opencode/harness/harness.json").read_text())
        self.assertEqual(m["version"], "v9.9.9")

    def test_non_git_dir_source_falls_back_to_local(self):
        source = make_source(self.tmp, "src")  # not a git repo
        result = subprocess.run(
            [sys.executable, str(INSTALLER), "install", "--from", str(source)],
            cwd=self.target,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        m = json.loads((self.target / ".opencode/harness/harness.json").read_text())
        self.assertEqual(m["version"], "local")


class TestInstallerCLI(unittest.TestCase):
    """Top-level installer CLI flags (--version) and invocation-aware
    post-install hints (file-path vs piped-via-stdin)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.target = self.tmp / "project"
        self.target.mkdir()
        self.source = make_source(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_version_flag_prints_and_exits_zero(self):
        result = subprocess.run(
            [sys.executable, str(INSTALLER), "--version"],
            cwd=self.target,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("opencode-agent-harness installer", result.stdout)

    def test_version_flag_does_not_require_subcommand(self):
        # --version must exit cleanly without `install`/`status`, even though
        # subparsers are required.
        result = subprocess.run(
            [sys.executable, str(INSTALLER), "--version"],
            cwd=self.target,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("required", result.stderr.lower())

    def test_install_hint_for_file_path_invocation(self):
        result = subprocess.run(
            [sys.executable, str(INSTALLER), "install", "--from", str(self.source)],
            cwd=self.target,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        # File-path users get told to re-invoke by absolute path.
        self.assertIn("python3 ", result.stdout)
        self.assertIn(str(INSTALLER), result.stdout)
        self.assertIn("status", result.stdout)
        # Must NOT accidentally suggest the curl one-liner.
        self.assertNotIn("curl ", result.stdout)

    def test_install_hint_for_stdin_invocation(self):
        # Simulate `curl ... | python3 - install` by piping the installer
        # source via stdin with argv[0] == '-'.
        installer_src = INSTALLER.read_text()
        result = subprocess.run(
            [sys.executable, "-", "install", "--from", str(self.source)],
            cwd=self.target,
            input=installer_src,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        # stdin users get told to re-curl.
        self.assertIn("curl -fsSL", result.stdout)
        self.assertIn("python3 - status", result.stdout)


def make_source_with_deprecated(base: Path, name: str = "source") -> Path:
    """A source whose MANIFEST omits a file that DEPRECATED explains.

    Simulates a v0.2.0 → v0.4.0 upgrade: `.opencode/commands/migrate.md` was
    shipped once, removed in v0.3.0, and recorded in DEPRECATED so downstream
    installs that still have it get an explanation instead of silence.
    """
    src = make_source(base, name)
    (src / "DEPRECATED").write_text(
        ".opencode/commands/migrate.md\tv0.3.0\t"
        "Removed; install is now idempotent. Safe to delete.\n"
    )
    return src


class TestManifestGating(InstallerTestCase):
    """A file under .opencode/ in the source but NOT in MANIFEST must not ship.

    This is the structural leak prevention the manifest system exists for — the
    exact failure that let extract-release-notes.py escape in v0.3.x.
    """

    def test_stray_source_file_excluded(self):
        stray = self.source / ".opencode/harness/scripts/stray.py"
        stray.parent.mkdir(parents=True, exist_ok=True)
        stray.write_text("# maintainer-only; must not ship")
        rc, out, _ = self._run("install", "--from", str(self.source))
        self.assertEqual(rc, 0, out)
        self.assertFalse(
            (self.target / ".opencode/harness/scripts/stray.py").exists(),
            "stray source file leaked through MANIFEST gating",
        )
        # Source HAS a manifest, so the legacy-fallback notice must not appear.
        self.assertNotIn("no MANIFEST", out)


class TestLegacyFallback(InstallerTestCase):
    """A source without MANIFEST (predates v0.4.0) falls back to rglob discovery.

    Preserves backward compat: the v0.4.0 installer can install from an old tag
    (v0.3.x) that has no MANIFEST, with a notice that leak protection is off.
    """

    def test_no_manifest_uses_rglobs_with_notice(self):
        (self.source / "MANIFEST").unlink()
        rc, out, _ = self._run("install", "--from", str(self.source))
        self.assertEqual(rc, 0, out)
        # Files still installed via the fallback discoverer.
        self.assertTrue((self.target / ".opencode/agents/reviewer.md").exists())
        self.assertTrue((self.target / ".opencode/commands/ship.md").exists())
        # User is told why leak protection is inactive.
        self.assertIn("no MANIFEST", out)
        self.assertIn("rglob", out)


class TestOrphanDetection(InstallerTestCase):
    """Downstream files the current MANIFEST doesn't track are reported.

    Deprecated orphans (listed in source DEPRECATED) get a reason; unknown
    orphans get a generic message. By default nothing is deleted.
    """

    def setUp(self):
        super().setUp()
        # Swap in a source whose DEPRECATED explains migrate.md.
        shutil.rmtree(self.source)
        self.source = make_source_with_deprecated(self.tmp)

    def test_deprecated_orphan_reported_with_reason(self):
        orphan = self.target / ".opencode/commands/migrate.md"
        orphan.parent.mkdir(parents=True, exist_ok=True)
        orphan.write_text("stale leftover from v0.2.0")
        rc, out, _ = self._run("install", "--from", str(self.source))
        self.assertEqual(rc, 0, out)
        self.assertIn("Deprecated files found", out)
        self.assertIn("migrate.md", out)
        self.assertIn("v0.3.0", out)
        self.assertIn("idempotent", out)
        # Warn-only by default: the file is NOT deleted.
        self.assertTrue(
            orphan.exists(), "deprecated orphan deleted without --prune-deprecated"
        )
        self.assertIn("--prune-deprecated", out)

    def test_unknown_orphan_reported_generically(self):
        # A downstream file in neither MANIFEST nor DEPRECATED — could be the
        # user's own file. Reported but never touched.
        unknown = self.target / ".opencode/commands/my-custom.md"
        unknown.parent.mkdir(parents=True, exist_ok=True)
        unknown.write_text("user's own file")
        rc, out, _ = self._run("install", "--from", str(self.source))
        self.assertEqual(rc, 0, out)
        self.assertIn("Untracked files", out)
        self.assertIn("my-custom.md", out)
        self.assertTrue(unknown.exists())

    def test_prune_deprecated_deletes_only_deprecated(self):
        deprecated = self.target / ".opencode/commands/migrate.md"
        deprecated.parent.mkdir(parents=True, exist_ok=True)
        deprecated.write_text("stale")
        unknown = self.target / ".opencode/commands/custom.md"
        unknown.write_text("user file")
        rc, out, _ = self._run(
            "install", "--from", str(self.source), "--prune-deprecated"
        )
        self.assertEqual(rc, 0, out)
        # Deprecated orphan IS pruned.
        self.assertFalse(deprecated.exists(), "deprecated orphan not pruned")
        self.assertIn("pruned", out.lower())
        # Unknown orphan is NOT touched.
        self.assertTrue(
            unknown.exists(), "unknown orphan pruned (should be left alone)"
        )

    def test_status_detects_orphans_after_drop(self):
        # Install writes a downstream manifest tracking only the shipped set.
        self._run("install", "--from", str(self.source))
        # Drop a file that the manifest doesn't track (simulates a leftover).
        orphan = self.target / ".opencode/commands/migrate.md"
        orphan.write_text("stale")
        rc, out, _ = self._run("status")
        self.assertIn("Orphans:", out)
        self.assertIn("migrate.md", out)

    def test_status_no_orphans_when_clean(self):
        self._run("install", "--from", str(self.source))
        rc, out, _ = self._run("status")
        self.assertIn("No orphans", out)


class TestColorOutput(InstallerTestCase):
    """ANSI color highlights the orphan report so 'safe to remove' files stand
    out. Color is auto-disabled when stdout isn't a TTY (pipes, captures, logs)
    so the curl|python3 install path stays clean. NO_COLOR / CLICOLOR_FORCE env
    vars and --no-color / --color flags all participate."""

    RESET = "\033[0m"

    def _make_unknown_orphan(self) -> Path:
        unknown = self.target / ".opencode/commands/custom.md"
        unknown.parent.mkdir(parents=True, exist_ok=True)
        unknown.write_text("user file")
        return unknown

    def test_color_off_when_stdout_captured(self):
        # Default behavior with stdout captured (not a TTY) and no env override:
        # no ANSI escapes. This is what every other test in this suite sees.
        self._make_unknown_orphan()
        rc, out, _ = self._run(
            "install",
            "--from",
            str(self.source),
            env={"NO_COLOR": "", "CLICOLOR_FORCE": ""},
        )
        self.assertEqual(rc, 0, out)
        self.assertIn("safe to remove", out)
        self.assertNotIn("\033[", out)

    def test_color_on_with_clicolor_force(self):
        # CLICOLOR_FORCE!=0 flips color on even when stdout is captured.
        self._make_unknown_orphan()
        rc, out, _ = self._run(
            "install", "--from", str(self.source), env={"CLICOLOR_FORCE": "1"}
        )
        self.assertEqual(rc, 0, out)
        # The unknown-orphan header and the path line both get wrapped.
        self.assertIn("\033[33m", out)  # yellow
        self.assertIn(self.RESET, out)
        # The plain text is still present inside the escape sequences.
        self.assertIn("safe to remove", out)

    def test_no_color_env_disables_color(self):
        # NO_COLOR (non-empty) overrides CLICOLOR_FORCE per the spec.
        self._make_unknown_orphan()
        rc, out, _ = self._run(
            "install",
            "--from",
            str(self.source),
            env={"NO_COLOR": "1", "CLICOLOR_FORCE": "1"},
        )
        self.assertEqual(rc, 0, out)
        self.assertNotIn("\033[", out)

    def test_no_color_flag_overrides_clicolor_force(self):
        # The --no-color flag wins over CLICOLOR_FORCE.
        self._make_unknown_orphan()
        rc, out, _ = self._run(
            "install",
            "--from",
            str(self.source),
            "--no-color",
            env={"CLICOLOR_FORCE": "1"},
        )
        self.assertEqual(rc, 0, out)
        self.assertNotIn("\033[", out)

    def test_color_flag_forces_color_when_piped(self):
        # The --color flag flips color on regardless of TTY.
        self._make_unknown_orphan()
        rc, out, _ = self._run(
            "install",
            "--from",
            str(self.source),
            "--color",
            env={"NO_COLOR": "", "CLICOLOR_FORCE": ""},
        )
        self.assertEqual(rc, 0, out)
        self.assertIn("\033[33m", out)


if __name__ == "__main__":
    unittest.main()
