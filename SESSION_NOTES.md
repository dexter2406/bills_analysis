# SESSION_NOTES

半自动会话记录：`start` 自动记录会话开始，`end` 自动记录最近一次提交并附人工 next。

## [2026-02-08 22:44:51] START agent-b-m1-multipart
- branch: `feat-backend`
- head: `30ed1b6`
- worktree: `D:\CodeSpace\prj_rechnung\bills_analysis_backend`
- status: in_progress

## [2026-02-08 23:11:04] END agent-b-m1-multipart
- branch: `feat-backend`
- commit: `30ed1b6`
- summary: chore: secure deps
- changed_files: `uv.lock`
- next: 前端按multipart字段对齐：daily传zbon_file(单文件)+可选bar_files；office传office_files
- risk_or_note: 已切换FastAPI原生Form/File解析，依赖python-multipart；部署环境需确保该依赖存在
- status: done


## [2026-02-10 11:46:03] START agent-b-m1-downstream-migration
- branch: `feat-backend`
- head: `b0cff64`
- start_head: `b0cff64`
- worktree: `D:\CodeSpace\prj_rechnung\bills_analysis_backend`
- status: in_progress

## [2026-02-10 11:57:17] END agent-b-m1-downstream-migration
- branch: `feat-backend`
- commit: `b0cff64`
- summary: backend: add v1 multipart batch upload API and contracts
- uncommitted_files: `AGENTS.md`, `README.md`, `SESSION_NOTES.md`, `tests/cleanup_outputs.py`, `tests/json_to_excel_map.py`, `tests/json_to_excel_office.py`, `tests/merge_daily_excel.py`, `tests/merge_excel_entry.py`, `tests/merge_office_excel.py`, `tests/run_with_category.py`, `tests/vlm_pipeline_api.py`, `tests/vlm_pipeline_report.py`
- next: 可开始把薄封装入口逐步迁移到cli/并规划Excel/Merge API开放（M2）
- risk_or_note: pipeline严格等价依赖真实Azure与样例PDF，当前parity主要覆盖规则与结构，建议补充golden样例集
- status: done

## [2026-02-10 12:05:32] START agent-b-remove-default-prompt
- branch: `feat-backend`
- head: `b0cff64`
- start_head: `b0cff64`
- worktree: `D:\CodeSpace\prj_rechnung\bills_analysis_backend`
- status: in_progress

## [2026-02-10 12:06:27] END agent-b-remove-default-prompt
- branch: `feat-backend`
- commit: `b0cff64`
- summary: backend: add v1 multipart batch upload API and contracts
- uncommitted_files: `AGENTS.md`, `README.md`, `SESSION_NOTES.md`, `tests/cleanup_outputs.py`, `tests/json_to_excel_map.py`, `tests/json_to_excel_office.py`, `tests/merge_daily_excel.py`, `tests/merge_excel_entry.py`, `tests/merge_office_excel.py`, `tests/run_with_category.py`, `tests/vlm_pipeline_api.py`, `tests/vlm_pipeline_report.py`
- next: 继续清理tests薄封装中遗留未使用参数（如prompt/model）
- risk_or_note: 本次仅移除azure_pipeline_adapter中未使用DEFAULT_PROMPT与内部无效参数传递，外部行为不变
- status: done

## [2026-02-10 12:38:23] START agent-b-fix-azure-silent-failure
- branch: `feat-backend`
- head: `b0cff64`
- start_head: `b0cff64`
- worktree: `D:\CodeSpace\prj_rechnung\bills_analysis_backend`
- status: in_progress

## [2026-02-10 12:41:46] END agent-b-fix-azure-silent-failure
- branch: `feat-backend`
- commit: `b0cff64`
- summary: backend: add v1 multipart batch upload API and contracts
- uncommitted_files: `AGENTS.md`, `README.md`, `SESSION_NOTES.md`, `pyproject.toml`, `src/bills_analysis/extract_by_azure_api.py`, `tests/cleanup_outputs.py`, `tests/json_to_excel_map.py`, `tests/json_to_excel_office.py`, `tests/merge_daily_excel.py`, `tests/merge_excel_entry.py`, `tests/merge_office_excel.py`, `tests/run_with_category.py`, ... (+2 files)
- next: Run uv sync to install new DI dependencies and rerun category pipeline with valid Azure env vars
- risk_or_note: Medium: extraction still returns null until env has Azure DI package and credentials
- status: done
- 
## [2026-02-08 23:56:34] START frontend-m1
- branch: `feat-frontend`
- head: `30ed1b6`
- worktree: `D:\CodeSpace\prj_rechnung\bills__frontend`
- status: in_progress

## [2026-02-10 13:55:35] END frontend-m1
- branch: `feat-frontend`
- scope: `frontend/**` M1->M2.1 upload/manual-review workflow
- status: in_progress
- note: Upload and Manual Review UI are connected; one-click Submit in Confirm Results now chains review + queue merge.
- note: Monthly Excel source switch now supports `from Local` and `from Lark` (scaffold); local maps to `local://<filename>`.
- next: split first-version frontend commits into tooling/contracts/upload/review/docs and push for backend联调.
- risk: Local Excel currently passes only string path token, backend has no binary upload parsing yet.

## [2026-02-10 17:05:17] START frontend-m2-commit-split
- branch: `feat-frontend`
- head: `28997aa`
- start_head: `28997aa`
- worktree: `D:\CodeSpace\prj_rechnung\bills__frontend`
- status: in_progress

## [2026-02-10 17:05:43] END frontend-m2-commit-split
- branch: `feat-frontend`
- commit: `28997aa`
- summary: frontend: update mock workflow semantics and harden hook tests with act and timing-safe waits to eliminate flaky async assertions
- uncommitted_files: `SESSION_NOTES.md`
- next: Office scenario integration and end-to-end validation in real API mode.
- risk_or_note: Backend and frontend review-row normalization may diverge again; keep v1 payload contract strict and re-run full smoke after backend updates.
- status: done
