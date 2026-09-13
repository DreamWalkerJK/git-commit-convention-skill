---
name: git-commit-convention-skill
description: Create, review, or validate Git commit messages using the shared bilingual format, allowed types, required scope, and 72-character subject limit.
metadata:
  short-description: Enforce the shared Git commit message convention
---

# Git commit convention

Use this skill when a user asks to write, revise, validate, amend, revert, or create a Git commit. Do not invoke it for read-only Git questions that do not concern a commit message.

Apply these rules to the subject, which is the first line of the message:

- Format: `<type>(<scope>): <description>`.
- `type` must be exactly one of `feat`, `fix`, `refactor`, `perf`, `docs`, `chore`, `revert`, `test`, `style`, `build`, or `ci`.
- `scope` is required, concise, non-empty, and names the affected module, subsystem, or concern. Do not invent one when the changed area is unknown; inspect the diff or ask for the missing context.
- The description may be Chinese, English, or a mixture. Keep it concrete and preserve code identifiers and established project names.
- The complete subject, including type, scope, punctuation, spaces, and Unicode characters, must be at most 72 characters and must remain one line.
- Use `build` for build-tool changes, `ci` for continuous-integration changes, and `chore` for other maintenance such as dependency or configuration updates.
- A body and footer are optional. They do not replace or relax the subject rules.

When choosing a message, inspect the change and select one primary type that best describes its intent. For `revert`, identify the reverted commit when the context is available.

When the user asks only for a message, return the proposed subject (and an optional body) without staging or committing. When the user explicitly authorizes a commit, inspect the staged diff, validate the final message with `scripts/validate_commit_message.py`, and then run the requested Git command. Never stage unrelated changes automatically.

For deterministic enforcement outside an agent, read [references/enforcement.md](references/enforcement.md). It describes the optional `commit-msg` hook and CI check; installing either changes repository or Git configuration and requires the user's explicit request.
