# 旧版模板教程

旧版模板、脚本与三个 Skill 的原有仓库路径仍保留，供已有链接使用；`legacy/` 提供一份独立归档。新用户请从[最新入口](../README.md)开始。

- [旧版实操教程](docs/tutorial.md)
- [旧版设计](docs/design.md)
- [历史验证记录](docs/verification.md)：仅对应旧版，不代表新版全部通过。
- 新用户请从[最新入口](../README.md)开始。

## 已有用户

新版采用根目录 `SKILL.md` 与 `scripts/wiki.py`，有不同的分类、状态与审核格式。**不要把新版脚本直接指向旧练习库，也不要用 init 覆盖升级。** 本次不自动搬动、迁移或删除任何私人资料。需要迁移时先另建新库和外部备份，再逐项审核，当前没有自动迁移命令。

## 复验旧模板

在本目录（`legacy/`）运行，使用已有可写临时目录作为 TMPDIR：

```bash
python3 -B -m unittest discover -s tests -v
python3 scripts/wiki_tool.py check --root templates/wiki
```

旧教程中的仓库根路径与公开 raw URL描述属于历史上下文；需要本地查看时从本目录寻找 `scripts/`、`templates/`、`skills/`。本目录不是新版安装路线，也不宣称历史链接已经随归档更新。
