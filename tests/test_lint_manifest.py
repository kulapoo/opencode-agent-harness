"""Tests for scripts/lint-manifest.py — the manifest/deprecated validator.

Run:  python3 -m unittest tests.test_lint_manifest
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "lint-manifest.py"


def _make_repo(
    base: Path,
    manifest: str,
    deprecated: str = "",
    files: dict[str, str] | None = None,
) -> Path:
    """Build a minimal repo with a .opencode/ tree, MANIFEST, and DEPRECATED.

    `files` maps repo-relative paths to file contents (the .opencode/ shippable
    set). Defaults to two files so tests can vary MANIFEST against a known tree.
    """
    repo = base / "repo"
    files = files or {
        ".opencode/agents/a.md": "a",
        ".opencode/commands/c.md": "c",
    }
    for rel, content in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    (repo / "MANIFEST").write_text(manifest)
    (repo / "DEPRECATED").write_text(deprecated)
    return repo


class TestLintManifest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _run(self, repo: Path) -> tuple[int, str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(repo)],
            capture_output=True,
            text=True,
        )
        return result.returncode, result.stdout + result.stderr

    def test_consistent_repo_passes(self):
        repo = _make_repo(
            self.tmp,
            manifest=".opencode/agents/a.md\n.opencode/commands/c.md\n",
        )
        rc, out = self._run(repo)
        self.assertEqual(rc, 0, out)
        self.assertIn("OK", out)

    def test_unlisted_shippable_file_is_flagged_as_leak(self):
        # c.md exists on disk but MANIFEST doesn't list it → would silently ship.
        repo = _make_repo(
            self.tmp,
            manifest=".opencode/agents/a.md\n",  # omits c.md
        )
        rc, out = self._run(repo)
        self.assertEqual(rc, 1)
        self.assertIn("c.md", out)
        self.assertIn("NOT in MANIFEST", out)

    def test_manifest_declares_missing_file_is_flagged(self):
        # MANIFEST lists a file that doesn't exist under .opencode/.
        repo = _make_repo(
            self.tmp,
            manifest=(
                ".opencode/agents/a.md\n"
                ".opencode/commands/c.md\n"
                ".opencode/ghosts/missing.md\n"
            ),
        )
        rc, out = self._run(repo)
        self.assertEqual(rc, 1)
        self.assertIn("missing.md", out)
        self.assertIn("no such file", out.lower())

    def test_path_in_both_manifest_and_deprecated_is_flagged(self):
        repo = _make_repo(
            self.tmp,
            manifest=".opencode/agents/a.md\n.opencode/commands/c.md\n",
            deprecated=(".opencode/commands/c.md\tv1.0\tremoved.\n"),
        )
        rc, out = self._run(repo)
        self.assertEqual(rc, 1)
        self.assertIn("BOTH", out)

    def test_deprecated_entry_still_on_disk_is_flagged(self):
        # DEPRECATED claims c.md was removed, but c.md still ships — contradiction.
        # Make MANIFEST omit c.md (so it's not 'in both'), but the file exists.
        repo = _make_repo(
            self.tmp,
            manifest=".opencode/agents/a.md\n",  # c.md not shipped
            deprecated=".opencode/commands/c.md\tv1.0\tremoved.\n",
            # c.md still exists in the tree though (files default includes it)
        )
        rc, out = self._run(repo)
        self.assertEqual(rc, 1)
        self.assertIn("still exists", out)

    def test_missing_manifest_file_is_flagged(self):
        repo = _make_repo(
            self.tmp,
            manifest=".opencode/agents/a.md\n.opencode/commands/c.md\n",
        )
        (repo / "MANIFEST").unlink()
        rc, out = self._run(repo)
        self.assertEqual(rc, 1)
        self.assertIn("MANIFEST file is missing", out)

    def test_missing_deprecated_file_is_flagged(self):
        repo = _make_repo(
            self.tmp,
            manifest=".opencode/agents/a.md\n.opencode/commands/c.md\n",
        )
        (repo / "DEPRECATED").unlink()
        rc, out = self._run(repo)
        self.assertEqual(rc, 1)
        self.assertIn("DEPRECATED file is missing", out)


if __name__ == "__main__":
    unittest.main()
