#!/usr/bin/env python3
"""Synchronize the canonical project skill into Claude Code's project path."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".agents" / "skills" / "git-commit-convention-skill"
TARGET = ROOT / ".claude" / "skills" / "git-commit-convention-skill"


def files(root: Path) -> list[Path]:
    return sorted(
        p.relative_to(root)
        for p in root.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail when the copies differ")
    args = parser.parse_args()
    source_files = files(SOURCE)
    target_files = files(TARGET)
    if args.check:
        if source_files != target_files or any(
            (SOURCE / relative).read_bytes() != (TARGET / relative).read_bytes()
            for relative in source_files
        ):
            print("ERROR: .claude skill copy is out of sync")
            return 1
        print("OK: skill copies are synchronized")
        return 0
    if TARGET.exists():
        shutil.rmtree(TARGET)
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE, TARGET, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    print(f"Synchronized {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
