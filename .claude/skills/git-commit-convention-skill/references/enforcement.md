# Enforcing the convention for every contributor

An agent skill guides an agent only when that agent discovers and loads it. To cover ordinary Git clients and agents that do not load skills, add the repository's `commit-msg` hook and run the same validator in server-side CI.

## Repository hook

From the repository root, configure the checked-in hook directory:

```sh
git config core.hooksPath .githooks
```

The hook calls the same validator used by CI. It is repository-scoped and does not change system Git configuration. A local hook can still be bypassed with `git commit --no-verify`.

## CI

Run `python scripts/validate_commit_range.py <base>..<head>` for every pull request and push range. Mark the workflow as a required status check in branch protection if invalid messages must block merges.

## Distribution

Install the skill in each agent's documented skill directory. The Agent Skills format is portable, but discovery paths are implementation-specific. Project `.agents/skills/` is a useful cross-client convention; Claude Code also supports `.claude/skills/`, and Codex has its own user-level skills directory. Do not share an entire `CODEX_HOME` merely to share this skill because it may contain credentials and session state.
