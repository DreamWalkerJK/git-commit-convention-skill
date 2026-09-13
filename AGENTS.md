# Repository instructions

This repository implements the `git-commit-convention-skill` Agent Skill and its deterministic Git message validator.

- Keep the canonical project skill in `.agents/skills/git-commit-convention-skill/` and keep the Claude Code copy synchronized with `python scripts/sync_skill.py`.
- Preserve the exact format `<type>(<scope>): <description>` and the eleven allowed types documented in `SKILL.md`.
- Count the complete subject with Python Unicode string length; the maximum is 72 characters.
- Changes to the validator require tests for both accepted and rejected messages.
- Do not install a hook, modify global Git configuration, or install a user-level Skill during development unless the user explicitly requests that operation.
