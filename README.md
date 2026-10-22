# Personal Wiki Starter

一份可以跟着做的个人 Wiki 入门包：用本地 Markdown 保存长期背景，让 AI 按需读取、先提候选、再由本人批准。

作者：阿生。基于实际使用中的个人 Wiki 方法，重新编写为不含私人数据的简化教学版。

**先读 [完整实操教程](docs/tutorial.md)。** 本仓库不是聊天导出器，也不是全自动记忆产品。

## 你能得到什么

- 空白的私人 Wiki 目录与审核规则。
- 三个可独立安装的 Skill：背景读取、候选提取、批准后合并。
- 虚构练习资料和预期候选，能逐步检查有没有越过审核。
- 零依赖 Python 初始化 / 只读结构检查工具。
- [流程图](docs/workflow.html)、[设计说明](docs/design.md)、[验证范围](docs/verification.md)。

## 快速开始

前提：已能使用 Hermes，终端有 Python 3.10+ 和 Git。主教程命令适用于 Linux/macOS/Windows WSL 的 Bash；实际执行验证环境为 WSL。

```bash
git clone https://github.com/tsetwf-cloud/personal-wiki-starter.git
cd personal-wiki-starter
python3 scripts/wiki_tool.py init --root "$HOME/my_personal_wiki"
python3 scripts/wiki_tool.py check --root "$HOME/my_personal_wiki"
```

初始化只允许新目录或空目录，拒绝覆盖非空目录。公开模板在当前仓库，私人文件在仓库外的 `~/my_personal_wiki`，不要混在一起。

## 安装 Skill

先检查源文件，理解其操作范围，再逐条运行：

```bash
hermes skills install https://raw.githubusercontent.com/tsetwf-cloud/personal-wiki-starter/main/skills/wiki-context-reader/SKILL.md
hermes skills install https://raw.githubusercontent.com/tsetwf-cloud/personal-wiki-starter/main/skills/wiki-review-intake/SKILL.md
hermes skills install https://raw.githubusercontent.com/tsetwf-cloud/personal-wiki-starter/main/skills/wiki-approved-merge/SKILL.md
hermes skills list
```

新会话从私人目录启动：

```bash
cd ~/my_personal_wiki
hermes
```

在聊天里明确要求使用对应 Skill。三个 Skill 的正文与模板不包含作者私人路径、账户标识或聊天内容。它们是操作指引，不是强制权限沙箱；请审核改动和备份。

## 核心流程

```text
指定来源 → 候选提取 → 原文归档与哈希核对 → 人工审批 → 正式主题页
                                         ↓                ↓
                                  未批准继续待审      来源、索引、日志
```

原文归档不是批准入库。AI 建议不是用户决定。健康、财务、家庭和第三方信息需要额外谨慎，不建议作为第一份练习资料。

## 安全与范围

开源 Agent、本地文件和离线模型是三件事。云模型会收到读取结果；不要先上传仅限本地资料再试图用标签撤回。默认不采集聊天、不调度、不发送通知、不自动合并，也不包含原系统的锁、游标与去重状态库。个人真实资料不得进入公开仓库。

`check` 只能检查实现支持的目录、文件和相对链接；不校验事实、隐私完整性或模型是否遵守批准边界。详见 [验证说明](docs/verification.md)。

## 测试

测试用例要求 `TMPDIR` 指向已存在、可写的临时目录，所有虚构夹具只在其中生成并清理。没有设置时，可先执行：

```bash
mkdir -p "$HOME/.cache/wiki_starter_tests"
export TMPDIR="$HOME/.cache/wiki_starter_tests"
python3 -m unittest discover -s tests -v
```

## 许可证

新编写的代码、模板与文档采用 [MIT](LICENSE)。Hermes 为独立项目，按其自身许可证使用。本仓库不分发作者私人资料或从第三方资料复制的内容。
