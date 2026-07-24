#!/usr/bin/env python3
"""opencode-agent-harness installer.

Installs or updates the harness under .opencode/ in the current project.

Usage:
    python3 install.py install [--tag TAG] [--from PATH] [--force] [--skip-existing]
    python3 install.py update  [--tag TAG] [--from PATH]
    python3 install.py status

Flags:
    --tag TAG          Install a specific git tag (default: latest release or main)
    --from PATH        Use a local directory or tarball instead of GitHub
    --force            Overwrite conflicting files during install
    --skip-existing    Skip conflicting files during install
    -h, --help         Show this message
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

REPO = "kulapoo/opencode-agent-harness"
MANIFEST_REL = ".opencode/harness/harness.json"
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


def write_manifest(version: str, files: dict[str, str]) -> None:
    p = manifest_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump({"version": version, "files": files}, f, indent=2, sort_keys=True)
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
    """Return all files under .opencode/ in source_root, excluding harness.json."""
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


# ── source resolution ────────────────────────────────────────────────────────


def resolve_source(from_path: str | None, tag: str | None) -> tuple[Path, str, bool]:
    """Return (source_root, version_label, cleanup_needed)."""
    if from_path:
        p = Path(from_path)
        if p.is_dir():
            return p.resolve(), tag or "local", False
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

    if read_manifest() is not None:
        print("Harness already installed. Use 'update' instead.")
        return 1

    harness_files = list_harness_files(source_root)
    if not harness_files:
        raise SystemExit("No harness files found in source (.opencode/ missing).")

    # Pre-flight: detect conflicts before copying anything
    file_list = []
    conflicts: list[str] = []
    for src_file in harness_files:
        rel = src_file.relative_to(source_root)
        dest = Path(rel)
        if dest.exists():
            if args.force:
                file_list.append((src_file, dest))
            elif args.skip_existing:
                pass
            else:
                conflicts.append(str(rel))
        else:
            file_list.append((src_file, dest))

    if conflicts and not args.force and not args.skip_existing:
        print(f"\n{len(conflicts)} conflicting file(s) already exist:")
        for c in conflicts:
            print(f"  {c}")
        print("\nOptions: --force to overwrite, --skip-existing to keep yours.")
        return 1

    # Copy pass
    installed = 0
    skipped = len(harness_files) - len(file_list)
    for src_file, dest in file_list:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dest)
        installed += 1

    hashes = {}
    all_installed = list_harness_files(Path.cwd())
    for f in all_installed:
        rel = str(f.relative_to(Path.cwd()))
        hashes[rel] = sha256_file(f)

    write_manifest(version, hashes)

    wrote_config = ensure_config()

    print(f"\nInstalled {installed} file(s) (version {version}).")
    if skipped:
        print(f"Skipped {skipped} existing file(s).")
    if wrote_config:
        print(f"Wrote default config: {CONFIG_FILES[0]}")
    print(f"Manifest: {MANIFEST_REL}")
    print("\nNext steps:")
    print("  1. Restart opencode (config loads at startup).")
    print("  2. Run /adopt to detect your tech and scaffold AGENTS.md.")
    return 0


def cmd_update(args) -> int:
    manifest = read_manifest()
    if manifest is None:
        print("No harness installation found. Use 'install' first.")
        return 1

    source_root, version, _cleanup = resolve_source(args.from_path, args.tag)
    old_files = manifest.get("files", {})
    new_source_files = list_harness_files(source_root)
    new_rel_set = {str(f.relative_to(source_root)) for f in new_source_files}

    upgraded = 0
    preserved = 0
    added = 0
    removed = 0
    drift: list[str] = []

    # Process new/upgraded files
    for src_file in new_source_files:
        rel = str(src_file.relative_to(source_root))
        dest = Path(rel)

        if rel in old_files:
            if dest.exists():
                current_hash = sha256_file(dest)
                if current_hash == old_files[rel]:
                    # Untouched — safe to upgrade
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dest)
                    upgraded += 1
                else:
                    # User modified — preserve
                    preserved += 1
                    drift.append(f"  modified (preserved): {rel}")
            else:
                # Was in manifest but deleted by user — reinstall
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dest)
                upgraded += 1
        else:
            # New file upstream
            if dest.exists():
                # User created a file at this path independently
                preserved += 1
                drift.append(f"  conflict (preserved): {rel}")
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dest)
                added += 1

    # Process deleted upstream files
    for rel in old_files:
        if rel not in new_rel_set:
            dest = Path(rel)
            if dest.exists():
                current_hash = sha256_file(dest)
                if current_hash == old_files[rel]:
                    dest.unlink()
                    removed += 1
                else:
                    preserved += 1
                    drift.append(f"  modified (preserved): {rel}")
            # else: already gone

    # Rewrite manifest
    hashes = {}
    all_installed = list_harness_files(Path.cwd())
    for f in all_installed:
        rel_str = str(f.relative_to(Path.cwd()))
        hashes[rel_str] = sha256_file(f)
    write_manifest(version, hashes)

    wrote_config = ensure_config()

    print(f"\nUpdated to {version}.")
    print(
        f"  Upgraded: {upgraded}  Added: {added}  Removed: {removed}  Preserved: {preserved}"
    )
    if wrote_config:
        print(f"  Wrote default config: {CONFIG_FILES[0]}")
    if drift:
        print("\nDrift (user-modified files kept as-is):")
        for d in drift:
            print(d)
        print("\nTo force-overwrite a drifted file, delete it and run 'update' again.")
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

    latest = latest_release_tag()
    if latest and latest != version:
        print(f"  Update available: {latest}")
    elif latest == version:
        print("  Up to date.")
    else:
        print("  (could not check for updates)")

    if modified or missing:
        return 1
    return 0


# ── main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="opencode-agent-harness installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_install = sub.add_parser("install", help="Install the harness into this project")
    p_install.add_argument("--tag", default=None, help="Specific git tag")
    p_install.add_argument(
        "--from", dest="from_path", default=None, help="Local dir or tarball"
    )
    p_install.add_argument("--force", action="store_true", help="Overwrite conflicts")
    p_install.add_argument(
        "--skip-existing", action="store_true", help="Skip conflicts"
    )
    p_install.set_defaults(func=cmd_install)

    p_update = sub.add_parser("update", help="Update an existing installation")
    p_update.add_argument("--tag", default=None, help="Specific git tag")
    p_update.add_argument(
        "--from", dest="from_path", default=None, help="Local dir or tarball"
    )
    p_update.set_defaults(func=cmd_update)

    p_status = sub.add_parser("status", help="Show installation status and drift")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
