# 不再每次向 AI 介绍自己：搭一个 Hermes、Codex、Claude Code 通用的个人 Wiki

聊工作、项目和生活时，总要重新介绍背景。我的做法是把长期有用的信息保存成自己的 Markdown 文件。AI 回答前按需读取；遇到变化，先提候选，等我确认后再更新。

这篇直接搭一个入门版。你只需要选择自己已有的 Hermes、Codex CLI 或 Claude Code，不必为了个人 Wiki 再换工具。文中的 Claude 指 Claude Code，不是普通网页聊天框。

**完成标准：换一个工具、开一个新会话，AI 仍能读取你批准的信息，不把未批准的计划或 AI 建议当成事实。**

配套仓库：https://github.com/tsetwf-cloud/personal-wiki-starter

模板、Skill 和练习资料可以公开分享。你自己的档案放在另一个私人目录，不上传到这个仓库。所有练习均为虚构；这不是全量聊天采集器，也不是全自动记忆产品。

## 一、只选一个你已经能用的工具

需要电脑、Python 3.10+、Git，以及一个能读写本地文件的 Agent。Hermes、Codex CLI、Claude Code 任选一个。模型使用可能收费；不要为了跟做同时开通三个付费服务。

已有可用工具就跳过安装。没有的读者按 [工具安装与可选 Skill 安装](agents.md) 选择一条路线，确认能正常回答后再继续。不要把 API 密钥写进 Wiki 或聊天。

操作系统也有区别：

- Linux、macOS、Windows WSL 使用本文的 Bash 命令。
- 原生 Windows 使用本文单列的 PowerShell 命令。先确认你选择的 Agent 支持当前 Windows 环境；Hermes 的本篇默认路线为 WSL。
- 本地实测环境是 WSL，不把命令写法适配等同于原生 Windows、macOS 的整套验收。详细结果见 [验证记录](verification.md)。

普通网页聊天如果没有获得本地文件访问能力，只能让你手动上传、下载与保存，不能直接按本文维护电脑里的文件夹。它可以使用同样的信息组织方法，但不是本文实测的本地工作流。

### 检查基础工具

Linux / macOS / WSL 终端：

```bash
python3 --version
git --version
```

Windows PowerShell：

```powershell
py -3 --version
git --version
```

Python 需要 3.10 或以上，脚本没有第三方依赖，不需要 pip。Windows 没有 `py` 但有正确版本的 `python`，把后面 `py -3` 换成 `python`。没有 Python 或 Git，先按 [Python 下载页](https://www.python.org/downloads/) 和 [Git 下载页](https://git-scm.com/downloads) 安装，重新打开终端验证。

WSL Ubuntu 缺少工具时，可执行下面的系统安装操作，企业电脑先遵守单位规定：

```bash
sudo apt update
sudo apt install python3 git
```

不要把 apt 命令发给 macOS 或原生 Windows，也不要关闭安全软件解决安装问题。

## 二、下载公共模板，建立私人目录

以下两组命令只选适合当前终端的一组，一次执行一行。

### Linux / macOS / WSL：Bash

```bash
cd ~
git clone https://github.com/tsetwf-cloud/personal-wiki-starter.git
cd personal-wiki-starter
python3 scripts/wiki_tool.py init --root "$HOME/my_personal_wiki"
python3 scripts/wiki_tool.py check --root "$HOME/my_personal_wiki"
```

### Windows：PowerShell

```powershell
Set-Location $HOME
git clone https://github.com/tsetwf-cloud/personal-wiki-starter.git
Set-Location personal-wiki-starter
py -3 scripts/wiki_tool.py init --root "$HOME/my_personal_wiki"
py -3 scripts/wiki_tool.py check --root "$HOME/my_personal_wiki"
```

成功时初始化与检查都返回 JSON，`ok` 为 `true`。这只是结构检查成功，不代表 AI 已读取过文件。

如果 clone 提示同名目录存在，先确认是不是之前下载的仓库。初始化拒绝非空目录是保护，不是故障。换一个新目录名，并同步修改后文路径；不要强行覆盖已有资料。

现在有两个互相独立的目录：

- `personal-wiki-starter`：公开教程、代码、空白模板。
- `my_personal_wiki`：你的私人知识库，位于前者之外，不推送到公开远端。

私人目录的主要结构：

```text
my_personal_wiki/
├── AGENTS.md
├── SCHEMA.md
├── index.md
├── log.md
├── 资料导入规范.md
├── wiki_skills/
│   ├── wiki-context-reader/SKILL.md
│   ├── wiki-review-intake/SKILL.md
│   └── wiki-approved-merge/SKILL.md
├── 00-基础信息/个人概况.md
├── 01-工作与项目/当前项目.md
├── 02-生活/时间安排与兴趣.md
└── 99-收件箱/
    ├── 待导入/
    ├── 待审核/
    ├── 原始资料/
    └── 处理记录/
```

`index.md` 是导航，主题页保存批准的信息，收件箱处理来源和候选，`log.md` 记录实际修改。`wiki_skills` 里只有公开操作说明，没有个人经历。

用普通文本编辑器、VS Code 或 Obsidian 打开私人目录都可以。Obsidian 不是必需组件。

已经建过旧版 Wiki 的读者不要重新 init。先备份，把新版 `templates/wiki/wiki_skills` 文件夹复制进旧私人库；如果已有同名目录，先比较自己的改动，不直接覆盖。原正式页与审核记录不需要重写。

## 三、不安装插件，先让 AI 读取同一份 Skill

主路线故意不依赖全局 Skill 安装。三个工具的自动发现目录不同，最稳妥的共同入口是：在提示词里给出精确路径，让它读取。

- 背景读取：`wiki_skills/wiki-context-reader/SKILL.md`。
- 候选提取：`wiki_skills/wiki-review-intake/SKILL.md`。
- 批准合并：`wiki_skills/wiki-approved-merge/SKILL.md`。

这些是操作说明，不是权限沙箱。每个工具使用自己的文件与终端能力，不要求它们都提供名为 `read_file` 的工具。

### 从私人目录启动工具

Bash：

```bash
cd "$HOME/my_personal_wiki"
```

PowerShell：

```powershell
Set-Location "$HOME/my_personal_wiki"
```

然后只输入你选的那一条：

```text
hermes
```

或：

```text
codex
```

或：

```text
claude
```

**`cd`、`python3`、`py -3` 在终端执行；下面的中文提示词发到 Agent 的聊天输入框。** 工具询问工作目录信任或文件操作权限时，先核对具体内容再批准，不关闭所有审批。

Hermes、Codex 可读取项目的 AGENTS.md；Claude Code 有自己的项目记忆入口。本文每次关键操作都显式要求读取 AGENTS.md，不依赖三者的自动加载机制一致，也不要求修改用户全局配置。熟悉后再按 [适配说明](agents.md) 选择原生 Skill 安装。

## 四、用虚构资料走完候选提取

在另一个终端窗口复制练习资料。先确认目标不存在同名文件；已经做过练习就查看已有记录，不覆盖再导一次。

Bash：

```bash
cp -n "$HOME/personal-wiki-starter/examples/first_source.txt" "$HOME/my_personal_wiki/99-收件箱/待导入/first_source.txt"
```

PowerShell：

```powershell
$source = "$HOME/personal-wiki-starter/examples/first_source.txt"
$target = "$HOME/my_personal_wiki/99-收件箱/待导入/first_source.txt"
if (Test-Path -LiteralPath $target) { throw "目标已存在，请先查看已有记录" }
Copy-Item -LiteralPath $source -Destination $target
```

回到任何一个 Agent，发送同一段提示词：

```text
当前工作目录就是我的私人 Wiki 根目录。
先读取 AGENTS.md，以及 wiki_skills/wiki-review-intake/SKILL.md，按规程操作。
本次仅处理 99-收件箱/待导入/first_source.txt。
这是公开虚构练习资料，允许发送给当前配置的模型处理。

先读规则与索引；提取候选，保留原文、真实 SHA-256 与完整拟落位路径。
原字节归档后核对哈希，候选来源改成真实归档路径。
不要修改任何正式主题页，不接入聊天、不创建定时任务。
使用你实际具备的文件和终端工具；没有权限先报告，不编造结果。
最后给我审核文件路径、候选摘要和批准语法。
```

预期结果，可对照 `examples/review_example.md`：

- C01：希望 AI 先读相关背景，并独立指出问题，拟放入个人概况。
- C02：计划尝试每周整理学习笔记，但尚未开始，通常拟放入生活页。模型也可能建议当前项目页，先核对该分类是否符合你的规则，不把示例落位当成固定输出。
- 不进入候选：暂停项目、专做短视频。这是 AI 建议，示例用户没有采纳。

编号可能随模型输出变化，审批前要读实际审核文件。示例不能替代真实执行记录。

资料写明日期为 2026-10-22，归档使用这个来源日期。你自己的文件应使用可靠资料日期；不知道就记录接收日期并注明，不能凭空补日期。

### 亲手检查三件事

打开审核文件，确认每项有原文、类型、来源、哈希与完整落位路径。打开三个正式页，确认练习内容还没有入库。核对原文与归档的 SHA-256 相同，不接受 AI 只说已经检查。

如需自己复算，将 AI 报告的实际归档相对路径替换进第二条命令。Bash 用 `python3`，Windows 用 `py -3`：

```bash
python3 -c "import hashlib,pathlib; print(hashlib.sha256(pathlib.Path.home().joinpath('personal-wiki-starter/examples/first_source.txt').read_bytes()).hexdigest())"
python3 -c "import hashlib,pathlib; print(hashlib.sha256(pathlib.Path('这里替换为实际归档相对路径').read_bytes()).hexdigest())"
```

**如果候选还没批准，正式页已经出现相应内容，就停下来。** 让 AI 对照备份撤回越权修改，没有备份就先检查具体差异，不能凭记忆覆盖旧资料。这次不算验收通过。

归档不等于入库。前者保存证据，后者需要你的决定。

## 五、只批准一项

确认实际编号后，在同一会话发送：

```text
先读取 AGENTS.md 和 wiki_skills/wiki-approved-merge/SKILL.md。
批准 first_source 的 C01；C02 保持待审核，不批准其它内容。
合并前保留受影响文件的本地可恢复版本，不推送远端。
只合并到候选声明的位置，更新真实来源、日期、索引及日志。
完成后报告已合并、拒绝、仍待审核的编号与实际目标文件。
```

核对：

1. `00-基础信息/个人概况.md` 出现批准的协作偏好，并带来源。
2. C02 仍待审核，正式生活页没有把计划写成既有习惯。
3. `log.md` 记录这次批准、编号与落位，备份位置可打开。
4. 原始资料没有改写，来源哈希不变。

如果实际编号不同，先改提示词，不照抄。拒绝应记录为拒绝，不删除原文。还有待审项的整份审核记录留在待审核区；全部解决后才移入处理记录。

健康、财务、家庭与第三方信息需要逐项批准。新增正式主题页也单独确认，不靠一句批准全部越过这些边界。

## 六、开新会话，也可以直接换工具

退出当前会话。从同一私人目录启动一个新会话，不用继续上一段聊天。想验证迁移，可以把原来的 `hermes` 换成 `codex` 或 `claude`，前提是另一工具已安装且可用。不要求装齐三个才能完成教程。

发送：

```text
当前目录是我的私人 Wiki。这些公开虚构练习文件允许由当前模型处理。
先读取 AGENTS.md 和 wiki_skills/wiki-context-reader/SKILL.md，按规程只读检索。
告诉我：我希望你怎样给我建议？我是否已经开始每周整理学习笔记？
列出实际读过的文件。只用规则、索引和相关正式页作答。
不读待审核、原始资料或聊天历史，不修改任何文件。
不知道就说不知道，不靠别的会话补齐。
```

合格结果：读出 C01 的协作偏好；对学习笔记回答正式资料不足以确认。没有批准的内容不因换工具就自动成为事实。

这一步依靠的是同一份文件，不是三个产品同步了聊天记忆、账号或配置。不同工具的回答措辞可以不同，事实边界必须相同。

## 七、练习通过，再整理你自己的资料

先从当前项目、实际时间限制、协作偏好开始，不从身份证、工资明细、家庭矛盾或整库聊天记录开始。

下面这段也适用于三个工具：

```text
我想建立自己的个人 Wiki，先做一次低敏访谈。
每次最多问两个问题，只问会影响当前项目或协作的信息，允许我跳过。
先问当前项目与实际时间约束，再问协作偏好。
不要索要真实姓名、身份证、精确住址、账号凭据或家庭成员隐私。

我说访谈结束后，只将我本人提供的信息整理成待导入来源。
写入前让我确认这些内容允许由当前模型继续处理。
再读取 wiki_skills/wiki-review-intake/SKILL.md 生成候选，等我审核。
不要直接合并；你自己的建议不能当成我的决定。
```

也可以自己写一页 `.md` 或 `.txt`，放入待导入，再指定精确路径处理。一个来源围绕一个主题，少量开始。

涉及阶段变化，要保留时间和范围。例如这两个月周末没有固定学习时间，不能永久改写成从不学习。冲突先分清是时间变化还是口径矛盾。

## 八、日常怎么用

带背景提问：

```text
先读 AGENTS.md 和 wiki_skills/wiki-context-reader/SKILL.md。
读取正式的当前项目和时间安排，结合已批准的限制，帮我安排本周任务。
列出实际读过的页面。缺少影响安排的信息再问。
这次只给建议，不写 Wiki，不创建或发送日程。
```

更新背景：指定来源，生成候选，查看内容、类型与落位，再逐项审批。起步阶段手动触发，一次一份资料。

自动采集聊天是另一项工程，要处理会话白名单、消息标识、游标、去重、并发锁和失败恢复。本包不附带生产采集器、不自动每天更新，也不因换成其他 Agent 就获得采集账户的授权。

## 九、备份与隐私

真实资料放在公开仓库外，`.gitignore` 不能替代权限和人工检查。第一次处理自己的资料前先做本地备份；采用云盘或私有 Git 远端前确认允许相应服务保存这些内容，私有仓库不等于端到端加密。

换电脑时复制整个私人目录，包括规则、Skill、来源、审核与日志，再安装所选 Agent，指定新路径并重做第六步。不要只搬正式页，否则来源链会断。

本地文件、开源 Agent、离线模型是不同的事。调用云模型时，读取的正文仍可能发给当前提供方；换工具也可能换了提供方。先确认允许处理，再读取真实资料，不能先上传后加一个仅限本地标记。

个人 Wiki 会过时，也会漏信息。背景充分不保证职业、投资或健康建议正确，最终决定仍由你判断。

## 十、卡住时怎么处理

- 找不到 Python：先完成基础工具验证。Windows 检查 `py -3` 或 `python`，Bash 检查 `python3`。
- init 拒绝非空目录：换新路径，不关闭保护。
- AI 说没有安装 Skill：直接要求读取私人库里 `wiki_skills/对应名称/SKILL.md`。读文件不等于完成原生安装。
- Claude Code 没自动读 AGENTS.md：显式要求读取。无需为了跟做修改全局配置。
- 文件只读或没有写权限：先核对工作目录与具体权限提示，不用关闭全部审批解决。
- 换会话不知道 Wiki 在哪里：从私人根目录启动，或给出实际绝对路径。Windows 和 WSL 的路径不能混用。
- 只有候选没改正式页：这是默认流程，检查后明确批准。
- AI 提前合并：暂停，核对备份与具体差异，本轮不算通过。
- `check` 成功但回答错误：它只查结构与支持范围内的相对链接，不验证事实、隐私完整性或模型判断。
- 下载旧版本没有 wiki_skills：按第二节的旧版迁移说明复制公开规程，不重新初始化旧库。

## 最后验收

- 初始化成功，重复初始化不会覆盖资料。
- 虚构资料形成候选，正式页不变。
- 只批准 C01 后，只有 C01 入库，C02 继续待审。
- 新会话能实际读取正式页，不把计划或 AI 建议说成既成事实。
- 原件哈希相同，来源、日志与备份可以打开。
- 私人资料不在公开仓库，清楚本次数据将交给哪家模型服务。

先让它准确读出一件你批准的事，再增加真实资料。不需要先装齐所有工具，也不需要一开始就导入全部人生。

---

版本与参考：2026-10-22 跨工具版。安装、发现目录与权限机制以各产品官方文档和本机 `--help` 为准。见 [工具适配与官方链接](agents.md)、[实际验证范围](verification.md)。
