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
