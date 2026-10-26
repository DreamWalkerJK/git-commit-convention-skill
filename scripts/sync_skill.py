#!/usr/bin/env python3
"""Synchronize the canonical project skill into Claude Code's project path."""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".agents" / "skills" / "git-commit-convention-skill"
TARGET = ROOT / ".claude" / "skills" / "git-commit-convention-skill"


def reject_link(path: Path) -> None:
    attributes = getattr(path.lstat(), "st_file_attributes", 0)
    if path.is_symlink() or attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
        raise ValueError(f"refusing a symbolic link or junction: {path}")


def contents(root: Path, *, require_skill: bool = False) -> dict[Path, bytes]:
    """Read the payload without following links or including Python caches."""
    reject_link(root)
    if not root.is_dir():
        raise ValueError(f"expected a Skill directory: {root}")
    result: dict[Path, bytes] = {}

    def visit(directory: Path) -> None:
        for path in sorted(directory.iterdir()):
            if path.name == "__pycache__" or path.suffix == ".pyc":
                continue
            reject_link(path)
            if path.is_dir():
                visit(path)
            elif path.is_file():
                result[path.relative_to(root)] = path.read_bytes()
            else:
                raise ValueError(f"unsupported filesystem entry: {path}")

    visit(root)
    if require_skill and Path("SKILL.md") not in result:
        raise ValueError(f"Skill is missing SKILL.md: {root}")
    return result


def require_child(path: Path, parent: Path) -> None:
    """Check the final absolute destination before a move or recursive delete."""
    resolved = path.resolve()
    if resolved == parent or not resolved.is_relative_to(parent):
        raise ValueError(f"path resolved outside the intended directory: {path}")
    if os.path.lexists(path):
        reject_link(path)


def _synchronize(check: bool) -> int:
    temporary: Path | None = None
    preserve_backup = False
    parent: Path | None = None
    try:
        repository = ROOT.resolve()
        if not SOURCE.resolve().is_relative_to(repository) or not TARGET.resolve().is_relative_to(repository):
            raise ValueError("Skill path resolved outside the repository")
        source = contents(SOURCE, require_skill=True)
        existing = os.path.lexists(TARGET)
        previous = contents(TARGET) if existing else None
        if check:
            if source != previous:
                print("ERROR: .claude skill copy is out of sync")
                return 1
            print("OK: skill copies are synchronized")
            return 0

        TARGET.parent.mkdir(parents=True, exist_ok=True)
        reject_link(TARGET.parent)
        parent = TARGET.parent.resolve()
        require_child(TARGET, parent)
        temporary = Path(tempfile.mkdtemp(prefix=f".{TARGET.name}-sync-", dir=parent))
        staged = temporary / "new"
        backup = temporary / "previous"
        shutil.copytree(SOURCE, staged, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        if contents(staged, require_skill=True) != source:
            raise ValueError("source changed during staging; retry synchronization")
        if existing:
            if contents(TARGET) != previous:
                raise ValueError("target changed during staging; refusing to replace it")
            require_child(TARGET, parent)
            require_child(backup, parent)
            TARGET.rename(backup)
        elif os.path.lexists(TARGET):
            raise ValueError("target appeared during staging; refusing to overwrite it")
        try:
            require_child(staged, parent)
            require_child(TARGET, parent)
            staged.rename(TARGET)
        except (OSError, ValueError):
            if existing:
                try:
                    require_child(backup, parent)
                    require_child(TARGET, parent)
                    backup.rename(TARGET)
                except (OSError, ValueError):
                    preserve_backup = True
                    print(f"Recovery backup (restore manually): {backup}", file=sys.stderr)
            raise
        print(f"Synchronized {TARGET}")
        return 0
    finally:
        if temporary is not None and not preserve_backup:
            assert parent is not None
            try:
                require_child(temporary, parent)
                shutil.rmtree(temporary)
            except (OSError, ValueError) as error:
                raise OSError(f"cannot clean synchronization staging {temporary}: {error}") from error


def synchronize(check: bool = False) -> int:
    try:
        return _synchronize(check)
    except (OSError, ValueError) as error:
        print(f"ERROR: synchronization failed: {error}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail when the copies differ")
    args = parser.parse_args()
    return synchronize(check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
