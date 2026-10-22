# Personal Wiki Starter

Hermes、Codex CLI、Claude Code 通用的个人 Wiki 教学包。用自己的 Markdown 保存背景，AI 按需读取、先提候选、本人批准后再更新。

作者：阿生。所有模板与练习均重新编写，不含私人档案。**从 [完整实操教程](docs/tutorial.md) 开始。**

## 选一个工具就能跟做

不用为了本教程安装 Hermes，也不用装齐三款工具。已有 Codex CLI 或 Claude Code 就直接使用；本文的 Claude 指 Claude Code，不是普通网页聊天框。

- 同一套正式页面、来源与审核规则。
- 三份通用 Skill，初始化后在私人库内直接读取，无需先全局安装。
- Bash 与 Windows PowerShell 分别给出命令，不混用终端。
- [工具安装与可选原生 Skill 安装](docs/agents.md)。

支持设计不等于所有环境都实测：本地 AI 工作流验证环境为 WSL，实际结果与限制见 [验证记录](docs/verification.md)。

## 快速开始

前提：Python 3.10+、Git，以及一个可读写本地文件的 Agent。

Linux / macOS / WSL：

```bash
git clone https://github.com/tsetwf-cloud/personal-wiki-starter.git
cd personal-wiki-starter
python3 scripts/wiki_tool.py init --root "$HOME/my_personal_wiki"
python3 scripts/wiki_tool.py check --root "$HOME/my_personal_wiki"
cd "$HOME/my_personal_wiki"
```

Windows PowerShell：

```powershell
git clone https://github.com/tsetwf-cloud/personal-wiki-starter.git
Set-Location personal-wiki-starter
py -3 scripts/wiki_tool.py init --root "$HOME/my_personal_wiki"
py -3 scripts/wiki_tool.py check --root "$HOME/my_personal_wiki"
Set-Location "$HOME/my_personal_wiki"
```

成功返回 `ok: true`。init 拒绝非空目标，不能用来覆盖升级旧库。私人目录在公开仓库外。

输入 `hermes`、`codex` 或 `claude` 中的一条启动，再发：

```text
当前目录是我的私人 Wiki，先读取 AGENTS.md 与
wiki_skills/wiki-context-reader/SKILL.md。
只读索引与相关正式页，说明目前有什么已批准背景、缺少什么。
不读原始资料或待审核，不改文件。
```

空模板没有你的真实经历，正确结果应说明还没有批准的背景。按 [教程第四节](docs/tutorial.md) 用虚构来源练习导入、部分批准和新会话读取。

## 内容

- `templates/wiki/`：空白 Wiki 与三份局部操作规程。
- `skills/`：同源 Skill，可按各工具原生机制安装。
- `examples/`：虚构来源与候选示例，不是运行证据。
- `scripts/wiki_tool.py`：零第三方依赖的 init / check。
- [设计说明](docs/design.md)、[流程图](docs/workflow.html)、[验证范围](docs/verification.md)。

## 边界

归档不等于批准，AI 建议不等于用户决定。默认不采集聊天、不调度、不通知、不自动合并。没有作者生产系统的采集器、游标、锁或状态库。

本地文件不等于离线处理，云模型可能收到读取的正文；在读取真实资料前确认允许当前提供方处理。Skill 不是权限沙箱，`check` 不验证事实、隐私完整性或模型是否服从。

不要发布私人 Wiki。`.gitignore` 不是数据保护系统。

## 开发测试

测试夹具仅放在已存在、可写的 TMPDIR 中。Bash：

```bash
mkdir -p "$HOME/.cache/wiki_starter_tests"
export TMPDIR="$HOME/.cache/wiki_starter_tests"
python3 -B -m unittest discover -s tests -v
python3 scripts/wiki_tool.py check --root templates/wiki
```

跨工具副本由测试逐字节比较，修改源 `skills/` 后应同步 `templates/wiki/wiki_skills/`。当前工具链单测范围见验证记录，不把 WSL 测试当作全平台结果。

## 许可证

新编写的代码、模板和文档采用 [MIT](LICENSE)。各 Agent 为独立产品，按自身许可和服务条款使用。
