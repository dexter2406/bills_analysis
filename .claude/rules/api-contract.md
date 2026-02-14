# API Contract Rules (v1 Frozen)

## Current Contract Baseline

- 当前对外 contract 版本：`v1`（Frozen）。
- 当前执行阶段：`M1`（并行开发期）。
- 前端默认对接：`src/bills_analysis/models/` 中 `v1` schema，不依赖临时脚本输出。
- 后端改动边界：M1 可重构内部实现，但不得改变 `v1` 对外字段、类型与语义。

## 契约优先规则

- 前后端统一以 `src/bills_analysis/models/` 为唯一 contract 来源。
- API 变更必须先更新 schema，再更新调用方。
- `v1` schema 冻结：禁止删除/重命名/改类型已发布字段。
- 如必须做 breaking change：先版本升级（如 `v1.1`/`v2`），并在 `SESSION_NOTES.md` 明确标注。

## 并行开发规则

- Frontend 默认仅对接 `v1` 冻结契约，不依赖临时脚本返回结构。
- Backend 在 M1 可重构内部实现，但不得改变 `v1` 对外字段与语义。
