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
- `scope` is required, concise, non-empty, and names the affected module, subsystem, or concern. Choose it using the repository evidence below; there is no universal list of scope values.
- The description may be Chinese, English, or a mixture. Keep it concrete and preserve code identifiers and established project names.
- The complete subject, including type, scope, punctuation, spaces, and Unicode characters, must be at most 72 characters and must remain one line.
- Use `build` for build-tool changes, `ci` for continuous-integration changes, and `chore` for other maintenance such as dependency or configuration updates.
- A body and footer are optional. They do not replace or relax the subject rules.

| Type | Meaning |
| --- | --- |
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Restructuring without feature changes or bug fixes |
| `perf` | Performance improvement |
| `docs` | Documentation change |
| `chore` | Maintenance, dependencies, or configuration |
| `revert` | Revert an earlier commit |
| `test` | Add or change tests |
| `style` | Formatting without logic changes |
| `build` | Build tool or build system change |
| `ci` | Continuous integration change |

Count Unicode code points (Python `len`), not bytes or terminal columns. Use exactly one ASCII space after the colon, no boundary whitespace in scope or description, and no control characters or Unicode line separators in the subject. Scope cannot contain parentheses. The validator requires Python 3.10 or newer; if no Python runtime is available, check the same rules using the agent's available tools. Skill instructions remain usable without Python.

When choosing a message, inspect the change and select one primary type that best describes its intent. For `revert`, identify the reverted commit when the context is available.

Choose the scope from the actual changes:

- Follow explicit user or repository scope rules first, including configured scope lists and the user's corrections for the current task. A correction establishes a choice in that context, not an alias for every repository.
- Identify the module, package, or service that owns the behavior being changed. Inspect its relevant commit history and reuse an established scope when it still fits. Unrelated recent commits, imported libraries, internal class names, and endpoint names do not establish the owner's scope.
- If no scope convention exists, prefer the actual owning module's name over a broader capability or a newly coined label. Preserve its identity, applying repository casing or prefix conventions when known; do not expand abbreviations, substitute synonyms, translate, or change word forms merely to make it sound descriptive. For a module named `Auth`, `auth` preserves the name; `authentication` needs its own repository or user evidence. Conversely, keep `authentication` when that is the established scope.
- Use a functional concern when it is the actual shared area of the change or no concrete owner applies. A directory or file name is evidence to interpret, not a mechanical rule. The repository name, branch name, current task, or a label such as `core` is not a default scope.
- Keep type and scope independent: an authentication fix, its tests, and its documentation may use `fix(auth)`, `test(auth)`, and `docs(auth)`. A repository that explicitly uses `tests` or `docs` as scopes may keep that convention; do not derive the scope only from the type or file extension.
- Supporting tests, documentation, contracts, or registration changes for one module's feature can keep that module's scope even when they live elsewhere. For behavior that genuinely spans modules, use an established shared subsystem or concern that covers the change. If unrelated changes need separate commits, propose that split within the user's authorized scope. Do not invent a shared module or list unrelated names merely to fill the required scope. If the affected area is still unknown after inspection, ask for the missing context.

The validator checks subject syntax and length. It cannot determine whether a scope accurately describes a diff; passing validation does not replace the scope selection above. The installer's `--scope user|project` selects an installation location and has no relation to commit scope values.

When the user asks only for a message, return the proposed subject (and an optional body) without staging or committing. When the user explicitly authorizes a commit, inspect the staged diff, validate the final message with `scripts/validate_commit_message.py`, and then run the requested Git command. Never stage unrelated changes automatically.

For deterministic enforcement outside an agent, read [references/enforcement.md](references/enforcement.md). It describes the optional `commit-msg` hook and CI check; installing either changes repository or Git configuration and requires the user's explicit request.
