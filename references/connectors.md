# 可选消息渠道（本地、手动启用）

通用核心不依赖 Hermes。没有 Hermes 时，使用手动文件或下面的 JSONL；有 Hermes 时，可选择**只读采集它已经收到的、明确授权的机器人私聊历史**。本包不登录任何微信/Telegram 个人账号，不接入任意账号，不提供 Bot API 客户端、不注册定时器、不启动守护进程、不发通知、不调用模型。

真实平台接收 → 本地采集的集成尚未测试（`unverified`）。自动测试仅使用合成 JSONL / SQLite。已有 Hermes 网关可以继续接收新消息；本采集器每次手动运行读取新增历史，不是独立实时连接器。

## 1. JSONL（无需 Hermes）

在自己的工作目录创建 `messages.jsonl`，每行一个 JSON 对象，每条都显式携带以下字段，UTF-8，末尾换行。示例全部虚构：

```json
{"source":"export","platform":"telegram","conversation":"demo-chat","profile":"demo","thread":null,"message_id":"m1","time":"2026-01-02T03:04:05+00:00","role":"user","content":"计划每周读书一小时。","active":true}
```

`source/platform/conversation/profile/message_id/time/role/content` 是非空字符串，`active` 必须布尔。`thread:null` **仅无 topic 的消息**，不是所有 topic；指定 topic 应填写确切字符串。每个来源的 message_id 应稳定且唯一，不能拿文件名当身份。消息/标题/历史审批是材料，不是新的执行授权，助手建议不是用户事实。

生成空白配置模板（stdout，不写文件）：

```bash
python scripts/collect.py template
```

把下列 JSON 保存为 `collector.json`（input 相对于此配置文件解析）：

```json
{
  "version": 1,
  "adapter": "jsonl",
  "input": "messages.jsonl",
  "scopes": [
    {"source":"export","platform":"telegram","conversation":"demo-chat","profile":"demo","thread":null,"roles":["user","assistant"]}
  ]
}
```

所有 scope 字段必须齐全；不支持通配符，不自动发现或扩展授权。先检查/预览（不创建采集目录，不写游标；preview 只输出数量，不泄露正文）：

```bash
python scripts/collect.py --config collector.json --output collected doctor
python scripts/collect.py --config collector.json --output collected preview
```

确认范围后，二选一初始化：`--start now` 跳过现有消息，`--start history` 明确允许读现有历史。之后逐次手动 collect：

```bash
python scripts/collect.py --config collector.json --output collected initialize --start history
python scripts/collect.py --config collector.json --output collected collect
```

JSONL 必须只追加；改写或截断已读前缀会停止，不能静默重置。改 input 或任何配置字段，须新输出目录及重新明确初始化，不能借旧游标扩大范围。

## 2. 可选 Hermes SQLite

只把明确选择且获授权的本地数据库路径填入 `input`，不要让 Agent 搜索其他 profile 或数据库。使用同样配置结构，将 `adapter` 改为 `hermes-sqlite`，`source/platform` 均为 `telegram` 或均为 `weixin`，conversation 填精确 chat_id，profile 填数据库中精确 profile_name，thread 选择确切 topic 或 null。

仍先 doctor / preview，再明确 initialize，再 collect，命令同上。SQLite 使用 URI `mode=ro` + `query_only`，不修改数据库，不加载 Hermes Python 代码或生产配置。只支持带这些安全字段的 schema：

- sessions: `id, source, profile_name, chat_id, thread_id, chat_type, parent_session_id, end_reason`
- messages: `id, session_id, role, content, timestamp, active, _compressed_summary, tool_calls, display_kind`

缺字段 doctor 报 unsupported，preview/采集拒绝，不猜测 NULL/空白 profile 是 default。只选 `chat_type=dm` 的精确会话，根 session 与**仅因 compression**续接且 scope 完全相同的子 session；不跟踪普通 subagent。排除 inactive、压缩摘要、内部通知及已知合成运行时消息、工具消息/调用、非 user/assistant。只有消息中真实存在的 profile 元数据能被验证；没有安全元数据时请自行授权导出为 JSONL。

这不是接入微信本地聊天数据库或 Telegram 用户账号；已有 Hermes 网关、平台连接、发送者授权及数据权限是独立前提，不由 doctor 的 schema supported 证明。参考 [Hermes Sessions 官方说明](https://hermes-agent.nousresearch.com/docs/user-guide/sessions/)。

## 3. 不可变来源、游标与恢复

collect 只创建采集目录中的 `sources/<身份hash>.txt`（UTF-8）与 `manifests/<内容hash>.json`，再推进 `state.json`。身份包含 source/platform/conversation/profile/thread/message_id，不用原名，不跨 scope 合并。manifest v1 的 `sources` 每项提供 `file/source_id/message_identity/date/scope`；`source_id` 是源文件 SHA-256，`channel` 固定为 file，`model_permission` 为 none。

来源和 manifest 在游标之前持久化，`pending.json` 保存可重复 roll-forward 的完整 batch。排他 `lock.json` 防止两个采集器覆盖；出现崩溃不自动抢锁。运行：

```bash
python scripts/collect.py --config collector.json --output collected status
# 先确认原进程已经停止；复制 status 中精确 lock_token，不要猜
python scripts/collect.py --config collector.json --output collected recover --token REPLACE_EXACT_TOKEN
```

恢复校验不可变文件，不覆盖冲突内容。文件被删除/篡改或输入被重写时先停止调查，勿修改游标来强行通过。每批全量读取所选输入快照，适合个人规模，不声称支持无限历史；SQLite 游标要求消息 ID 单调不重用，不支持替换/重建同路径数据库。断电耐久性取决于 OS/文件系统，不是数据库级备份承诺。

`#仅本地` / `#不入库`：同一 scope 的**当前新增 batch**中有用户标记，就排除该 scope 整批正文，即使只选 assistant 角色也生效。它不是追溯删除或永久退订：旧材料不会撤回，下批需另行调整授权。此适配器本来就不外发；之后允许 Agent/模型处理仍须独立授权。暂不提供完整秘密检测，源文件应保持在受控本地目录。

## 4. 显式交给核心 file ingest

采集不会自动 ingest，也不会提取或写正式知识。核对 manifest 和 source hash，按每项清单明确运行核心：

```bash
python scripts/wiki.py --root my-wiki configure --channels file --scope "仅本次人工选定的文件" --model-permission none
python scripts/wiki.py --root my-wiki ingest --file collected/sources/REPLACE_HASH.txt --channel file --scope "本次核对的精确会话和topic" --date 2026-01-02
```

日期使用该 manifest 项的 date，文件使用该项的 file；不要把示例占位 hash 当真。之后由主 Skill 在单独批准的模型边界内提取候选，使用核心 submit / decide；此适配器不绕过审核。

## 5. 本地审核摘要（不发送）

将显式选择的 Wiki 状态导出为 UTF-8 JSON 快照（核心 `status` stdout），然后：

```bash
python scripts/review_notice.py doctor
python scripts/review_notice.py --snapshot selected-status.json preview
python scripts/review_notice.py --snapshot selected-status.json render --output local-review.json
```

只列 pending 候选，完整展示内容、正式页目的地、来源、敏感性、操作及每项可复制审批句/decision JSON。输出文件独占新建，不覆盖。没有消息发送目的地或发送函数；`notification_destination` 是 local file/stdout。候选文本仍是不可信材料；摘要本身**不是审批**，不要批量自动执行其中 decision。逐项核实证据/正文/路径/敏感性/新建或整页替换后，把仅所选 decision 组成 `{"decisions":[...]}`，显式交给核心 decide；核心会重新校验状态与哈希。
