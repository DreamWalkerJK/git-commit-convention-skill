# git-commit-convention-skill

一个可分发的 Agent Skill，用于生成、审查和校验统一的 Git commit 消息。

它把两个层次分开：

1. `SKILL.md` 指导 agent 分析变更并生成符合规则的消息。
2. 校验器、`commit-msg` hook 和 CI 在实际 Git 流程中拒绝不合规消息。

Skill 本身不能让没有加载它的 agent 或普通 Git 客户端自动遵守规范。因此项目提供项目级 `.agents/skills/` 和 Claude Code 的 `.claude/skills/` 示例，同时提供按 agent 和作用域复制 Skill 的安装器。

## 规则

标题格式为：

```text
<type>(<scope>): <description>
```

允许的 `type`：

```text
feat fix refactor perf docs chore revert test style build ci
```

标题必须满足：

- `scope` 非空；
- `description` 非空；
- 可以使用中文、英文或混合文字；
- 第一行不超过 72 个 Unicode 字符；
- 冒号后恰好使用一个空格；
- 不添加规则之外的 `!`、`BREAKING CHANGE` 或其他 type。

例如：

```text
feat(api): 添加分页查询
fix(auth): handle token expiry
docs(install): 补充安装说明
ci(github): validate commit messages
```

## 项目内容

```text
.agents/skills/git-commit-convention-skill/  # 通用项目级 Skill
.claude/skills/git-commit-convention-skill/  # Claude Code 项目级副本
.githooks/commit-msg                   # 可选本地 hook
.github/workflows/commit-message.yml   # 可选 CI 校验
scripts/install.py                     # 可预览、可恢复的安装器
scripts/validate_commit_range.py       # 校验一段提交历史
tests/                                  # 行为测试
```

## 本地验证

项目只使用 Python 标准库：

```powershell
python -m unittest discover -s tests -v
python scripts/validate_commit_range.py HEAD~5..HEAD
```

For a repository whose current commit has no parent (the first commit), pass
the commit itself, for example `python scripts/validate_commit_range.py HEAD`.

Skill 结构可以用 Agent Skills 规范提供的 `skills-ref validate` 检查；如果本机没有该命令，至少检查 `SKILL.md` 的 frontmatter 和目录名。

## 安装 Skill

默认只预览，不写入文件：

```powershell
python scripts/install.py install --agent generic --scope user
python scripts/install.py install --agent claude --scope project --project C:\path\to\project
```

确认预览无误后才加 `--apply`：

```powershell
python scripts/install.py install --agent generic --scope user --apply
```

支持的目标：

| agent | user 目录 | project 目录 |
| --- | --- | --- |
| `generic` | `~/.agents/skills/git-commit-convention-skill` | `.agents/skills/git-commit-convention-skill` |
| `codex` | `$CODEX_HOME/skills/git-commit-convention-skill`，未设置时 `~/.codex/skills/...` | `.agents/skills/git-commit-convention-skill` |
| `claude` | `~/.claude/skills/git-commit-convention-skill` | `.claude/skills/git-commit-convention-skill` |

默认不会覆盖已有目录。只有目标由本安装器创建并且包含管理标记时，`uninstall --apply` 才会删除它。`--force` 也不会覆盖没有管理标记的已有目录。

安装到当前用户的目录只影响当前用户；安装到项目目录才会随仓库分发。要让机器上的所有用户使用，应由管理员按照每个 agent 的组织级发现机制部署，不能把一个共享 `CODEX_HOME` 当成所有 agent 的通用目录，因为其中可能包含用户凭据和会话状态。

## 启用本地 hook

预览并确认仓库级 hook 配置：

```powershell
git config core.hooksPath .githooks
```

hook 使用项目内的同一校验器。它只影响当前仓库，不修改系统级 Git 配置；`--no-verify` 仍可绕过本地 hook，所以受保护分支应启用 CI required check。

## 发布和兼容性

Agent Skills 规范定义了 `SKILL.md` 的格式，但不规定所有 agent 共用的安装目录。项目把 `.agents/skills/` 作为跨客户端约定，并为 Codex、Claude Code 和 generic user/project scope 提供显式安装路径。其他 agent 需要把同一 Skill 复制或链接到它们的 documented skills directory。

在没有实际测试某个 agent 的版本前，项目不会声称该 agent 已兼容。云端或沙箱 agent 通常需要项目级 Skill、插件或平台级注册，无法看到本机用户目录。

GitHub 创建空仓库时可能产生一个平台生成的 `Initial commit`。本项目的 CI 在普通 push 和 pull request 中只检查新增的 commit 范围；如果要在首次推送时启用 CI，请创建空仓库时不要自动生成 README、license 或 `.gitignore`。现有非规范历史可以由管理员一次性整理，不能用 `--no-verify` 绕过新提交的检查。

## 发布到 GitHub

项目不会自动创建远程仓库，也不会保存 GitHub 凭据。先在 GitHub 创建一个空仓库，再在本地完成登录，然后执行：

```bash
git remote add origin https://github.com/<owner>/git-commit-convention-skill.git
git push --set-upstream origin main
git push origin v0.1.0
```

如果本地已经存在 `origin`，先用 `git remote set-url origin <url>` 更新地址。推送前确认 `git status` 干净，并确认远程仓库的可见性符合组织要求。发布后应在 GitHub Actions 中确认 `Commit message convention` 工作流成功，再把它设置为受保护分支的 required status check。

## License

MIT，见 [LICENSE](LICENSE)。
