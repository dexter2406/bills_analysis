# CLAUDE.md

## 1. Project Context

- 项目目标：面向餐馆内部，完成 `daily/office` 两种场景的票据的上传、提取、人工校验、归档预览与最终 merge 入账闭环。
- 当前阶段：`M1`（并行开发）：Backend 迁移已验证流程到分层架构，Frontend 基于冻结契约推进上传与状态链路。
- 当前 API Contract： `v1`（Frozen，当前唯一对接基线）。

技术栈：

- 前端：Azure Static Web Apps（计划），使用JavaScript语言编写
- 后端：FastAPI + Python（Azure Functions / Queue 模式计划）
- 文档识别：Azure Document Intelligence（office 还使用 Azure OpenAI 做语义补充）

## 2. Current Pipeline & Verified Scripts

Canonical reference pipeline（legacy-verified）：

- `tests/run_with_category.py`
- `src/bills_analysis/extract_by_azure_api.py`
- `src/bills_analysis/excel_ops.py`

Legacy/auxiliary wrappers（按需参考，不作为新功能主入口）：

- 其余 `tests/*.py` 脚本（如 JSON->Excel、merge、report、cleanup）属于历史验证与辅助脚本。

## 3. Architecture Targets

目标目录与职责：

- `src/bills_analysis/api/`：FastAPI routes（HTTP 输入输出）。
- `src/bills_analysis/services/`：业务编排（process/review/merge）。
- `src/bills_analysis/integrations/`：外部适配（azure/excel/storage/queue/repo）。
- `src/bills_analysis/models/`：schema/contract（API、任务、结果模型）。
- `src/bills_analysis/workers/`：异步任务处理（queue consumer）。
- `frontend/`：前端工程（SWA 部署）。

These boundaries are architectural contracts and must not be blurred.

里程碑方向：

- M1：后端迁移 tests 已验证逻辑到 `services/integrations`；前端基于冻结 `v1` contract 开发调用链路。
- M2：稳定开放 API（create batch / query status / submit review / merge）并完成联调。
- M3：完成上传-校验-确认-下载闭环，merge 结果页对齐。

Milestone Status（当前 + 整体）：

- As of `2026-02-13`：项目处于 `M1` 并行开发阶段（Backend 迁移 + Frontend 对接冻结契约）。
- Backend 当前状态：核心流程已在 `tests/` 验证，正在下沉到 `src/bills_analysis/services/` 与 `src/bills_analysis/integrations/`。
- Frontend 当前状态：已按 `v1` 契约推进上传与状态流转页面，联调以 `v1` 字段语义为准。
- 整体进度判断：`M1` 进行中，`M2/M3` 尚未进入冻结验收阶段。

## 4. Collaboration Boundaries

前后端严格隔离，禁止互改。详见 `.claude/rules/collaboration-boundaries.md`。

核心要点：Frontend 仅改 `frontend/**`，Backend 仅改 `src/bills_analysis/**`。Commit 前缀 `frontend: ...` / `backend: ...`，不混合。

## 5. API Contract Rules (v1 Frozen)

`v1` schema 冻结，禁止 breaking change。详见 `.claude/rules/api-contract.md`。

核心要点：以 `src/bills_analysis/models/` 为唯一 contract 来源，变更必须先更新 schema 再更新调用方。

## 6. Session Handoff

`SESSION_NOTES.md` 是当前状态对齐文件（非审计日志）。详见 `.claude/rules/session-handoff.md`。

核心要点：fenced JSON 记录，> 10 条时建议 `/session-notes-compact` 语义压缩。写入命令 `python scripts/session_notes.py log ...`。

## 7. Commands You Should Prefer

- 启动 API：`uv run invoice-web-api`
- Contract 测试：`uv run pytest tests/test_api_schema_v1.py -q`
- 导出 OpenAPI v1：`uv run python scripts/export_openapi_v1.py`
- Frontend 开发：`pnpm dev` / `pnpm test`

## 8. Definition of Done & Safety

详见 `.claude/rules/dod-and-safety.md`。

核心要点：contract 一致性验证、功能可运行、可观测、不破坏既有流程、新代码有注释、文档按需更新。

## 9. Maintenance of This File

本文件是仓库级主协作规范。稳定规则已拆分到 `.claude/rules/*.md`：

- `.claude/rules/collaboration-boundaries.md` — 前后端边界与提交约定
- `.claude/rules/api-contract.md` — v1 冻结策略与契约优先规则
- `.claude/rules/session-handoff.md` — SESSION_NOTES 字段规范、命令与压缩策略
- `.claude/rules/dod-and-safety.md` — 完成标准与安全约束

触发更新条件：

- API contract 变化（含版本升级）。
- 目录边界与职责变化。
- 标准启动/验证命令变化。
- DoD 或安全规范变化。

更新责任：发起变更的 session 负责同步更新本文件、rules 文件与 `SESSION_NOTES.md`。

冲突处理：若 rules 文件与本文件冲突，以本文件为准。
