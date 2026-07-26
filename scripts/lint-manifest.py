#!/usr/bin/env python3
"""Validate MANIFEST and DEPRECATED against the actual .opencode/ tree.

Runs in the harness SOURCE repo (not downstream). Catches the two failure
modes the manifest system exists to prevent:
  1. A file under .opencode/ that is NOT in MANIFEST (would silently ship —
     the exact leak that let extract-release-notes.py escape in v0.3.x).
  2. A DEPRECATED entry for a file that still exists in source (stale), or a
     path that is both shipped and deprecated (contradiction).

Uses install.py's skip rules so "shippable" means precisely what the installer
would copy — no second definition to drift.

Exit 0 if all checks pass, 1 otherwise. Prints a one-line summary either way.

Usage:
    python3 scripts/lint-manifest.py [repo_root]
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
# Reuse the installer's skip rules + discoverer so this validator's notion of
# "shippable" can never drift from what install.py actually copies.
sys.path.insert(0, str(REPO_ROOT))
import install  # noqa: E402


def _read_plain_list(path: Path) -> set[str]:
    """Read a '#'-comment / blank-line aware plain-text path list."""
    if not path.is_file():
        return set()
    out: set[str] = set()
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.add(line)
    return out


def _read_deprecated(path: Path) -> dict[str, tuple[str, str, str]]:
    """Read DEPRECATED → {path: (removed_in, reason, replacement)}.

    replacement is '' when the 4th field is absent. Malformed lines are reported
    to stderr and skipped (the caller's set-membership checks still apply).
    """
    if not path.is_file():
        return {}
    out: dict[str, tuple[str, str, str]] = {}
    for ln, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            print(
                f"DEPRECATED:{ln}: malformed (need >=3 tab fields): {line!r}",
                file=sys.stderr,
            )
            continue
        rel = parts[0].strip()
        removed_in = parts[1].strip()
        reason = parts[2].strip()
        replacement = parts[3].strip() if len(parts) > 3 else ""
        out[rel] = (removed_in, reason, replacement)
    return out


def main() -> int:
    repo = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else REPO_ROOT
    errors: list[str] = []

    manifest_file = repo / install.MANIFEST_FILE
    deprecated_file = repo / install.DEPRECATED_FILE

    if not manifest_file.is_file():
        errors.append("MANIFEST file is missing at repo root.")
    if not deprecated_file.is_file():
        errors.append("DEPRECATED file is missing at repo root.")

    manifest = _read_plain_list(manifest_file)
    deprecated = _read_deprecated(deprecated_file)

    # The ground-truth shippable set, per install.py's own skip rules.
    on_disk = {str(p.relative_to(repo)) for p in install.list_harness_files(repo)}

    # 1. Declared in MANIFEST but not actually shippable on disk.
    for rel in sorted(manifest - on_disk):
        if not (repo / rel).is_file():
            errors.append(
                f"MANIFEST declares '{rel}' but no such file exists under .opencode/."
            )
        else:
            errors.append(
                f"MANIFEST declares '{rel}' but it is excluded by the install "
                "skip rules (skipped dir / scaffolding root file) — pick one."
            )

    # 2. Shippable on disk but not declared — the leak this validator prevents.
    for rel in sorted(on_disk - manifest):
        errors.append(
            f"Shippable file '{rel}' exists under .opencode/ but is NOT in "
            "MANIFEST — it would silently ship. Add it to MANIFEST (or remove "
            "the file)."
        )

    # 3. Present in both MANIFEST and DEPRECATED.
    for rel in sorted(manifest & deprecated.keys()):
        errors.append(
            f"'{rel}' appears in BOTH MANIFEST and DEPRECATED — a file is "
            "either shipped or deprecated, not both."
        )

    # 4. Deprecated but still present in the source tree (stale entry).
    for rel in sorted(deprecated):
        if (repo / rel).is_file():
            errors.append(
                f"DEPRECATED entry '{rel}' still exists in the source tree — "
                "remove the file (or remove the DEPRECATED entry)."
            )

    if errors:
        print(f"lint-manifest: {len(errors)} error(s):")
        for e in errors:
            print(f"  ✗ {e}")
        return 1

    print(
        f"lint-manifest: OK  "
        f"(MANIFEST={len(manifest)} shippable={len(on_disk)} deprecated={len(deprecated)})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
