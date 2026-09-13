#!/usr/bin/env python3
"""Validate every commit in a Git revision range."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SKILL_SCRIPTS = Path(__file__).resolve().parents[1] / ".agents" / "skills" / "git-commit-convention-skill" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))
from validate_commit_message import validate  # noqa: E402


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-c", "i18n.logOutputEncoding=UTF-8", *args],
        check=True, encoding="utf-8", capture_output=True,
    )
    return result.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("revision_range", help="Git revision range, for example base..head")
    args = parser.parse_args()
    try:
        commits = git("rev-list", "--reverse", args.revision_range).splitlines()
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: cannot enumerate {args.revision_range}: {exc}", file=sys.stderr)
        return 2

    invalid = 0
    for commit in commits:
        try:
            message = git("show", "-s", "--format=%B", commit)
        except (OSError, subprocess.CalledProcessError) as exc:
            print(f"ERROR: cannot read commit {commit}: {exc}", file=sys.stderr)
            invalid += 1
            continue
        errors = validate(message)
        if errors:
            invalid += 1
            print(f"{commit[:12]}: invalid commit message", file=sys.stderr)
            for error in errors:
                print(f"  ERROR: {error}", file=sys.stderr)
        else:
            print(f"{commit[:12]}: OK")
    if invalid:
        print(f"ERROR: {invalid} commit(s) failed validation", file=sys.stderr)
        return 1
    print(f"OK: validated {len(commits)} commit(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
