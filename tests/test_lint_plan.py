"""Tests for .opencode/harness/scripts/lint-plan.py — the plan.md thinness validator.

The validator enforces the "thin index" rule from planning-and-task-breakdown:
per-task detail (acceptance criteria, file lists, verification) belongs in
tasks/00N-<slug>.md, not inlined into plan.md. These tests pin its three
detection rules and guard against the obvious false positives (checkpoint
bullets, architecture decisions referencing file paths, template placeholders).

Run:  python3 -m unittest tests.test_lint_plan
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / ".opencode"
    / "harness"
    / "scripts"
    / "lint-plan.py"
)


def _write_plan(repo: Path, slug: str, content: str) -> Path:
    """Write docs/specs/<slug>/plan.md under repo and return its path."""
    p = repo / "docs" / "specs" / slug / "plan.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return p


# Canonical thin plan (mirrors the template in planning-and-task-breakdown/SKILL.md).
THIN_PLAN = """\
# Plan: Example Effort

## Overview
One paragraph of what we're building.

## Architecture Decisions
- Use Postgres for durable state.
- API follows the JSON:API spec.

## Task Index

### Phase 1: Foundation
- [ ] Task 1: Set up DB → `tasks/001-db-setup.md`
- [ ] Task 2: Migrations → `tasks/002-migrations.md`

### Checkpoint: Foundation
- [ ] Tests pass, builds clean

### Phase 2: Core Features
- [ ] Task 3: User registration → `tasks/003-registration.md`

### Checkpoint: Core Features
- [ ] End-to-end flow works

## Risks and Mitigations
| Risk | Impact | Mitigation |
| :--- | :--- | :--- |
| Schema churn | Med | Versioned migrations |

## Open Questions
- Which auth provider?
"""


class TestLintPlan(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = self.tmp / "repo"
        self.repo.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _run(self) -> tuple[int, str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(self.repo)],
            capture_output=True,
            text=True,
        )
        return result.returncode, result.stdout + result.stderr

    # ── no-op when spec flow isn't in use ────────────────────────────────────

    def test_no_specs_dir_passes(self):
        rc, out = self._run()
        self.assertEqual(rc, 0, out)
        self.assertIn("not in use", out)

    def test_empty_specs_dir_passes(self):
        (self.repo / "docs" / "specs").mkdir(parents=True)
        rc, out = self._run()
        self.assertEqual(rc, 0, out)

    # ── clean plans pass ────────────────────────────────────────────────────

    def test_thin_plan_passes(self):
        _write_plan(self.repo, "effort-a", THIN_PLAN)
        rc, out = self._run()
        self.assertEqual(rc, 0, out)
        self.assertIn("thin", out)

    def test_template_placeholders_pass(self):
        # The skill's template uses `<slug>` placeholders; the pointer regex
        # must not choke on the angle brackets.
        plan = THIN_PLAN.replace(
            "- [ ] Task 1: Set up DB → `tasks/001-db-setup.md`",
            "- [ ] Task 1: Set up DB → `tasks/001-<slug>.md`",
        )
        _write_plan(self.repo, "tmpl", plan)
        rc, out = self._run()
        self.assertEqual(rc, 0, out)

    def test_pointer_without_backticks_passes(self):
        plan = THIN_PLAN.replace(
            "- [ ] Task 1: Set up DB → `tasks/001-db-setup.md`",
            "- [ ] Task 1: Set up DB → tasks/001-db-setup.md",
        )
        _write_plan(self.repo, "noback", plan)
        rc, out = self._run()
        self.assertEqual(rc, 0, out)

    # ── false-positive guards ───────────────────────────────────────────────

    def test_checkpoint_bullets_not_flagged(self):
        # Checkpoints legitimately have `- [ ]` bullets at column 0 — they are
        # NOT per-task detail and must not trip the indented-content rule.
        _write_plan(self.repo, "ckpt", THIN_PLAN)
        rc, out = self._run()
        self.assertEqual(rc, 0, out)
        self.assertNotIn("inlined", out)

    def test_architecture_decision_referencing_paths_not_flagged(self):
        # Decisions may legitimately mention source paths; the validator must
        # not treat these as per-task file lists.
        plan = THIN_PLAN.replace(
            "- Use Postgres for durable state.",
            "- Persist models under `src/db/` via the Postgres driver.",
        )
        _write_plan(self.repo, "paths", plan)
        rc, out = self._run()
        self.assertEqual(rc, 0, out)

    def test_risks_table_not_flagged(self):
        _write_plan(self.repo, "risks", THIN_PLAN)
        rc, out = self._run()
        self.assertEqual(rc, 0, out)

    # ── rule 1: per-task detail headers ─────────────────────────────────────

    def test_acceptance_criteria_header_flagged(self):
        plan = THIN_PLAN.replace(
            "## Architecture Decisions\n",
            "## Architecture Decisions\n\n"
            "**Acceptance criteria:**\n"
            "- [ ] DB accepts connections\n",
        )
        _write_plan(self.repo, "hdr", plan)
        rc, out = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("**Acceptance criteria:**", out)
        self.assertIn("tasks/00N", out)

    def test_all_seven_task_detail_headers_flagged(self):
        headers = [
            "**Description:**",
            "**Acceptance criteria:**",
            "**Verification:**",
            "**Dependencies:**",
            "**Files likely touched:**",
            "**Docs:**",
            "**Estimated scope:**",
        ]
        for n, header in enumerate(headers):
            with self.subTest(header=header):
                repo = self.tmp / f"repo-{n}"
                repo.mkdir(exist_ok=True)
                plan = THIN_PLAN.replace(
                    "## Architecture Decisions\n",
                    f"## Architecture Decisions\n\n{header} stuff\n",
                )
                _write_plan(repo, "eff", plan)
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), str(repo)],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn(header, result.stdout + result.stderr)

    # ── rule 2: task line missing pointer ───────────────────────────────────

    def test_task_line_missing_pointer_flagged(self):
        plan = THIN_PLAN.replace(
            "- [ ] Task 1: Set up DB → `tasks/001-db-setup.md`",
            "- [ ] Task 1: Set up DB and migrations and seed data",
        )
        _write_plan(self.repo, "noptr", plan)
        rc, out = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("missing pointer", out)
        self.assertIn("tasks/00N", out)

    def test_checked_task_line_missing_pointer_flagged(self):
        # `[x]` (completed) form must also carry the pointer.
        plan = THIN_PLAN.replace(
            "- [ ] Task 1: Set up DB → `tasks/001-db-setup.md`",
            "- [x] Task 1: Set up DB and seed data",
        )
        _write_plan(self.repo, "chk", plan)
        rc, out = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("missing pointer", out)

    # ── rule 3: indented sub-content under a task line ──────────────────────

    def test_indented_subcontent_flagged(self):
        plan = THIN_PLAN.replace(
            "- [ ] Task 1: Set up DB → `tasks/001-db-setup.md`\n",
            "- [ ] Task 1: Set up DB → `tasks/001-db-setup.md`\n"
            "  - [ ] Migration creates users table\n"
            "  - [ ] Seed data loads\n",
        )
        _write_plan(self.repo, "indent", plan)
        rc, out = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("inlined", out)

    def test_indented_subcontent_reports_task_line(self):
        # The error should point at the task line so the user knows which task
        # the orphaned detail belongs to.
        plan = THIN_PLAN.replace(
            "- [ ] Task 1: Set up DB → `tasks/001-db-setup.md`\n",
            "- [ ] Task 1: Set up DB → `tasks/001-db-setup.md`\n"
            "  - [ ] Migration creates users table\n",
        )
        _write_plan(self.repo, "indent2", plan)
        rc, out = self._run()
        self.assertEqual(rc, 1)
        # Line number of the task line (count: # Plan=1, blank=2, ## Overview=3...)
        self.assertIn("under task line", out)

    # ── multiple plans ──────────────────────────────────────────────────────

    def test_multiple_plans_one_bad_flagged_once(self):
        _write_plan(self.repo, "clean", THIN_PLAN)
        bad = THIN_PLAN.replace(
            "- [ ] Task 1: Set up DB → `tasks/001-db-setup.md`",
            "- [ ] Task 1: Set up DB and seeds",  # no pointer
        )
        _write_plan(self.repo, "bad", bad)
        rc, out = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("bad/plan.md", out)
        self.assertNotIn("clean/plan.md", out)

    def test_reports_count_of_plans_scanned(self):
        _write_plan(self.repo, "a", THIN_PLAN)
        _write_plan(self.repo, "b", THIN_PLAN)
        rc, out = self._run()
        self.assertEqual(rc, 0, out)
        self.assertIn("2 plan.md", out)


if __name__ == "__main__":
    unittest.main()
