# CLI 与数据契约

从包目录运行：`python3 -B scripts/wiki.py --root <Wiki绝对路径> <子命令>`。所有成功数据是 stdout JSON，错误是 stderr JSON 和非零退出码（argparse 参数错误除外）。`--help` 显示所有命令；不安装任何依赖。

| 命令 | 用途 |
|---|---|
| doctor | 不写 Wiki；解释器与所提供文件流程能力、未验证宿主、不支持实时渠道 |
| init | 仅空/不存在的无符号链接路径；六个一级空目录与 .wiki/state.json |
| inspect | 只读已有库兼容检查；必须六类齐全、无符号链接、无 .wiki |
| adopt --confirm-root PATH | exact absolute path 确认后只建 .wiki；不迁移正文 |
| configure --channels current,file --scope TEXT --model-permission none/local/remote | 显式完整配置；渠道可以只选 file 或 current；手动，不发网络 |
| ingest --file PATH --channel file/current --scope TEXT --date YYYY-MM-DD | 一次一个已授权文件，原始字节 hash 归档；不删除输入 |
| submit --file JSON | 接收 Agent 语义提取结果；程序验证并写候选，绝不正式合并 |
| decide --file JSON | exact ID 的部分批准/修改/拒绝/稍后；不提及的保留 pending |
| status | 全部状态、完整 IDs、恢复状态与 lock token；输出可能包含敏感候选，不发公共通道 |
| recover --token TOKEN | 用户确认原写进程已停止后的精确 token 前滚恢复 |
| context --query TEXT | 正式页子串匹配（忽略大小写），正文、完整页 hash 与核验来源元数据；空查询返回全部正式页 |
| check | 只查前五类正式 Markdown；来源完整性与简单本地 Markdown 链接，不扫描收件箱/备份 |

## 来源

来源 ID 是原始字节完整 SHA-256。档案在 `99-收件箱/原始资料/<sha256>.bin`；`.bin` 是固定存储后缀，不改变字节，原始文件名和日期保存在状态。相同字节即相同来源：不同渠道/文件名再次提交不会产生第二份来源，第二次事件范围不被合并进首次元数据。若需独立多渠道引用，未来需明确来源事件表，本版未做。

## 候选 JSON

```json
{
  "candidates": [{
    "source_id": "<ingest返回的完整source_id>",
    "claim_key": "reading-plan",
    "kind": "plan",
    "quote": "原文中确切出现的完整片段",
    "text": "计划每周阅读一次；执行时间待确认。",
    "target": "02-生活/阅读.md",
    "sensitive": false,
    "operation": "create",
    "expected_hash": null
  }]
}
```

字段必须恰好匹配示例。kind 可取 fact/judgment/plan/decision/conflict；sensitive 必须 JSON boolean。create 不得覆盖现有页；replace 的 text 是**完整替换正文**（不包含脚本生成的头部），expected_hash 为现有整个文件原字节的 SHA-256。旧页来源元数据会合并保留；标题/无关既有知识由 Agent 整合并让用户审核。

候选 ID 是 `[source_id,claim_key]` 确定性 hash，不是模型生成短码。相同 pending ID 且字段变更会报身份冲突；用户编辑通过审批的 text 字段执行。已解析 ID 不复活；同一来源精确 quote 被拒绝后换 claim_key 或目录仍返回拒绝项。不同 quote 的语义重复由 Agent 核对。使用足够窄的 quote 避免将互不相同的观点绑在同一个拒绝锚点上。

## 决策 JSON

```json
{
  "decisions": [{
    "id": "<submit返回的完整候选ID>",
    "action": "approve",
    "approve_structure": true,
    "text": "用户修改并批准的完整正文"
  }]
}
```

- 敏感项额外 `approve_sensitive: true`；旧页替换额外 `approve_replace: true`。必须逐项来自用户实际授权。
- 拒绝：`{"id":"完整ID","action":"reject","reason":"用户原因"}`。
- 稍后：`{"id":"完整ID","action":"later"}`；不改变 pending 状态。
- 一个决定数组先全量验证再事务写入；同一次两个批准指向同页会拒绝，须整合为一个用户审核的页面替换。
- 状态 JSON 是权威，Markdown review 是同步的可读记录。已 resolved review 暂不移动到另一个目录，避免路径含义变化；依状态判断，不以待审核目录文件数推导待审数量。

## 日志 / 恢复

`.wiki/events.jsonl` 记录实际动作与 exact IDs；`.wiki/backups/<事务token>/...` 保存被替换的原字节。journal 持有待写 payload，可能有敏感资料。中断后所有读正式页/写入都应停止，status 获取 token，由用户确认写进程已停止再 recover。若 old/new hash 都不匹配，保留锁，不强行覆盖。没有自动 stale-lock 清除。

测试专用 `WIKI_FAIL_AFTER=N` 在第 N 次事务文件写后以 86 中断；不要在真实运行设置。测试覆盖审批的四个写入边界和来源归档中断，不能冒称覆盖所有掉电/磁盘故障。
