# Enforcing the convention for every contributor

An agent skill guides an agent only when that agent discovers and loads it. To cover ordinary Git clients and agents that do not load skills, add the repository's `commit-msg` hook and run the same validator in server-side CI.

## Repository hook

Get `.githooks/commit-msg` and the complete `.agents/skills/git-commit-convention-skill/` directory from the [source repository](https://github.com/DreamWalkerJK/git-commit-convention-skill). Put both in the target repository, preserving executable permissions (or run `chmod +x .githooks/commit-msg` on Unix). Integrate the invocation with an existing hook if the repository already uses hooks. Otherwise, configure the checked-in hook directory:

```sh
git config core.hooksPath .githooks
```

The hook calls the same validator used by CI. It is repository-scoped and does not change system Git configuration. A local hook can still be bypassed with `git commit --no-verify`.

## CI

Copy `scripts/validate_commit_range.py` and `.github/workflows/commit-message.yml` from the source repository as well. The range checker imports the same installed validator. Run `python scripts/validate_commit_range.py <base>..<head>` for every pull request and push range. Mark the workflow as a required status check in branch protection if invalid messages must block merges. Check the final squash title when merging, since it can differ from PR commit titles.

## Distribution

Install the skill in each agent's documented skill directory. The Agent Skills format is portable, but discovery paths are implementation-specific. Project `.agents/skills/` is a useful cross-client convention; Claude Code also supports `.claude/skills/`, and Codex has its own user-level skills directory. Do not share an entire `CODEX_HOME` merely to share this skill because it may contain credentials and session state.
