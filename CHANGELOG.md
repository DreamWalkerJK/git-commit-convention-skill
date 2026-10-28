# Changelog

## 0.1.3 - 2026-10-28

- Preserve the owning module's name when choosing a commit scope instead of inventing synonyms or expanding abbreviations; respect explicit rules, task-specific user corrections, and relevant scope history.
- Keep a module's scope for supporting changes outside its source directory, and distinguish those changes from behavior shared across modules.
- Add generic semantic evaluation cases for module ownership, explicit scope rules, relevant history, user corrections, and cross-module changes.

## 0.1.2 - 2026-10-26

- Choose commit scopes from explicit repository rules, relevant history, and the actual diff; clarify that syntax validation cannot verify scope meaning.
- Keep scope selection consistent between the canonical Skill, Claude Code copy, and Chinese/English documentation.
- Preserve raw line endings in message files and Git history so a bare carriage return cannot hide an invalid or overlong subject; report unreadable history as an operational error.
- Reject a missing canonical Skill during synchronization; stage replacements and restore or retain the previous copy when synchronization fails.
- Allow managed installations to be checked, upgraded, or uninstalled after Python creates caches for managed source files; continue protecting user additions and preserve caches in recovery backups.

## 0.1.1 - 2026-09-13

- Restore executable hook permissions and LF checkout; choose a working Python runtime on Windows, macOS, and Linux.
- Decode commit input and history as UTF-8; reject control characters and Unicode separators that can hide an overlong subject.
- Preserve edited installations, make repeat installs a no-op, verify file ownership, and retain backups when upgrading or uninstalling.
- Test actual Git hooks, installer recovery, and packaging on three operating systems.
- Publish a standalone Skill archive, source archive, and SHA-256 checksums after release tests pass.

## 0.1.0 - 2026-09-13

- Initial implementation of the reusable Agent Skill, validator, installer, hook, and CI workflow.
