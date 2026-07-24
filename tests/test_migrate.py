"""Migration test suite — validates `install.py migrate` for the legacy
`.opencode/{rules,tech}` → `.opencode/harness/{rules,tech}` relocation.

Run:  python3 -m unittest tests.test_migrate
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

ROUTER_TECH_MD = """## Tech

Conventions are loaded lazily — this file is the router, not the content.
BEFORE writing or modifying code in a stack below, Read the matching files:

- `python` → `.opencode/harness/tech/python/*.md` + `.opencode/harness/tech/common/*.md`
- `react` → `.opencode/harness/tech/react/*.md` + `.opencode/harness/tech/common/*.md`

Polyglot: when a task spans multiple stacks, load each stack's conventions.
Other folders under `.opencode/harness/tech/` stay dormant — add them above.
"""


def make_source(base: Path, name: str = "source") -> Path:
    """A new-layout harness source: .opencode/{agents,commands,skills,harness/...}."""
    src = base / name
    oc = src / ".opencode"

    (oc / "agents").mkdir(parents=True)
    (oc / "agents" / "reviewer.md").write_text("---\ndescription: test\n---\nbody v2")

    (oc / "commands").mkdir(parents=True)
    (oc / "commands" / "ship.md").write_text("---\ndescription: test\n---\nship")
    (oc / "commands" / "adopt.md").write_text("---\ndescription: adopt\n---\nadopt")

    (oc / "skills" / "spec-driven-development").mkdir(parents=True)
    (oc / "skills" / "spec-driven-development" / "SKILL.md").write_text(
        "---\nname: spec-driven-development\ndescription: test\n---\nv2"
    )

    # New-layout harness tree.
    (oc / "harness" / "rules").mkdir(parents=True)
    (oc / "harness" / "rules" / "tech.md").write_text(ROUTER_TECH_MD)
    (oc / "harness" / "scripts").mkdir(parents=True)
    (oc / "harness" / "scripts" / "check-refs.py").write_text("# noop\n")

    # Tech dirs. NOTE: rust + typescript exist; react deliberately absent so we
    # can exercise the "unmapped stack" warning path.
    for stack in ("rust", "typescript", "common"):
        d = oc / "harness" / "tech" / stack
        d.mkdir(parents=True)
        (d / "coding-style.md").write_text(f"# {stack} style\n")

    # Local-only scaffolding that must never ship to targets.
    (oc / ".gitignore").write_text("node_modules\n")
    (oc / "package.json").write_text('{"dependencies": {}}\n')
    return src


def make_old_target(base: Path, name: str = "project") -> Path:
    """A target stuck on the legacy layout (rules/tech at .opencode/ root)."""
    tgt = base / name
    oc = tgt / ".opencode"

    # Legacy location of rules + tech.
    (oc / "rules").mkdir(parents=True)
    (oc / "rules" / "tech.md").write_text(
        "## Tech\n\nActive stacks:\n\n- rust\n- typescript\n- react\n"
    )
    (oc / "tech").mkdir(parents=True)
    (oc / "tech" / "rust").mkdir()
    (oc / "tech" / "rust" / "coding-style.md").write_text("# old rust\n")

    # Older content that should be updated to the source version.
    (oc / "agents").mkdir(parents=True)
    (oc / "agents" / "reviewer.md").write_text("---\ndescription: test\n---\nOLD v0")

    # Local-only command that must survive the migration (no --delete semantics).
    (oc / "commands").mkdir(parents=True)
    (oc / "commands" / "status.md").write_text("---\ndescription: mine\n---\nmine")

    # Local scaffolding at .opencode/ root — preserve.
    (oc / "package.json").write_text('{"dependencies": {"local": true}}\n')

    # Project-root files.
    (tgt / "AGENTS.md").write_text("# My Project — custom map\n")
    (tgt / "opencode.jsonc").write_text(
        json.dumps(
            {
                "$schema": "https://opencode.ai/config.json",
                "instructions": [".opencode/rules/tech.md"],
                "mcp": {"example": {"type": "local", "command": ["npx", "x"]}},
            },
            indent=2,
        )
        + "\n"
    )
    return tgt


class MigrateTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.source = make_source(self.tmp)
        self.target = make_old_target(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _run(self, *args: str, **kw) -> tuple[int, str, str]:
        result = subprocess.run(
            [
                sys.executable,
                str(INSTALLER),
                "migrate",
                "--from",
                str(self.source),
                *args,
            ],
            cwd=self.target,
            capture_output=True,
            text=True,
            **kw,
        )
        return result.returncode, result.stdout, result.stderr

    def _manifest(self) -> dict | None:
        p = self.target / ".opencode/harness/harness.json"
        if not p.exists():
            return None
        return json.loads(p.read_text())


class TestDryRun(MigrateTestCase):
    def test_dry_run_prints_plan_and_changes_nothing(self):
        before_rules = (self.target / ".opencode/rules/tech.md").read_text()
        rc, out, _ = self._run("--dry-run")
        self.assertEqual(rc, 0, out)
        # Plan mentions the key actions.
        self.assertIn("MOVE", out)
        self.assertIn(".opencode/rules", out)
        self.assertIn("DELETE", out)
        # Nothing mutated.
        self.assertEqual(
            (self.target / ".opencode/rules/tech.md").read_text(), before_rules
        )
        self.assertFalse((self.target / ".opencode/harness").exists())
        # Config untouched.
        cfg = json.loads((self.target / "opencode.jsonc").read_text())
        self.assertIn(".opencode/rules/tech.md", cfg["instructions"])


class TestApply(MigrateTestCase):
    def test_relocates_rules_and_tech_under_harness(self):
        rc, out, _ = self._run("--force")
        self.assertEqual(rc, 0, out)
        self.assertTrue((self.target / ".opencode/harness/rules/tech.md").exists())
        self.assertTrue((self.target / ".opencode/harness/tech/rust").is_dir())

    def test_deletes_legacy_orphan_dirs(self):
        self._run("--force")
        self.assertFalse((self.target / ".opencode/rules").exists())
        self.assertFalse((self.target / ".opencode/tech").exists())

    def test_fixes_config_instructions_path(self):
        self._run("--force")
        cfg = json.loads((self.target / "opencode.jsonc").read_text())
        self.assertEqual(cfg["instructions"], [".opencode/harness/rules/tech.md"])
        # MCP block preserved verbatim (key + content).
        self.assertIn("mcp", cfg)
        self.assertIn("example", cfg["mcp"])

    def test_ports_tech_md_stacks_deterministically(self):
        self._run("--force")
        tech = (self.target / ".opencode/harness/rules/tech.md").read_text()
        # rust + typescript had source tech dirs → router bullets emitted.
        self.assertIn("`rust` → `.opencode/harness/tech/rust/*.md`", tech)
        self.assertIn("`typescript` → `.opencode/harness/tech/typescript/*.md`", tech)
        # react had no source tech dir → not emitted (unmapped, warned).
        self.assertNotIn("`react`", tech)

    def test_warns_about_unmapped_stacks(self):
        rc, out, _ = self._run("--force")
        self.assertEqual(rc, 0, out)
        self.assertIn("react", out)  # surfaced as unmapped

    def test_updates_content_files_to_source(self):
        self._run("--force")
        reviewer = (self.target / ".opencode/agents/reviewer.md").read_text()
        self.assertIn("body v2", reviewer)

    def test_adds_new_upstream_files(self):
        self._run("--force")
        self.assertTrue((self.target / ".opencode/commands/adopt.md").exists())

    def test_preserves_local_command(self):
        rc, out, _ = self._run("--force")
        self.assertEqual(rc, 0, out)
        status = (self.target / ".opencode/commands/status.md").read_text()
        self.assertIn("mine", status)

    def test_preserves_custom_agents_md(self):
        self._run("--force")
        self.assertEqual(
            (self.target / "AGENTS.md").read_text(), "# My Project — custom map\n"
        )

    def test_preserves_local_scaffolding(self):
        self._run("--force")
        pkg = (self.target / ".opencode/package.json").read_text()
        self.assertIn('"local"', pkg)

    def test_records_migration_id_in_manifest(self):
        self._run("--force")
        m = self._manifest()
        self.assertIsNotNone(m, "manifest not written")
        self.assertIn("001-harness-relocate", m.get("migrations", []))
        self.assertGreater(len(m.get("files", {})), 0)


class TestIdempotent(MigrateTestCase):
    def test_second_run_is_noop(self):
        self._run("--force")
        tech_before = (self.target / ".opencode/harness/rules/tech.md").read_text()
        rc, out, _ = self._run("--force")
        self.assertEqual(rc, 0, out)
        self.assertIn("nothing to migrate", out.lower())
        tech_after = (self.target / ".opencode/harness/rules/tech.md").read_text()
        self.assertEqual(tech_before, tech_after)


class TestNoOpWhenCurrent(MigrateTestCase):
    def setUp(self):
        super().setUp()
        # Remove legacy markers → target looks already-migrated.
        shutil.rmtree(self.target / ".opencode/rules")
        shutil.rmtree(self.target / ".opencode/tech")

    def test_reports_nothing_to_migrate(self):
        rc, out, _ = self._run("--force")
        self.assertEqual(rc, 0, out)
        self.assertIn("nothing to migrate", out.lower())


class TestCheck(MigrateTestCase):
    def test_check_fails_on_legacy_layout(self):
        rc, out, _ = self._run("--check")
        self.assertEqual(rc, 1, out)

    def test_check_passes_after_migrate(self):
        self._run("--force")
        rc, out, _ = self._run("--check")
        self.assertEqual(rc, 0, out)


if __name__ == "__main__":
    unittest.main()
