# Definition of Done & Safety Guardrails

## Definition of Done

每个任务完成需满足：

- Contract consistency verified（schema + tests）。
- 功能可运行（按最小命令验证）。
- 有日志和错误提示（可观测）。
- 不破坏既有脚本主流程。
- 新加的 class、function 等有 docstring 或者 comment。
- 如果 API model 更新，contract 测试需要 pass。
- 说明类的文档按需更新（至少 `SESSION_NOTES.md` 要按照 session-handoff 规则判断）。

## Safety Guardrails

- 禁止跨边界改动（遵循 `collaboration-boundaries.md`）。
- `.env` 不入库，示例配置放 `.env.example`。
- 阈值与业务参数统一走 `tests/config.json`（后续迁移到 `config/`）。
- 所有 merge 写入需保留审计日志（操作者、时间、目标表、变更摘要）。
