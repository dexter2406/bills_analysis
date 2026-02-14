# Session Handoff (SESSION_NOTES.md)

`SESSION_NOTES.md` 是**当前状态对齐文件**（近期过去 + 近期未来），不是审计日志。已彻底解决的信息应被清理，保持文件精简。

采用 fenced JSON 记录多 Agent 交接（每条记录一个 ` ```json ... ``` ` 代码块）。

## 字段规范

- 必填字段：`id`, `ts`, `status`, `scope`, `who`, `what`, `next`
- 可选字段：`dep`, `risk`
- 状态规则：`status` 允许 `OPEN` / `CLOSED`
  - `OPEN`：仍待跟进或存在阻塞
  - `CLOSED`：已完成且无后续阻塞
- `who` 必须包含：`agent`, `side`, `branch`, `head`
- `what` 用数组记录变更事实与动机（what + why），用中文做解释，技术上可以用英语
- `dep` 只在依赖对方时填写；出现 `dep` 代表需要跨 Agent 跟进，用中文做解释，技术上可以用英语
- `next` 必须包含：`goal`, `owner`，用中文做解释，技术上可以用英语

## 写入命令

```bash
python scripts/session_notes.py log \
  --scope "<scope>" --agent <agent> --side <frontend|backend> \
  --what "<what>" --why "<why>" \
  --next-goal "<next-goal>" --next-owner "<owner>"
```

- 可重复参数：`--what`、`--dep`、`--risk`
- `id` 默认自动递增（如 `C-001`），可选 `--id` 手工指定

## 辅助命令

- `python scripts/session_notes.py summary`：输出记录数、文件大小、各记录摘要（含 dep/risk 标注）。
- `python scripts/session_notes.py rewrite --records-json '<json array>'`：用 Agent 决定的记录列表原子重写文件，自动更新 ID 水位线。

## 压缩策略

- 记录数 > 10 条时建议执行 `/session-notes-compact`（语义压缩 Skill）。
- 压缩由 Agent 语义判断：保留仍有决策价值的记录，合并同链路递进记录，删除已解决的记录。
- ID 水位线 `<!-- max_id: C-NNN -->` 确保压缩后新 ID 不复用。
- 里程碑切换时强烈建议全量压缩。

## 参考记录

```json
{
  "id": "C-001",
  "ts": "2026-02-13T16:20:00+01:00",
  "status": "OPEN",
  "scope": "upload-review chain",
  "who": {"agent":"agent-a","side":"frontend","branch":"feat-frontend","head":"28997aa"},
  "what": ["打通了 Upload->Review->Submit 的工作流","why:按M1的开发计划"],
  "dep": ["backend: POST /v1/batches/{id}/review-rows accepts {row_id,result:{...}}"],
  "risk": ["仅为 mock API; 实际 real API 还未验证"],
  "next": {"goal":"替换为实际API，并执行some test","owner":"agent-a"}
}
```
