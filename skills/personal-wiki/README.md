# Personal Wiki

把你指定的对话和文件，整理成一套**先审核、再入库、以后能继续查询**的个人 Wiki。正式知识、待审核内容和原始来源分开保存，文件都在你选择的本地目录里。

**安装后直接在 Agent 对话框输入固定入口，不需要先学习仓库里的脚本：**

```text
Codex：      $personal-wiki 帮我建立个人 Wiki
Claude Code：/personal-wiki 帮我建立个人 Wiki
Claude 插件：/personal-wiki:personal-wiki 帮我建立个人 Wiki
Hermes：     /skill personal-wiki 帮我建立个人 Wiki
```

你可以用它：

- 建立一套由自己审核的 Markdown 个人知识库。
- 整理指定对话或文件，先生成候选，不直接改正式知识。
- 只批准其中一部分，其余内容继续待审或拒绝。
- 在新会话中只查询已经批准的知识。

[三步开始使用](#三步开始使用) · [查看真实截图](docs/seven_steps/README.md) · [查看验证范围](docs/validation.md)

当前公开候选版本：`0.2.0-rc.2`。第一次请使用虚构或低敏感资料。

## 三步开始使用

### 第 1 步：安装

需要 Node.js 22.20+，以及能读取文件、创建文件并运行 Python 命令的 Agent。在**终端**运行下面的命令，把 `<agent>` 换成你使用的宿主：`codex`、`claude-code` 或 `hermes-agent`。

```bash
npx --yes skills@1.7.4 add https://github.com/tsetwf-cloud/personal-wiki-starter/tree/v0.2.0-rc.2/skills/personal-wiki \
  --agent <agent> \
  --skill personal-wiki --copy -g -y
```

例如，安装到 Codex：

```bash
npx --yes skills@1.7.4 add https://github.com/tsetwf-cloud/personal-wiki-starter/tree/v0.2.0-rc.2/skills/personal-wiki \
  --agent codex --skill personal-wiki --copy -g -y
```

安装后新开一个 Agent 会话。该命令会复制完整 Skill 包，不只是一个 `SKILL.md`。

### 第 2 步：在 Agent 对话框显式调用

根据宿主输入对应入口。下面是可以直接复制的第一次请求：

**Codex**

```text
$personal-wiki 帮我建立个人 Wiki。第一次只用虚构资料，不接聊天渠道，不设置定时任务。
```

**Claude Code（Skills CLI 安装）**

```text
/personal-wiki 帮我建立个人 Wiki。第一次只用虚构资料，不接聊天渠道，不设置定时任务。
```

**Claude Code 插件**

```text
/personal-wiki:personal-wiki 帮我建立个人 Wiki。第一次只用虚构资料，不接聊天渠道，不设置定时任务。
```

**Hermes**

```text
/skill personal-wiki 帮我建立个人 Wiki。第一次只用虚构资料，不接聊天渠道，不设置定时任务。
```

固定名称始终是 `personal-wiki`，前面的 `$`、`/` 或 `/skill` 由宿主决定。Claude 插件安装方法见[其他安装方式](#其他安装方式)。

### 第 3 步：按提示确认，再继续使用

Agent 会先让你确认 Wiki 保存位置、资料范围和模型处理许可。确认后，可以在同一个对话里继续说：

```text
以下是虚构人物林舟的资料：他希望 AI 先给结论，再解释理由，发现问题直接指出。他考虑每周整理学习笔记，但还没开始。请生成待审核候选，不要直接修改正式知识页。
```

看到候选后，只批准你确认过的内容：

```text
只批准“沟通偏好”这一项。学习笔记计划继续待审；不要合并其他内容。
```

以后新开会话时，再次用同一个显式入口调用 `personal-wiki`。它会只读取已经批准的正式知识；对尚未批准的计划，应回答“正式知识不足以确认”。

> **隐私提醒：** 文件保存在本地，不代表内容没有发送给远端模型。读取真实资料前，必须分别确认资料范围和模型处理许可。本项目不是加密库、权限沙箱或凭据保险箱。

按本 Skill 规程操作时，程序会限制处理范围、要求逐项审核，并让新会话默认只读正式知识；但拥有同等文件权限的 Agent 仍可能绕过脚本。

## 什么时候用

### 建立一套可审核的个人知识

**怎么说：**

> 帮我建立个人 Wiki。先用虚构资料走完候选、部分批准和新会话读取，不要直接导入真实聊天历史。

**你会得到：**独立目录中的 Markdown Wiki，以及正式知识、待审候选、来源和处理记录之间的清晰边界。

### 整理一段对话或指定文件

**怎么说：**

> 只整理〈明确对话片段或完整文件路径〉。本次范围是〈范围〉，允许／不允许交给〈模型〉处理。先生成候选，不要写正式页。

**你会得到：**原始字节归档和 SHA-256、事实／判断／计划等分类、原文依据、资料日期、拟保存路径和待审候选。

### 只批准一部分内容

**怎么说：**

> 批准〈完整候选 ID 和内容〉；〈另一项〉继续待审。不要批准未点名内容。

**你会得到：**只有明确批准的内容进入正式页，其他内容保持待审或拒绝状态；敏感内容、新路径和整页替换仍需分别确认。

### 在新会话中使用正式知识

**怎么说：**

> 从〈Wiki 完整路径〉读取与〈当前问题〉有关的正式知识。只依据正式页回答，不读取待审、拒绝、备份或原始资料，也不要修改文件。

**你会得到：**基于已批准知识的回答，以及对缺失、过期或冲突信息的明确说明。

### 情况变化时更新旧知识

**怎么说：**

> 这个情况已经变化。请比较现有正式页和这次资料，展示完整拟修改内容与差异，先让我审核，不要直接覆盖。

**你会得到：**旧知识与新资料的差异、待审核更新、批准后的备份、来源和动作日志。

## 其他安装方式

Claude Code 可以通过本仓库自带的插件清单安装。下面先在 Claude Code 中添加 Marketplace，再安装插件：

```text
/plugin marketplace add tsetwf-cloud/personal-wiki-starter
/plugin install personal-wiki@personal-wiki
```

插件安装后使用 `/personal-wiki:personal-wiki`。插件清单只注册当前 `personal-wiki` 主入口，不把仓库中保留的旧模板 Skill 暴露为并列入口。Marketplace 当前跟随仓库地址，不能作为 rc.2 的不可变安装来源；需要严格复现候选版本时，使用上面的 tag 路径或 Release 压缩包。

也可以下载 Release 压缩包并显式让 Agent 读取完整目录，作为不支持原生 Skill 安装时的备用方式；这种方式不等于宿主已注册快捷入口。

## 命令没有出现怎么办

1. 确认 Skill 安装到了**当前正在使用的宿主**，而不是另一款 Agent。上面的主命令使用全局范围；如果自行去掉 `-g`，则是项目级安装，需要从对应项目启动 Agent。
2. 新开会话或按宿主要求重启／刷新；安装前已经打开的会话可能没有重新扫描。
3. 查看宿主的 Skill 列表或选择器，以实际显示名称为准。Claude 插件使用带命名空间的 `/personal-wiki:personal-wiki`。
4. 区分“Skill 没被发现”和“Skill 已发现但脚本缺失”。后一种情况要重新安装完整包，不能只补一个 `SKILL.md`。
5. 仍无法使用时，运行 `python3 -B scripts/verify_skill_install.py --source <完整包路径>`。输出包含本机路径；对外分享前先删除用户名和目录结构。

## 已验证与使用范围

如果你只想开始使用，读到这里已经足够；下面是兼容性和测试边界。完整命令、测试结果和未验证范围见[验证记录](docs/validation.md)。

- **已实际调用：** Codex 0.163.0 已通过 Skills CLI 安装，并使用 `$personal-wiki` 显式加载 `0.2.0-rc.2`。
- **已验证安装：** 完整 Skill 包可以复制到 Codex、Claude Code 和 Hermes；安装副本测试和虚构 walkthrough 通过。
- **Claude Code：** 2.1.296 的插件清单严格校验和单一组件安装通过；当前环境未登录，因此没有执行模型会话中的 `/personal-wiki` 或 `/personal-wiki:personal-wiki`。
- **Hermes：** 0.22.2 的完整复制和本地 Skill 目录结构通过；隔离环境没有配置模型，因此没有执行 `/skill personal-wiki` 的模型会话。
- **尚未验证：** 原生 Windows、macOS、Python 3.10 最低 runtime、所有宿主版本、真实微信／Telegram 收消息、自动调度和远端通知。未验证不等于不支持。

Python 核心不依赖 Hermes、OAuth、API key 或联网服务。

## 账号、费用和隐私

Python 核心只使用标准库，本身不需要账号。理解资料、提取候选和回答问题由你使用的 Agent 模型完成，可能需要账号、订阅或 API 费用；远端模型可能接收资料。允许本地保存不等于允许发送给远端模型。

本包不提供微信或 Telegram 登录、独立实时客户端、消息发送或自动调度。拥有文件权限的用户或 Agent 可以绕过脚本；原文、日志和同盘备份可能包含明文敏感资料。不要导入密码、凭据或未获授权的他人资料。

## 详细资料

- [客户操作指南](USER_GUIDE.md)：建库、范围、渠道、审核和新会话使用。
- [七步真实操作](docs/seven_steps/README.md)：虚构样例截图及来源核验。
- [Agent 操作规程](SKILL.md)、[命令与数据格式](references/cli.md)。
- [渠道条件](references/channels.md)、[可选采集器](references/connectors.md)。
- [程序保证与非保证](references/boundaries.md)、[验证记录](docs/validation.md)。

仓库中的旧模板用户请看 [`legacy/README.md`](https://github.com/tsetwf-cloud/personal-wiki-starter/blob/main/legacy/README.md)。新版不自动迁移旧库，也不与旧脚本混用；独立候选压缩包不附带旧版归档。

原创：阿生（tsetwf-cloud），MIT。保留[仓库原有许可](LICENSE)与[新版程序版权声明](LICENSE.personal-wiki)。公开包不含生产个人 Wiki 正文、私人聊天、账号配置或凭据。
