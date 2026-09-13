#!/usr/bin/env python3
"""Preview or apply a reversible installation of the project Skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
import uuid
from pathlib import Path


SKILL_NAME = "git-commit-convention-skill"
MARKER = ".managed-by-git-commit-convention-skill.json"
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".agents" / "skills" / SKILL_NAME

# The original v0.1.0 installer did not record ownership hashes. These are its
# released payload bytes in LF and CRLF form, so migration needs no Git/network.
LEGACY_HASHES = {
    "SKILL.md": {
        "075671641f30e75e89764f05567328bd943e0524a1a7c39c5c329b03ac7fe3d5",
        "a2ba616716ca89a6a5d779e9fe20447e405ba4b40ba647182f4d4e02800e101d",
    },
    "references/enforcement.md": {
        "5326873b1ad678b4a9195288eb66ce43de114cac0fdf50ebc0b082aaf062fcdd",
        "fb428d3d40c8c40c64bffda12ef7c7ea6aa16ed6ae011ab967a3ffccea2ffcc2",
    },
    "scripts/__init__.py": {
        "d4d0fb32720eb529665c4cc6378f25cd595bc633ca11c6264f52d875778560fd",
        "dca56403cfe4b75485c790ac17ecc925579f08a78ae0cd5737683590916b663c",
    },
    "scripts/validate_commit_message.py": {
        "a8f357b1fe540eb3b80e9a49b0dc67ce932af6e178cb05eacc580491e556423c",
        "da52977080ae8d7936d1e1c137ddf1f6c49be9c6cf8cb79b95a515d955d75a7d",
    },
}


class UnsafeTarget(ValueError):
    """A target cannot be proved to be an unchanged managed installation."""


def codex_home() -> Path:
    configured = os.environ.get("CODEX_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".codex"


def destination(agent: str, scope: str, project: Path) -> Path:
    if scope == "project":
        parent = Path(".claude") / "skills" if agent == "claude" else Path(".agents") / "skills"
        return project / parent / SKILL_NAME
    if agent == "claude":
        return Path.home() / ".claude" / "skills" / SKILL_NAME
    if agent == "codex":
        return codex_home() / "skills" / SKILL_NAME
    return Path.home() / ".agents" / "skills" / SKILL_NAME


def marker_path(target: Path) -> Path:
    return target / MARKER


def reject_link(path: Path) -> None:
    # Reparse-point detection also covers Windows junctions on Python 3.10/3.11.
    attributes = getattr(path.lstat(), "st_file_attributes", 0)
    if path.is_symlink() or attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
        raise UnsafeTarget(f"refusing a symbolic link or junction: {path}")


def inventory(root: Path, *, source: bool = False) -> dict:
    reject_link(root)
    if not root.is_dir():
        raise UnsafeTarget(f"expected a directory: {root}")
    files: dict[str, str] = {}
    directories: list[str] = []

    def visit(directory: Path) -> None:
        for path in sorted(directory.iterdir()):
            relative = path.relative_to(root).as_posix()
            reject_link(path)
            if relative == MARKER:
                continue
            if source and (path.name == "__pycache__" or path.suffix == ".pyc"):
                continue
            if path.is_dir():
                directories.append(relative)
                visit(path)
            elif path.is_file():
                files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
            else:
                raise UnsafeTarget(f"unsupported filesystem entry: {path}")

    visit(root)
    return {"files": files, "directories": sorted(directories)}


def managed_inventory(target: Path, current_source: dict | None = None) -> tuple[dict, int]:
    actual = inventory(target)
    marker = marker_path(target)
    if not marker.is_file():
        raise UnsafeTarget("target exists without an installer marker; refusing to change it")
    try:
        metadata = json.loads(marker.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as error:
        raise UnsafeTarget("installer marker is invalid; refusing to change the target") from error
    if not isinstance(metadata, dict) or metadata.get("tool") != SKILL_NAME:
        raise UnsafeTarget("installer marker belongs to another tool or is invalid")
    version = metadata.get("format")
    if type(version) is not int:
        raise UnsafeTarget("installer marker format is invalid")
    if version == 2:
        expected = {"files": metadata.get("files"), "directories": metadata.get("directories")}
        if actual != expected:
            raise UnsafeTarget("installed files were edited, added, or removed; preserve your changes before retrying")
    elif version == 1:
        files = actual["files"]
        original_release = (
            files.keys() == LEGACY_HASHES.keys()
            and actual["directories"] == ["references", "scripts"]
            and all(digest in LEGACY_HASHES[name] for name, digest in files.items())
        )
        if not original_release and actual != current_source:
            raise UnsafeTarget("legacy installation differs from v0.1.0 and the current source; refusing to change it")
    else:
        raise UnsafeTarget(f"unsupported installer marker format: {version}")
    return actual, version


def plan(action: str, target: Path, apply: bool = False) -> None:
    print(f"Action: {action}")
    print(f"Source: {SOURCE}")
    print(f"Destination: {target}")
    if action in ("absent", "already installed"):
        print("Mode: no changes")
    else:
        print("Mode: apply" if apply else "Mode: preview (add --apply to change files)")


def backup_target(target: Path) -> Path:
    # Store backups beside the skills directory so recursive skill discovery
    # cannot load a removed or superseded SKILL.md. Validate both move targets.
    parent = target.parent.resolve()
    backup_root = parent.parent / f".{SKILL_NAME}-backups"
    backup_root.mkdir(exist_ok=True)
    reject_link(backup_root)
    backup = backup_root / uuid.uuid4().hex
    if target.resolve().parent != parent or backup_root.resolve().parent != parent.parent or backup.resolve().parent != backup_root.resolve():
        raise UnsafeTarget("target or backup resolved outside the intended directories")
    target.rename(backup)
    return backup


def install(target: Path, apply: bool, force: bool = False) -> int:
    # --force is retained for CLI compatibility, never as permission to discard
    # changes or to overwrite an unverified target.
    del force
    try:
        if not SOURCE.is_dir():
            raise OSError(f"source Skill is missing: {SOURCE}")
        source_state = inventory(SOURCE, source=True)
        existing = os.path.lexists(target)
        previous = None
        if existing:
            previous, version = managed_inventory(target, source_state)
            if version == 2 and previous == source_state:
                plan("already installed", target, apply)
                return 0
        plan("replace managed target" if existing else "create target", target, apply)
        if not apply:
            return 0

        parent = target.parent
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=f".{SKILL_NAME}-stage-", dir=parent) as temp:
            staged = Path(temp) / SKILL_NAME
            shutil.copytree(SOURCE, staged, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", MARKER))
            if inventory(staged) != source_state:
                raise OSError("source changed during staging; retry installation")
            marker_path(staged).write_text(
                json.dumps({"tool": SKILL_NAME, "format": 2, **source_state}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            backup = None
            if existing:
                if managed_inventory(target, source_state)[0] != previous:
                    raise UnsafeTarget("target changed during staging; refusing to replace it")
                backup = backup_target(target)
            elif os.path.lexists(target):
                raise UnsafeTarget("target appeared during staging; refusing to overwrite it")
            try:
                staged.rename(target)
            except OSError:
                if backup is not None:
                    try:
                        backup.rename(target)
                    except OSError:
                        print(f"Recovery backup (restore manually): {backup}", file=sys.stderr)
                raise
            if backup is not None:
                print(f"Previous installation preserved: {backup}")
        print(f"Installed: {target}")
        return 0
    except UnsafeTarget as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"ERROR: installation failed: {error}", file=sys.stderr)
        return 2


def uninstall(target: Path, apply: bool) -> int:
    try:
        if not os.path.lexists(target):
            plan("absent", target, apply)
            return 0
        source_state = inventory(SOURCE, source=True) if SOURCE.is_dir() else None
        managed_inventory(target, source_state)
        plan("remove managed target (preserve recovery backup)", target, apply)
        if apply:
            backup = backup_target(target)
            print(f"Removed: {target}")
            print(f"Recovery backup: {backup}")
        return 0
    except UnsafeTarget as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"ERROR: uninstall failed: {error}", file=sys.stderr)
        return 2


def status(target: Path) -> int:
    if not os.path.lexists(target):
        print(f"{target}: absent")
        return 0
    try:
        source_state = inventory(SOURCE, source=True) if SOURCE.is_dir() else None
        _, version = managed_inventory(target, source_state)
        print(f"{target}: managed (format {version}, unchanged)")
        return 0
    except (UnsafeTarget, OSError) as error:
        print(f"{target}: unverified ({error})")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("install", "uninstall", "status"))
    parser.add_argument("--agent", choices=("generic", "codex", "claude"), default="generic")
    parser.add_argument("--scope", choices=("user", "project"), default="user")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--apply", action="store_true", help="perform the previewed filesystem change")
    parser.add_argument("--force", action="store_true", help="compatibility flag; never discards unverified or edited files")
    args = parser.parse_args()
    target = destination(args.agent, args.scope, args.project.resolve())
    if args.command == "install":
        return install(target, args.apply, args.force)
    if args.command == "uninstall":
        return uninstall(target, args.apply)
    return status(target)


if __name__ == "__main__":
    raise SystemExit(main())
