# git-commit-convention-skill

[中文](#中文) | [English](#english)

## 中文

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
- scope 和描述首尾不留空白，scope 不含括号，标题不含控制字符或 Unicode 换行分隔符；
- 标题不使用 `!` 或其他 type；body/footer 可选，不强制增加 `BREAKING CHANGE`。

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

纯文本 Skill 不要求 Python。确定性校验器和安装器需要 Python 3.10 或更新版本，只使用标准库：

```powershell
python -m unittest discover -s tests -v
python scripts/validate_commit_range.py 7f83136..HEAD
```

上面的范围检查本仓库采用规范之后的提交，其他项目应换成自己的 `base..head`。传入 `HEAD` 会检查全部可达历史，包括 GitHub 创建的非规范 `Initial commit`；它会如实失败。没有历史豁免规则。

Skill 结构可以用 Agent Skills 规范提供的 `skills-ref validate` 检查；如果本机没有该命令，至少检查 `SKILL.md` 的 frontmatter 和目录名。

## 安装 Skill

先获取源码；仓库的 README、脚本和引用文件都可以一起复制到其他机器，内部不依赖当前用户名或盘符：

```bash
git clone https://github.com/DreamWalkerJK/git-commit-convention-skill.git
cd git-commit-convention-skill
```

也可以从 [GitHub Releases](https://github.com/DreamWalkerJK/git-commit-convention-skill/releases) 获取独立 Skill ZIP，解压后把完整的 `git-commit-convention-skill` 目录放进目标 agent 的技能目录。ZIP 内带 LICENSE，不需要安装器；手工复制的目录仍由用户自行管理。

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

安装器默认只预览。已有非本工具管理的目录不会被覆盖；有本地修改、额外文件或无效标记的目录也会拒绝自动变更。完全相同的重复安装保持文件和时间戳不变。更新和卸载会把恢复备份放到技能扫描目录之外，例如 `~/.codex/.git-commit-convention-skill-backups/<uuid>/`，并输出路径；需要恢复时，可把备份移回原技能位置。`--force` 是兼容参数，不绕过上述检查。备份由用户检查后自行删除。

检查与卸载示例：

```bash
python scripts/install.py status --agent codex --scope user
python scripts/install.py uninstall --agent codex --scope user
python scripts/install.py uninstall --agent codex --scope user --apply
```

安装到当前用户的目录只影响当前用户；安装到项目目录才会随仓库分发。要让机器上的所有用户使用，应由管理员按照每个 agent 的组织级发现机制部署，不能把一个共享 `CODEX_HOME` 当成所有 agent 的通用目录，因为其中可能包含用户凭据和会话状态。

多用户分发可把发布的 Skill 目录放在 Windows `C:\ProgramData\AgentSkills\` 或 Linux/macOS `/opt/agent-skills/`，授予普通用户读取权限、管理员写权限，再通过账号初始化或设备管理把副本部署到每个用户的客户端技能目录。新用户也需要账号初始化步骤。共享位置本身不会自动被所有 agent 扫描；不支持 Skills 的 agent 可以通过项目指令显式读取 `SKILL.md`。云端 agent 需要仓库内技能或平台提供的组织级注册方式。

当前 Codex 支持 `.agents/skills/` 与自身技能目录；同名副本应由同一版本更新，避免规则分歧。纯文本安装可在下一次会话或客户端重新加载技能后验证。显式请求示例：`使用 git-commit-convention-skill，为暂存改动生成中文提交消息`。

## 启用本地 hook

在含本项目 `.githooks/commit-msg` 和 `.agents/skills/git-commit-convention-skill/` 的目标仓库中启用：

```powershell
git config core.hooksPath .githooks
```

hook 使用项目内的同一校验器。它只影响当前仓库，不修改系统级 Git 配置；`--no-verify` 仍可绕过本地 hook，所以受保护分支应启用 CI required check。

若目标已配置 hooksPath，应把校验调用接入原有 hook，避免覆盖原有行为。Unix 可执行位及 LF 换行由 Git 记录；若通过 ZIP 安装 hook，在 Unix 上还需执行 `chmod +x .githooks/commit-msg`。Skill 安装器只安装技能，不修改 hooksPath。

## 发布和兼容性

Agent Skills 规范定义了 `SKILL.md` 的格式，但不规定所有 agent 共用的安装目录。项目把 `.agents/skills/` 作为跨客户端约定，并为 Codex、Claude Code 和 generic user/project scope 提供显式安装路径。其他 agent 需要把同一 Skill 复制或链接到它们的 documented skills directory。

在没有实际测试某个 agent 的版本前，项目不会声称该 agent 已兼容。云端或沙箱 agent 通常需要项目级 Skill、插件或平台级注册，无法看到本机用户目录。

GitHub 创建仓库时可能产生一个平台生成的 `Initial commit`。本项目的 CI 在普通 push 和 pull request 中检查新增 commit 范围；新分支首次 push 会检查其可达历史。自动生成的 merge/revert 标题也必须遵守规范。Squash merge 的最终标题还需由维护者检查；PR 提交校验无法提前保证合并时才输入的标题。

自动化覆盖 Windows、macOS、Linux 的 Python 3.10/3.13；测试会在临时仓库中真实执行 hook，检查 UTF-8、72/73 字符边界、CRLF、非法类型和安装生命周期。绿色测试证明脚本在这些环境运行，不代表每个 agent 版本都已实测发现能力。Codex 的技能列表已验证能发现本项目级及当前用户级安装；Claude Code 安装文件已核对，其他客户端仍需按自身技能机制验证。

## 发布到 GitHub

项目不会自动创建远程仓库，也不会保存 GitHub 凭据。先在 GitHub 创建一个空仓库，再在本地完成登录，然后执行：

```bash
git remote add origin https://github.com/<owner>/git-commit-convention-skill.git
git push --set-upstream origin main
git tag -a v0.1.1 -m "Release v0.1.1"
git push origin v0.1.1
```

如果本地已经存在 `origin`，先用 `git remote set-url origin <url>` 更新地址。推送前确认 `git status` 干净，并确认远程仓库的可见性符合组织要求。发布后应在 GitHub Actions 中确认 `Commit message convention` 工作流成功，再把它设置为受保护分支的 required status check。

`Publish skill release` 在标签与 VERSION 一致且三系统测试通过后发布 Skill ZIP、源码 ZIP 和 SHA-256 校验文件。已发布标签不移动，后续修复使用新版本。本地可在干净、已提交的工作树运行 `python scripts/package_release.py` 生成相同布局的归档。`Portable skill tests` 校验脚本与同步副本；本地 hook 仅为提前反馈。

## License

MIT，见 [LICENSE](LICENSE)。

---

## English

A portable, cross-platform Agent Skill for Git commit conventions, supporting Codex, Claude Code, and compatible clients. Standardizes Chinese and English messages with `<type>(<scope>): <description>` and a 72-character subject limit. Includes a validator, optional Git hooks, CI checks, and recoverable installation and upgrades.

This distributable Agent Skill helps generate, review, and validate consistent Git commit messages.

It separates two layers:

1. `SKILL.md` guides agents through analyzing changes and generating messages that follow the convention.
2. The validator, `commit-msg` hook, and CI reject noncompliant messages in the actual Git workflow.

A Skill alone cannot make an agent that has not loaded it, or an ordinary Git client, follow the convention automatically. The project therefore provides project-level examples under `.agents/skills/` and Claude Code's `.claude/skills/`, along with an installer that copies the Skill for a selected agent and scope.

### Rules

The subject format is:

```text
<type>(<scope>): <description>
```

Allowed `type` values:

```text
feat fix refactor perf docs chore revert test style build ci
```

The subject must meet these requirements:

- `scope` must be nonempty;
- `description` must be nonempty;
- Chinese, English, or a mix of both is allowed;
- The first line must contain no more than 72 Unicode characters;
- The colon must be followed by exactly one space;
- Neither the scope nor the description may have leading or trailing whitespace; the scope must not contain parentheses, and the subject must not contain control characters or Unicode line separators;
- The subject must not use `!` or any other type; the body and footer are optional, and `BREAKING CHANGE` is not required.

Examples:

```text
feat(api): 添加分页查询
fix(auth): handle token expiry
docs(install): 补充安装说明
ci(github): validate commit messages
```

### Project contents

```text
.agents/skills/git-commit-convention-skill/  # Generic project-level Skill
.claude/skills/git-commit-convention-skill/  # Claude Code project-level copy
.githooks/commit-msg                       # Optional local hook
.github/workflows/commit-message.yml       # Optional CI validation
scripts/install.py                        # Installer with preview and recovery
scripts/validate_commit_range.py           # Validate a range of commits
tests/                                    # Behavior tests
```

### Local validation

The plain-text Skill does not require Python. The deterministic validator and installer require Python 3.10 or later and use only the standard library:

```powershell
python -m unittest discover -s tests -v
python scripts/validate_commit_range.py 7f83136..HEAD
```

The range above checks commits made after this repository adopted the convention. Other projects should substitute their own `base..head`. Passing `HEAD` checks all reachable history, including a noncompliant `Initial commit` created by GitHub; that check will correctly fail. There are no exemptions for historical commits.

You can check the Skill structure with `skills-ref validate` from the Agent Skills specification tooling. If that command is unavailable locally, at least check the `SKILL.md` frontmatter and directory name.

### Install the Skill

First, obtain the source. The repository's README, scripts, and reference files can be copied together to another machine; they do not depend on the current username or drive letter:

```bash
git clone https://github.com/DreamWalkerJK/git-commit-convention-skill.git
cd git-commit-convention-skill
```

You can also download the standalone Skill ZIP from [GitHub Releases](https://github.com/DreamWalkerJK/git-commit-convention-skill/releases), extract it, and place the complete `git-commit-convention-skill` directory in the target agent's skills directory. The ZIP includes LICENSE and does not require the installer; manually copied directories remain under your own management.

By default, these commands only preview changes and do not write any files:

```powershell
python scripts/install.py install --agent generic --scope user
python scripts/install.py install --agent claude --scope project --project C:\path\to\project
```

Add `--apply` only after confirming the preview:

```powershell
python scripts/install.py install --agent generic --scope user --apply
```

Supported targets:

| agent | user directory | project directory |
| --- | --- | --- |
| `generic` | `~/.agents/skills/git-commit-convention-skill` | `.agents/skills/git-commit-convention-skill` |
| `codex` | `$CODEX_HOME/skills/git-commit-convention-skill`, or `~/.codex/skills/...` when unset | `.agents/skills/git-commit-convention-skill` |
| `claude` | `~/.claude/skills/git-commit-convention-skill` | `.claude/skills/git-commit-convention-skill` |

The installer previews changes by default. It will not overwrite an existing directory that it does not manage, and it refuses automatic changes to directories with local modifications, extra files, or an invalid management marker. Reinstalling identical content leaves files and timestamps unchanged. Updates and uninstalls place recovery backups outside the directories scanned for Skills, for example `~/.codex/.git-commit-convention-skill-backups/<uuid>/`, and print the backup path. To restore an installation, move the backup back to the original Skill location. `--force` is a compatibility option and does not bypass these checks. You can delete backups yourself after reviewing them.

Status and uninstall examples:

```bash
python scripts/install.py status --agent codex --scope user
python scripts/install.py uninstall --agent codex --scope user
python scripts/install.py uninstall --agent codex --scope user --apply
```

Installing in the current user's directory affects only that user; installing in a project directory allows the Skill to be distributed with the repository. To make it available to every user on a machine, an administrator should deploy it according to each agent's organization-level discovery mechanism. A shared `CODEX_HOME` must not be treated as a universal directory for all agents, because it may contain user credentials and session state.

For multi-user distribution, administrators can place the released Skill directory in `C:\ProgramData\AgentSkills\` on Windows or `/opt/agent-skills/` on Linux/macOS, grant ordinary users read access and administrators write access, then deploy copies into each user's client skills directory through account provisioning or device management. New users also need this provisioning step. A shared location is not automatically scanned by every agent. Agents without Skills support can be instructed through project instructions to read `SKILL.md` explicitly. Cloud agents need an in-repository Skill or an organization-level registration mechanism provided by their platform.

Current Codex versions support `.agents/skills/` and Codex's own skills directory. Copies with the same name should be updated to the same version to avoid conflicting rules. You can verify a plain-text installation in the next session or after the client reloads its Skills. An explicit request could be: `Use git-commit-convention-skill to generate a Chinese commit message for the staged changes`.

### Enable the local hook

Enable it in a target repository containing this project's `.githooks/commit-msg` and `.agents/skills/git-commit-convention-skill/`:

```powershell
git config core.hooksPath .githooks
```

The hook uses the same validator stored in the project. It affects only the current repository and does not modify system-level Git configuration. `--no-verify` can still bypass the local hook, so protected branches should require the CI check.

If the target repository already has a configured hooksPath, integrate the validation call into its existing hook to preserve the current behavior. Git records the Unix executable bit and LF line endings. If you install the hook from a ZIP on Unix, also run `chmod +x .githooks/commit-msg`. The Skill installer only installs the Skill and does not modify hooksPath.

### Distribution and compatibility

The Agent Skills specification defines the `SKILL.md` format but does not prescribe a single installation directory shared by all agents. This project uses `.agents/skills/` as a convention across clients and provides explicit installation paths for Codex, Claude Code, and generic user/project scopes. Other agents require copying or linking the same Skill into their documented skills directory.

The project does not claim compatibility with an agent version before it has been tested. Cloud or sandboxed agents usually need a project-level Skill, a plugin, or platform-level registration because they cannot see the local user's directories.

GitHub may generate an `Initial commit` when creating a repository. This project's CI checks the range of new commits on ordinary pushes and pull requests; the first push of a new branch checks its reachable history. Automatically generated merge/revert subjects must also follow the convention. Maintainers must check the final subject of a squash merge; validating PR commits cannot guarantee a subject that is entered only when the PR is merged.

Automation covers Python 3.10/3.13 on Windows, macOS, and Linux. Tests execute the hook in temporary repositories and check UTF-8, the 72/73-character boundary, CRLF, invalid types, and the installation lifecycle. Passing tests demonstrate that the scripts run in these environments; they do not prove that every agent version has been tested for Skill discovery. Codex's Skill listing has been verified to discover this project's installation and the current user's installations. The installed Claude Code files have been checked; other clients still need validation through their own Skill mechanisms.

### Publish to GitHub

The project does not automatically create a remote repository or store GitHub credentials. First, create an empty repository on GitHub and authenticate locally, then run:

```bash
git remote add origin https://github.com/<owner>/git-commit-convention-skill.git
git push --set-upstream origin main
git tag -a v0.1.1 -m "Release v0.1.1"
git push origin v0.1.1
```

If `origin` already exists locally, update its URL first with `git remote set-url origin <url>`. Before pushing, confirm that `git status` is clean and that the remote repository's visibility meets your organization's requirements. After publishing, verify that the `Commit message convention` workflow succeeds in GitHub Actions, then configure it as a required status check for protected branches.

`Publish skill release` publishes the Skill ZIP, source ZIP, and SHA-256 checksum file after the tag matches VERSION and tests pass on all three operating systems. Published tags are not moved; subsequent fixes use a new version. Locally, run `python scripts/package_release.py` in a clean, committed working tree to generate archives with the same layout. `Portable skill tests` checks the scripts and synchronized copies; the local hook provides early feedback.

### License

MIT; see [LICENSE](LICENSE).
