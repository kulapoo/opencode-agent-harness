#!/usr/bin/env python3
"""opencode-agent-harness installer.

Installs the harness under .opencode/ in the current project. Initial setup
only — idempotent, so re-running is always safe: files that already match the
harness are left untouched, and any local files that differ are reported with
an overwrite warning before anything happens. There is no update or migrate
step; to refresh a project, re-run `install` (overwriting is always your
explicit decision via --force).

Usage:
    python3 install.py install [--tag TAG] [--from PATH] [--force] [--skip-existing]
    python3 install.py status
    python3 install.py --version

Flags:
    --tag TAG          Install a specific git tag (default: latest release or main)
    --from PATH        Use a local directory or tarball instead of GitHub
    --force            Overwrite divergent local files during install
    --skip-existing    Keep divergent local files during install
    --version          Print installer version and exit
    -h, --help         Show this message
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

REPO = "kulapoo/opencode-agent-harness"
# Pinned-tag URL for the installer itself. raw.githubusercontent.com resolves
# from tags whether or not a GitHub Release object exists. Bump this when cutting
# a new release so the documented one-liner and post-install hint stay in sync.
INSTALLER_URL = (
    "https://raw.githubusercontent.com/kulapoo/opencode-agent-harness/v0.4.0/install.py"
)
MANIFEST_REL = ".opencode/harness/harness.json"
# Source-side declarations (at the repo root of the harness itself). The install
# set is gated by MANIFEST — a file under .opencode/ ships only if listed there.
# When MANIFEST is absent (source predates v0.4.0), install falls back to
# discovering via rglob + the skip rules below. DEPRECATED drives the
# explanation printed when a downstream file is no longer in MANIFEST.
MANIFEST_FILE = "MANIFEST"
DEPRECATED_FILE = "DEPRECATED"
OPENCODE_PREFIX = ".opencode/"
SKIPPED_DIRS = {".git", "__pycache__", ".ruff_cache", "node_modules"}
# Local-only scaffolding at the .opencode/ root (opencode plugin/tooling) that
# must never ship to downstream projects.
SKIPPED_ROOT_FILES = {".gitignore", "package.json", "package-lock.json", "bun.lock"}
# opencode reads any of these at project root (first found wins).
CONFIG_FILES = ["opencode.jsonc", "opencode.json", ".opencode.jsonc"]
MIN_CONFIG = (
    "{\n"
    '  "$schema": "https://opencode.ai/config.json",\n'
    '  "instructions": [".opencode/harness/rules/tech.md"]\n'
    "}\n"
)


# ── helpers ──────────────────────────────────────────────────────────────────


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_path() -> Path:
    return Path(MANIFEST_REL)


def read_manifest() -> dict | None:
    p = manifest_path()
    if not p.exists():
        return None
    with open(p) as f:
        return json.load(f)


def write_manifest(
    version: str, files: dict[str, str], migrations: list[str] | None = None
) -> None:
    p = manifest_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": version, "files": files}
    if migrations is not None:
        payload["migrations"] = migrations
    with open(p, "w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")


def ensure_config() -> bool:
    """Write a minimal opencode.jsonc at the target root if no config exists.

    The tech router (.opencode/harness/rules/tech.md) must be injected into
    every session, which requires an `instructions` entry. Without this, a user
    who installs but skips /adopt gets no tech conventions. Safe to re-run:
    never overwrites an existing config in any supported filename variant.
    Returns True if a config was written.
    """
    for name in CONFIG_FILES:
        if (Path.cwd() / name).exists():
            return False
    (Path.cwd() / CONFIG_FILES[0]).write_text(MIN_CONFIG)
    return True


def list_harness_files(source_root: Path) -> list[Path]:
    """Return all files under .opencode/ in source_root, excluding harness.json.

    This is the ground-truth on-disk discoverer (rglob + skip rules). The
    primary install path reads MANIFEST instead (see resolve_install_files);
    this function backs the legacy fallback, the downstream manifest snapshot,
    and lint-manifest's notion of 'shippable'.
    """
    oc = source_root / OPENCODE_PREFIX
    if not oc.is_dir():
        return []
    result = []
    for p in sorted(oc.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(source_root)
        if str(rel) == MANIFEST_REL:
            continue
        if any(part in SKIPPED_DIRS for part in p.parts):
            continue
        if p.parent == oc and p.name in SKIPPED_ROOT_FILES:
            continue
        result.append(p)
    return result


def read_source_manifest(source_root: Path) -> list[str] | None:
    """Read the source MANIFEST; return declared paths, or None if absent.

    Returns None (not []) when MANIFEST is missing, so callers can distinguish
    'source predates the manifest' (-> rglob fallback) from 'declares nothing'.
    Comments ('#') and blank lines are ignored.
    """
    p = source_root / MANIFEST_FILE
    if not p.is_file():
        return None
    paths = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        paths.append(line)
    return paths


def read_source_deprecated(source_root: Path) -> dict[str, tuple[str, str, str]]:
    """Read source DEPRECATED -> {path: (removed_in, reason, replacement)}.

    replacement is '' when the 4th field is absent. Malformed lines are skipped.
    """
    p = source_root / DEPRECATED_FILE
    if not p.is_file():
        return {}
    out: dict[str, tuple[str, str, str]] = {}
    for line in p.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        out[parts[0].strip()] = (
            parts[1].strip(),
            parts[2].strip(),
            parts[3].strip() if len(parts) > 3 else "",
        )
    return out


def resolve_install_files(source_root: Path) -> tuple[list[Path], bool]:
    """Decide which source files to install. Returns (files, manifest_gated).

    Primary: read MANIFEST (the declared, validated install set) — this is what
    prevents stray files under .opencode/ from leaking downstream.
    Fallback: when MANIFEST is absent (source predates it), discover via rglob +
    skip rules, preserving backward compat with old release tags.
    """
    declared = read_source_manifest(source_root)
    if declared is not None:
        return [source_root / rel for rel in declared], True
    return list_harness_files(source_root), False


def discover_downstream_orphans(tracked: set[str]) -> list[str]:
    """Downstream .opencode/ files not in `tracked`. Sorted.

    Uses the same skip rules as list_harness_files so scaffolding, node_modules,
    and the manifest file itself never count as orphans. Used by:
      - install: `tracked` = current source MANIFEST (authoritative).
      - status:  `tracked` = downstream harness.json keys (self-contained).
    """
    oc = Path.cwd() / OPENCODE_PREFIX
    if not oc.is_dir():
        return []
    orphans: list[str] = []
    for p in sorted(oc.rglob("*")):
        if not p.is_file():
            continue
        rel = str(p.relative_to(Path.cwd()))
        if rel == MANIFEST_REL:
            continue
        if rel in tracked:
            continue
        if any(part in SKIPPED_DIRS for part in p.parts):
            continue
        if p.parent == oc and p.name in SKIPPED_ROOT_FILES:
            continue
        orphans.append(rel)
    return orphans


def report_orphans(
    orphans: list[str],
    deprecated_map: dict[str, tuple[str, str, str]],
    *,
    prune: bool,
) -> None:
    """Print a categorized orphan report; optionally delete deprecated ones.

    Splits orphans into 'deprecated' (DEPRECATED explains them, with reason) and
    'unknown' (not in MANIFEST or DEPRECATED). With prune=True, deletes ONLY the
    deprecated set — unknown orphans are always left untouched (they may be the
    user's own files under .opencode/). The flag is the confirmation, mirroring
    --force semantics.
    """
    deprecated_orphans = [o for o in orphans if o in deprecated_map]
    unknown_orphans = [o for o in orphans if o not in deprecated_map]
    if not deprecated_orphans and not unknown_orphans:
        return
    print()
    if deprecated_orphans:
        print(
            f"Deprecated files found ({len(deprecated_orphans)}) — no longer "
            "shipped by the harness:"
        )
        for rel in deprecated_orphans:
            removed_in, reason, replacement = deprecated_map[rel]
            extra = f"; replacement: {replacement}" if replacement else ""
            print(f"  {rel}  (deprecated in {removed_in}: {reason}{extra})")
        if prune:
            for rel in deprecated_orphans:
                (Path.cwd() / rel).unlink(missing_ok=True)
            print(f"  → pruned {len(deprecated_orphans)} deprecated file(s).")
        else:
            print("  → re-run install with --prune-deprecated to delete them.")
    if unknown_orphans:
        print(
            f"Untracked files under .opencode/ ({len(unknown_orphans)}) — not in "
            "MANIFEST or DEPRECATED:"
        )
        for rel in unknown_orphans:
            print(f"  {rel}  (no longer part of the harness; safe to remove)")


def latest_release_tag() -> str | None:
    url = f"https://api.github.com/repos/{REPO}/releases/latest"
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "opencode-agent-harness-installer"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
            return data.get("tag_name")
    except (urllib.error.URLError, json.JSONDecodeError, KeyError):
        return None


def describe_source_version(source: Path) -> str | None:
    """Best-effort version label for a local source from its git metadata.

    Returns `git describe --tags --always --dirty` (e.g. `v0.1.0` or
    `v0.1.0-3-gabc123-dirty`), or None if the path isn't a git repo / git is
    unavailable. Callers fall back to the bare 'local' label when None."""
    try:
        result = subprocess.run(
            ["git", "-C", str(source), "describe", "--tags", "--always", "--dirty"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            v = result.stdout.strip()
            return v or None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def installer_version() -> str:
    """Version label for this installer itself (not the payload)."""
    return describe_source_version(Path(__file__).parent) or "unknown"


def update_invocation_hint(command: str = "status") -> str:
    """Return the right way to re-invoke this installer for `command`.

    Detects whether we were run from a file path (clone user) or piped via
    stdin (curl|python3 one-liner user) by inspecting sys.argv[0]:
      - `'-'` → piped via stdin → re-curl to re-invoke.
      - else  → file path → call by absolute path.

    `command` is one of: status. (install is idempotent, so re-running it is
    the refresh path; we hint status for inspection.)
    """
    if sys.argv and sys.argv[0] == "-":
        return f"curl -fsSL {INSTALLER_URL} | python3 - {command}"
    invoked_as = Path(sys.argv[0]).resolve() if sys.argv else Path(__file__)
    return f"python3 {invoked_as} {command}"


# ── source resolution ────────────────────────────────────────────────────────


def resolve_source(from_path: str | None, tag: str | None) -> tuple[Path, str, bool]:
    """Return (source_root, version_label, cleanup_needed)."""
    if from_path:
        p = Path(from_path)
        if p.is_dir():
            ver = tag or describe_source_version(p) or "local"
            return p.resolve(), ver, False
        if p.is_file() and (p.suffix == ".gz" or ".tar" in p.name):
            extracted = extract_tarball(p)
            return extracted, tag or "local", True
        raise SystemExit(
            f"--from path is neither a directory nor a tarball: {from_path}"
        )

    effective_tag = tag or latest_release_tag() or "main"
    url = f"https://codeload.github.com/{REPO}/tar.gz/refs/{'tags' if tag else 'heads'}/{effective_tag}"
    if not tag and effective_tag != "main":
        url = f"https://codeload.github.com/{REPO}/tar.gz/refs/tags/{effective_tag}"

    print(f"Fetching {effective_tag} from GitHub…")
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "opencode-agent-harness-installer"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            tmp_tar = Path(tempfile.mktemp(suffix=".tar.gz"))
            tmp_tar.write_bytes(resp.read())
    except urllib.error.URLError as e:
        raise SystemExit(
            f"Failed to fetch from GitHub: {e}\nTry --from <local-clone> instead."
        )

    extracted = extract_tarball(tmp_tar)
    tmp_tar.unlink(missing_ok=True)
    return extracted, effective_tag, True


def extract_tarball(tarball_path: Path) -> Path:
    """Extract a tarball and return the directory containing .opencode/."""
    extract_dir = Path(tempfile.mkdtemp(prefix="harness-src-"))
    with tarfile.open(tarball_path, "r:gz") as tf:
        tf.extractall(extract_dir)

    # GitHub tarballs have a single top-level dir; find .opencode/ inside it
    for candidate in extract_dir.iterdir():
        if (candidate / OPENCODE_PREFIX).is_dir():
            return candidate

    # Maybe .opencode/ is directly in extract_dir
    if (extract_dir / OPENCODE_PREFIX).is_dir():
        return extract_dir

    raise SystemExit(f"Tarball does not contain .opencode/ directory: {tarball_path}")


# ── commands ─────────────────────────────────────────────────────────────────


def cmd_install(args) -> int:
    source_root, version, _cleanup = resolve_source(args.from_path, args.tag)

    install_files, manifest_gated = resolve_install_files(source_root)
    if not install_files:
        raise SystemExit(
            "No harness files found (MANIFEST empty or .opencode/ missing)."
        )

    # MANIFEST could drift from the tree if a maintainer forgot to keep them in
    # sync — lint-manifest catches this at dev time; here we fail loudly at
    # install time rather than copying a partial set.
    missing = [str(f) for f in install_files if not f.is_file()]
    if missing:
        raise SystemExit(
            "MANIFEST declares files not present in the source:\n  "
            + "\n  ".join(sorted(missing))
            + "\nThis source is inconsistent; use a different --tag or --from."
        )

    if not manifest_gated:
        print(
            "Note: source has no MANIFEST (predates v0.4.0); discovering files "
            "via rglob. Leak protection is inactive for this source."
        )

    # Pre-flight: classify every source file against what's already on disk.
    # Idempotent — a file whose content already matches the harness is a no-op,
    # not a conflict. Only genuine divergence needs a decision.
    to_write: list[tuple[Path, Path]] = []  # (src, dest) — absent or to overwrite
    up_to_date = 0
    divergent: list[str] = []

    for src_file in install_files:
        rel = src_file.relative_to(source_root)
        dest = Path(rel)
        if not dest.exists():
            to_write.append((src_file, dest))
        elif dest.read_bytes() == src_file.read_bytes():
            up_to_date += 1
        else:
            # Divergence: track it regardless of flag so the summary can report
            # what was kept. The flag decides whether it gets overwritten.
            divergent.append(str(rel))
            if args.force:
                to_write.append((src_file, dest))
            # --skip-existing and the default both keep it; default aborts later.

    if divergent and not args.force and not args.skip_existing:
        print(
            f"\nWARNING: {len(divergent)} local file(s) differ from the harness "
            "and would be OVERWRITTEN:"
        )
        for d in divergent:
            print(f"  {d}")
        print(
            "\nThis installer is for initial setup — re-running overwrites by "
            "design, and overwriting is always your explicit decision:"
        )
        print("  --force          overwrite the files listed above")
        print("  --skip-existing  keep your versions, write only missing files")
        print("\nNothing was changed. Re-run with one of these flags to proceed.")
        return 1

    # Copy pass.
    written = 0
    overwritten = 0
    for src_file, dest in to_write:
        already = dest.exists()
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dest)
        if already:
            overwritten += 1
        else:
            written += 1

    # (Re)write the manifest so `status` reflects this exact install. Record
    # only the tracked install set — NOT orphaned leftovers on disk — so `status`
    # can later detect those orphans as untracked.
    tracked_rels = [str(f.relative_to(source_root)) for f in install_files]
    hashes = {}
    for rel in tracked_rels:
        p = Path(rel)
        if p.is_file():
            hashes[rel] = sha256_file(p)
    write_manifest(version, hashes)

    wrote_config = ensure_config()

    print(f"\nHarness installed (version {version}).")
    print(f"  Written: {written}  Overwritten: {overwritten}  Up-to-date: {up_to_date}")
    if args.skip_existing and divergent:
        print(f"  Kept {len(divergent)} divergent local file(s) (--skip-existing)")
    if wrote_config:
        print(f"  Wrote default config: {CONFIG_FILES[0]}")
    print(f"  Manifest: {MANIFEST_REL}")

    # Orphan detection: downstream files the current source MANIFEST doesn't
    # track. Deprecated orphans get an explanation (and are pruned with
    # --prune-deprecated); unknown orphans are reported but never touched.
    tracked_set = set(tracked_rels)
    deprecated_map = read_source_deprecated(source_root)
    orphans = discover_downstream_orphans(tracked_set)
    report_orphans(orphans, deprecated_map, prune=args.prune_deprecated)

    print("\nNext steps:")
    print("  1. Restart opencode (config loads at startup).")
    print("  2. Run /adopt to detect your tech and scaffold AGENTS.md.")
    # install.py is never copied downstream; remind the user how to reach it
    # again for status, adapting to whether they piped via curl or invoked a
    # local file.
    print("\nTo inspect later (installer stays in source repo):")
    print(f"  {update_invocation_hint('status')}")
    return 0


def cmd_status(args) -> int:
    manifest = read_manifest()
    if manifest is None:
        print("No harness installation found. Use 'install' first.")
        return 1

    version = manifest.get("version", "unknown")
    files = manifest.get("files", {})
    clean = 0
    modified = 0
    missing = 0

    for rel, expected_hash in files.items():
        p = Path(rel)
        if not p.exists():
            missing += 1
        elif sha256_file(p) == expected_hash:
            clean += 1
        else:
            modified += 1

    print(f"Harness version: {version}")
    print(
        f"  Files: {len(files)} total  ({clean} clean, {modified} modified, {missing} missing)"
    )

    # Orphans: downstream .opencode/ files not recorded in this install's
    # manifest — leftovers from a prior version (e.g. a removed command) or
    # user-added files. Detected self-contained (no source needed); reasons are
    # shown at install time when the DEPRECATED registry is available.
    orphans = discover_downstream_orphans(set(files.keys()))
    if orphans:
        print(
            f"  Orphans: {len(orphans)} untracked file(s) under .opencode/ "
            "(not in this install's manifest)"
        )
        for rel in orphans[:10]:
            print(f"    {rel}")
        if len(orphans) > 10:
            print(f"    ... and {len(orphans) - 10} more")
        print("  Re-run install for deprecation explanations, or remove manually.")
    else:
        print("  No orphans (every .opencode/ file is tracked).")

    latest = latest_release_tag()
    if latest and latest != version:
        print(f"  Newer harness available: {latest} (re-run install to refresh)")
    elif latest == version:
        print("  Up to date.")
    else:
        print("  (could not check for newer releases)")

    if modified or missing:
        return 1
    return 0


# ── main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="opencode-agent-harness installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # action="version" prints and exits before the required-subparser check,
    # so `install.py --version` works without specifying a subcommand.
    parser.add_argument(
        "--version",
        action="version",
        version=f"opencode-agent-harness installer {installer_version()}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_install = sub.add_parser("install", help="Install the harness into this project")
    p_install.add_argument("--tag", default=None, help="Specific git tag")
    p_install.add_argument(
        "--from", dest="from_path", default=None, help="Local dir or tarball"
    )
    p_install.add_argument(
        "--force", action="store_true", help="Overwrite divergent local files"
    )
    p_install.add_argument(
        "--skip-existing", action="store_true", help="Keep divergent local files"
    )
    p_install.add_argument(
        "--prune-deprecated",
        action="store_true",
        help="Delete deprecated orphan files (per DEPRECATED) found downstream",
    )
    p_install.set_defaults(func=cmd_install)

    p_status = sub.add_parser("status", help="Show installation status and drift")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
