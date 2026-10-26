# Changelog

## Unreleased

- Choose commit scopes from explicit repository rules, relevant history, and the actual diff; clarify that syntax validation cannot verify scope meaning.
- Keep scope selection consistent between the canonical Skill, Claude Code copy, and Chinese/English documentation.

## 0.1.1 - 2026-09-13

- Restore executable hook permissions and LF checkout; choose a working Python runtime on Windows, macOS, and Linux.
- Decode commit input and history as UTF-8; reject control characters and Unicode separators that can hide an overlong subject.
- Preserve edited installations, make repeat installs a no-op, verify file ownership, and retain backups when upgrading or uninstalling.
- Test actual Git hooks, installer recovery, and packaging on three operating systems.
- Publish a standalone Skill archive, source archive, and SHA-256 checksums after release tests pass.

## 0.1.0 - 2026-09-13

- Initial implementation of the reusable Agent Skill, validator, installer, hook, and CI workflow.
