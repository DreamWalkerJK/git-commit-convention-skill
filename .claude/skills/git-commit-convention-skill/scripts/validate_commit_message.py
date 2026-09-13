#!/usr/bin/env python3
"""Validate a commit message against git-commit-convention-skill."""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path


ALLOWED_TYPES = frozenset(
    {"feat", "fix", "refactor", "perf", "docs", "chore", "revert", "test", "style", "build", "ci"}
)
MAX_SUBJECT_LENGTH = 72

# Scope may contain spaces and non-ASCII characters, but not parentheses or
# line breaks. Boundary whitespace is rejected so that the visible format is
# deterministic. Description must contain at least one non-whitespace char.
SUBJECT_RE = re.compile(
    r"^(?P<type>[a-z]+)\((?P<scope>[^()\s](?:[^()\r\n]*[^()\s])?)\): (?P<description>\S(?:.*\S)?)$"
)


def validate(message: str) -> list[str]:
    """Return human-readable validation errors for a commit message."""
    if not message:
        return ["commit message is empty"]

    subject = message.split("\n", 1)[0].removesuffix("\r")
    errors: list[str] = []
    if any(unicodedata.category(char) in {"Cc", "Zl", "Zp"} for char in subject):
        errors.append("subject must not contain control characters or line separators")
    if len(subject) > MAX_SUBJECT_LENGTH:
        errors.append(
            f"subject is {len(subject)} characters; maximum is {MAX_SUBJECT_LENGTH}"
        )

    match = SUBJECT_RE.fullmatch(subject)
    if not match:
        errors.append("subject must match '<type>(<scope>): <description>'")
        return errors

    commit_type = match.group("type")
    if commit_type not in ALLOWED_TYPES:
        errors.append(
            "type must be one of: " + ", ".join(sorted(ALLOWED_TYPES))
        )
    return errors


def main() -> int:
    if len(sys.argv) > 2:
        print("usage: validate_commit_message.py [MESSAGE_FILE]", file=sys.stderr)
        return 2
    try:
        message = (
            Path(sys.argv[1]).read_text(encoding="utf-8")
            if len(sys.argv) == 2
            else sys.stdin.buffer.read().decode("utf-8")
        )
    except (OSError, UnicodeError) as exc:
        print(f"ERROR: cannot read commit message: {exc}", file=sys.stderr)
        return 2

    errors = validate(message)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("OK: commit subject follows git-commit-convention-skill")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
