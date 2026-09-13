#!/usr/bin/env python3
"""Preview or apply a reversible installation of the project Skill."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


SKILL_NAME = "git-commit-convention-skill"
MARKER = ".managed-by-git-commit-convention-skill.json"
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".agents" / "skills" / SKILL_NAME


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


def plan(action: str, target: Path) -> None:
    print(f"Action: {action}")
    print(f"Source: {SOURCE}")
    print(f"Destination: {target}")
    print("Mode: preview (add --apply to change files)" if action != "absent" else "Mode: no changes")


def install(target: Path, apply: bool, force: bool) -> int:
    if not SOURCE.is_dir():
        print(f"ERROR: source Skill is missing: {SOURCE}", file=sys.stderr)
        return 2
    if target.exists():
        if not marker_path(target).is_file():
            if not force:
                plan("refuse existing unmanaged target", target)
                print("ERROR: target exists without an installer marker; refusing to overwrite", file=sys.stderr)
                return 1
            print("ERROR: --force cannot overwrite an unmanaged target", file=sys.stderr)
            return 1
        action = "replace managed target"
    else:
        action = "create target"
    plan(action, target)
    if not apply:
        return 0

    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{SKILL_NAME}-", dir=parent) as temp:
        staged = Path(temp) / SKILL_NAME
        shutil.copytree(SOURCE, staged, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        marker_path(staged).write_text(
            json.dumps({"tool": SKILL_NAME, "format": 1}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if target.exists():
            shutil.rmtree(target)
        shutil.move(str(staged), str(target))
    print(f"Installed: {target}")
    return 0


def uninstall(target: Path, apply: bool) -> int:
    if not target.exists():
        plan("absent", target)
        return 0
    if not marker_path(target).is_file():
        plan("refuse unmanaged target", target)
        print("ERROR: target is not marked as installed by this tool", file=sys.stderr)
        return 1
    plan("remove managed target", target)
    if apply:
        shutil.rmtree(target)
        print(f"Removed: {target}")
    return 0


def status(target: Path) -> int:
    state = "managed" if marker_path(target).is_file() else "unmanaged" if target.exists() else "absent"
    print(f"{target}: {state}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("install", "uninstall", "status"))
    parser.add_argument("--agent", choices=("generic", "codex", "claude"), default="generic")
    parser.add_argument("--scope", choices=("user", "project"), default="user")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--apply", action="store_true", help="perform the previewed filesystem change")
    parser.add_argument("--force", action="store_true", help="replace only an existing managed target")
    args = parser.parse_args()
    target = destination(args.agent, args.scope, args.project.resolve())
    if args.command == "install":
        return install(target, args.apply, args.force)
    if args.command == "uninstall":
        return uninstall(target, args.apply)
    return status(target)


if __name__ == "__main__":
    raise SystemExit(main())
