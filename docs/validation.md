# 验证记录

## 0.2.0-rc.2：安装发现与显式调用层

本候选在 0.2.0-rc.1 的业务核心上增加标准 Skill 安装和宿主入口。各层必须分开理解：

- **发现与复制：** Skills CLI 1.7.4 从白名单生成的 `skills/personal-wiki` 发现一个主 Skill，并在隔离 HOME／项目中把完整包复制到 Codex、Claude Code 和 Hermes 的 Skill 目录；安装副本按 `distribution-manifest.json` 核对全部文件和 SHA-256。
- **安装副本运行：** 从隔离安装副本运行完整 Python 测试和虚构 walkthrough，不借用源码工作树。
- **Claude 插件：** Claude Code 2.1.296 对 `.claude-plugin` 清单做严格校验，并在隔离配置目录完成本地 Marketplace 安装。插件清单只指向 `skills/personal-wiki`，入口为 `/personal-wiki:personal-wiki`。当前环境未登录，未执行模型会话调用。
- **Codex 显式调用：** Codex 0.163.0 在隔离 HOME 中完成 Skills CLI 全局复制，并实际使用 `$personal-wiki` 加载根 `SKILL.md`，回报名称 `personal-wiki` 与版本 `0.2.0-rc.2`。`agents/openai.yaml` 关闭 Codex 的隐式调用；此设置不影响 Claude Code 或 Hermes。
- **Claude 调用限制：** 当前 Claude Code 环境未登录，因此未执行模型会话中的 `/personal-wiki` 或 `/personal-wiki:personal-wiki`；本轮只证明 Skills CLI 完整复制、清单严格校验、插件安装及单一 `personal-wiki` 组件被发现。
- **Hermes 调用限制：** Hermes 0.22.2 已验证 Skills CLI 完整复制和本地 Skill 目录结构；隔离 HOME 未配置模型，因此未执行 `/skill personal-wiki` 的模型会话。Hermes Hub 当前索引仍指向 rc.1 仓库根，并因历史教程中的安装命令触发安全扫描而阻止安装，故 rc.2 不以 Hub 根标识作为推荐路线。
- **业务证据：** 既有 Codex 0.163.0 七步截图仍用于说明建库、范围确认、部分审核和独立新会话只读正式知识；它不单独证明 rc.2 的安装器路径。安装验证和业务截图是两类证据。

公开发布后还需从最终 Release 附件重新下载、核对 SHA-256，并重复安装副本测试；本节的本地验证不能替代公开附件回读。最终附件哈希记录在 Release 正文，避免把压缩包自身哈希写入包内文档造成自引用。

本地 rc.2 仓库在 WSL/Linux、Python 3.14.7 下执行 `python3 -B -m unittest discover -s tests -v`，共 68 项；实际结果以本次最终运行记录为准。白名单分发包由 `distribution-files.json` 生成，安装目录包含 32 个文件（含生成的 `distribution-manifest.json`），每个源文件都有 SHA-256。最终公开附件的哈希在上传后写入 Release 正文，不能沿用本地重建过程中的中间值。

本页区分历史安装包测试、已完成的真实 Agent 演示、`0.2.0-rc.1` 核心候选与 `0.2.0-rc.2` 安装调用候选的验证。版本、环境和包哈希属于验证范围，不能将旧结果沿用为新包通过。本文列明证据能说明什么，不以测试数量代替兼容性结论。

## 1. 历史已测包：0.1.0

以下为已有历史验收记录，不是本次文档修改重新执行的结果：

| 项目 | 已有记录 |
|---|---|
| 包版本 | `0.1.0` ZIP |
| ZIP SHA-256 | `8cf8b13b9f2d4d86ba09968fd08e770ca0876c9c1f30654ca13cd17a07bd20b0` |
| WSL/Linux，Python 3.14 | 46 项通过 |
| 离线 Debian 12 虚拟机，Python 3.11.2 | 46 项通过 |

这些结果只归属于上述哈希的历史 ZIP。它们不证明 `0.2.0-rc.1` 的测试、打包、分发或兼容性已经通过；Python 核心能离线运行，也不代表模型语义处理离线。

## 2. 已完成：真实 Codex 七步操作

操作界面为 **Codex 0.163.0**，位于宿主；本地文件和命令实际在隔离 Debian 虚拟机内运行，语义提取使用现有远端模型服务。没有用预写候选替代这次真实模型提取，资料和人物均为虚构。

- 第 1–6 步来自同一真实会话：从提供的安装包路径检查、解压并读取根 `SKILL.md`，建立空白 Wiki，解释渠道条件，确认手动范围和模型许可，提取虚构偏好与计划，完成部分批准。
- 第 7 步另开独立会话，使用同一份 Wiki。实际调用 `context`，只读取正式知识及必要的 Skill 说明，没有读取来源正文或待审正文，也没有写入 Wiki。
- 核验结果：新会话前后 **15 个 Wiki 文件哈希不变**；**1 项 approved、1 项 pending**；待审计划对应的正式页不存在；归档来源哈希一致。
- 截图 1–6 是实际会话录屏的原始抽帧；第 7 张是独立新会话截图。演示不要求观看视频，也不发布原始会话录屏。

公开材料：

- [七步过程与截图](seven_steps/README.md)
- [截图来源与 SHA-256 清单](seven_steps/sources.json)
- [文件与状态核验摘要](seven_steps/verification.json)

**证据范围：**这次演示证明了所述 Codex 界面、虚拟机工具和远端模型组合下的本地读取使用流程；不证明原生 Windows 文件／命令执行，不证明 Skill 全局注册或宿主原生发现。安装使用的是已提供的包路径，不是从 GitHub 下载 `0.2.0-rc.1` 新包的分发验证，也不能代替新包回归测试。过程中曾缺少 `rg`，Agent 改用其他方式继续；不以截图隐藏工具环境差异。

## 3. 0.2.0-rc.1 本次本地验证

- WSL/Linux 的仓库整合副本运行 `python3 -B -m unittest discover -s tests -v`：62 项通过，包含新版及保留的旧版测试。
- 本次构建的候选压缩包在新目录解压后运行相同命令：46 项新版测试通过。另运行 `python3 examples/walkthrough.py --output <独立输出目录>`，虚构资料的归档去重、审核后检索和检查通过；该脚本不调用模型。
- 对候选包文本检查了常见凭据模式，逐张审看了七张截图；这不能保证自动扫描发现所有敏感内容。
- 以上是本地结果，不代表本版在其他宿主或操作系统通过。提交 `813f461baf138513a79989e10c599289a1b0c151` 的 GitHub Actions（Python 3.12）已通过新版与保留测试及旧模板检查；候选压缩包的公开下载仍须按最终 Release 附件回读结果确认。

## 4. 尚未验证的范围

- 宿主全局 Skill 注册、原生发现，以及 Claude Code 对本次新包的安装和完整使用流程。
- 上述记录之外的操作系统／运行环境，包含原生 Windows、macOS；设计最低 Python 3.10 的实际 runtime 尚未验证。
- 真实微信或 Telegram 消息接收后进入本地采集的端到端链路。随包适配和合成数据测试不等于真实平台接入；渠道已有登录或网关也不是 Wiki 已获读取授权。
- 调度、后台运行、远端通知及用户实际收取消息。
- 升级、旧库格式迁移、卸载的完整操作流程。
- “临时 AI 在 20 分钟内从零复现同等可靠性”的对照实验。尚无冻结验收条件、隔离基线和独立评审后的比较结果。

未验证不自动等于不支持，但不得写成已兼容或已通过。更多实现约束见 [程序保证与非保证](../references/boundaries.md)。旧模板与资料见仓库中的 [`legacy/README.md`](https://github.com/tsetwf-cloud/personal-wiki-starter/blob/main/legacy/README.md)，不能与新脚本混用，也没有自动迁移承诺；独立候选压缩包不附带旧版归档。
