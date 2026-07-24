"""Installer test suite — validates install, update, and conflict behavior.

Run:  python3 -m pytest tests/test_installer.py
  or:  python3 -m unittest tests.test_installer
"""

from __future__ import annotations

import json
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
    return src


class InstallerTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.target = self.tmp / "project"
        self.target.mkdir()
        self.source = make_source(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _run(self, *args: str) -> tuple[int, str, str]:
        result = subprocess.run(
            [sys.executable, str(INSTALLER), *args],
            cwd=self.target,
            capture_output=True,
            text=True,
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
        self.assertIn("conflicting", out.lower())
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


class TestUpdate(InstallerTestCase):
    def setUp(self):
        super().setUp()
        self._run("install", "--from", str(self.source))

    def test_upgrades_untouched(self):
        rc, out, _ = self._run("update", "--from", str(self.source))
        self.assertEqual(rc, 0)
        self.assertIn("Upgraded", out)

    def test_preserves_modified(self):
        f = self.target / ".opencode/agents/reviewer.md"
        f.write_text("user modification")
        rc, out, _ = self._run("update", "--from", str(self.source))
        self.assertEqual(rc, 0)
        self.assertEqual(f.read_text(), "user modification")
        self.assertIn("preserved", out.lower())

    def test_adds_new_upstream_files(self):
        # Add a file to the source
        (self.source / ".opencode/agents/new-agent.md").write_text(
            "---\ndescription: new\n---\nnew body"
        )
        rc, out, _ = self._run("update", "--from", str(self.source))
        self.assertEqual(rc, 0)
        self.assertTrue((self.target / ".opencode/agents/new-agent.md").exists())
        self.assertIn("Added", out)

    def test_removes_deleted_upstream_files(self):
        # Remove a file from source
        (self.source / ".opencode/commands/ship.md").unlink()
        rc, out, _ = self._run("update", "--from", str(self.source))
        self.assertEqual(rc, 0)
        self.assertFalse((self.target / ".opencode/commands/ship.md").exists())
        self.assertIn("Removed", out)

    def test_preserves_modified_on_delete(self):
        f = self.target / ".opencode/commands/ship.md"
        f.write_text("user keeps this")
        (self.source / ".opencode/commands/ship.md").unlink()
        rc, out, _ = self._run("update", "--from", str(self.source))
        self.assertEqual(rc, 0)
        self.assertTrue(f.exists())
        self.assertEqual(f.read_text(), "user keeps this")


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

    def test_update_writes_config_if_missing(self):
        self._run("install", "--from", str(self.source))
        (self.target / "opencode.jsonc").unlink()
        rc, out, _ = self._run("update", "--from", str(self.source))
        self.assertEqual(rc, 0, out)
        self.assertTrue((self.target / "opencode.jsonc").exists())
        self.assertIn("Wrote default config", out)


if __name__ == "__main__":
    unittest.main()
