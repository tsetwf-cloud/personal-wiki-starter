# 工具安装与可选 Skill 安装

主教程无需全局安装 Skill：初始化会把公开规程复制到私人库的 `wiki_skills/`，提示词明确要求读取。这是三工具共同的基线，不假设自动发现机制一致。

## 安装一个 Agent 就够了

已有可用工具跳过本节。先核对官方页面，再执行与你的终端对应的命令；安装脚本会下载并运行代码。企业电脑先遵守软件政策。账号资格、地区可用性、网络和费用以提供方为准，不承诺免费。

### Codex CLI

官方：https://developers.openai.com/codex/cli

需要 Node.js 与 npm 的读者先按 Node.js 官方说明安装。已有 npm 时：

```text
npm install -g @openai/codex
codex --version
codex
```

在首次会话按提示登录。不要把登录材料放进 Wiki。Windows 可选官方支持的原生环境或 WSL；本项目实际 AI 验收在 WSL。私人目录不必为了本教程上传 GitHub。

若某版本的非交互命令要求 Git 仓库，本机 `codex exec --help` 可确认是否提供 `--skip-git-repo-check`；它只是非交互使用的仓库检查选项，不是关闭沙箱。主教程使用交互 `codex`，不要求读者创建公开仓库。

### Claude Code

官方：https://code.claude.com/docs/en/quickstart

Linux / macOS / WSL 的 Bash：

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

原生 Windows PowerShell：

```powershell
irm https://claude.ai/install.ps1 | iex
```

重新打开终端：

```text
claude --version
claude
```

按首次会话提示登录。需要有支持 Claude Code 的账号、API 或受支持服务，普通免费网页账号不等于已取得相同权限。

### Hermes

官方：https://hermes-agent.nousresearch.com/docs/getting-started/installation

本文 Hermes 路线使用 Linux / macOS / Windows WSL。Windows WSL 按微软说明安装：https://learn.microsoft.com/windows/wsl/install 。Ubuntu 与原生 PowerShell 不是同一个终端。

Bash：

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

重新打开终端后：

```bash
hermes --version
hermes model
hermes
```

按向导选择已有资格且允许处理所选资料的模型。不能读写文件时核对 `hermes tools` 的文件与终端能力；安装故障先用 `hermes doctor`，不要关闭全部审批。

## 熟悉以后，再选原生 Skill 安装

以下不是完成主教程的前置条件。先检查文件，遇到同名文件先比较，不能覆盖自己改过的版本。安装之后开新会话，确认实际能发现。表述上区分：文件已复制、列表已发现、实际已使用。

### Codex：项目级 `.agents/skills`

从私人 Wiki 根目录，Bash 执行：

```bash
mkdir -p .agents/skills
cp -Rn wiki_skills/wiki-context-reader .agents/skills/
cp -Rn wiki_skills/wiki-review-intake .agents/skills/
cp -Rn wiki_skills/wiki-approved-merge .agents/skills/
```

在新会话使用 `/skills` 查看，或在消息里用 `$wiki-context-reader`、`$wiki-review-intake`、`$wiki-approved-merge` 显式引用。若当前版本没有发现，就回到精确路径读取，不声称安装成功。

### Claude Code：项目级 `.claude/skills`

从私人 Wiki 根目录，Bash 执行：

```bash
mkdir -p .claude/skills
cp -Rn wiki_skills/wiki-context-reader .claude/skills/
cp -Rn wiki_skills/wiki-review-intake .claude/skills/
cp -Rn wiki_skills/wiki-approved-merge .claude/skills/
```

新会话可输入 `/wiki-context-reader`、`/wiki-review-intake` 或 `/wiki-approved-merge`。这些是聊天输入，不是终端命令。

### Windows PowerShell：项目级复制

在私人库根目录运行。Codex 使用下方 `.agents/skills`；Claude Code 将第一行改为 `.claude/skills`。不要一次装两份后忘记以后要同步更新。

```powershell
$destination = ".agents/skills"
$names = @("wiki-context-reader", "wiki-review-intake", "wiki-approved-merge")
foreach ($name in $names) {
    if (Test-Path -LiteralPath "$destination/$name") { throw "目标已存在，请先比较：$name" }
}
New-Item -ItemType Directory -Force -Path $destination | Out-Null
foreach ($name in $names) {
    Copy-Item -LiteralPath "wiki_skills/$name" -Destination $destination -Recurse
}
```

### Hermes：官方安装器

以下三条在终端执行，主教程的文件读取方式仍可继续使用：

```bash
hermes skills install https://raw.githubusercontent.com/tsetwf-cloud/personal-wiki-starter/main/skills/wiki-context-reader/SKILL.md
hermes skills install https://raw.githubusercontent.com/tsetwf-cloud/personal-wiki-starter/main/skills/wiki-review-intake/SKILL.md
hermes skills install https://raw.githubusercontent.com/tsetwf-cloud/personal-wiki-starter/main/skills/wiki-approved-merge/SKILL.md
hermes skills list
```

按安装器提示检查，不用 `--force` 绕过。Skill 文本可共用，但三工具不会共享登录、模型配置、聊天历史、长期记忆或权限。全局安装可能影响其它项目，先使用主教程的局部文件读取路线。

## 项目规则不是三个同名入口

Hermes 与 Codex 支持 AGENTS.md；Claude Code 有 CLAUDE.md 等项目入口。本教程显式读取 AGENTS.md，所以不必生成或改写 CLAUDE.md，也不替读者修改全局指令。高级用户可在获授权后按 Claude Code 官方说明配置导入，但这不是本包完成条件。

## 官方机制参考

- Codex Skills：https://developers.openai.com/codex/skills
- Codex AGENTS.md：https://developers.openai.com/codex/guides/agents-md
- Claude Code Skills：https://code.claude.com/docs/en/skills
- Claude Code 项目记忆：https://code.claude.com/docs/en/memory
- Hermes Skills：https://hermes-agent.nousresearch.com/docs/user-guide/features/skills

规则和 Skill 是操作说明，不是系统隔离。候选批准也不等于授权任何终端命令：仍需查看当前权限提示和具体改动。
