# Collaboration Boundaries

## Agent 改动范围

- Frontend session (Agent A) 仅改：
  - `frontend/**`
  - 前端相关文档与 API 调用示例
- Backend session (Agent B) 仅改：
  - `src/bills_analysis/**`
  - 后端相关 `tests/*.py`（迁移期）
  - `README.md` 后端段落

## 禁止互改

- 前端不改 `src/bills_analysis/**` 与 `tests/*.py` 业务逻辑。
- 后端不改 `frontend/**` UI/样式/构建配置。

## 提交约定

- Backend 分支：`feat-backend*`，commit 前缀：`backend: ...`
- Frontend 分支：`feat-frontend*`，commit 前缀：`frontend: ...`
- 单个 commit 不混合前后端改动。

## 安全与改动约束

- 禁止跨边界改动（遵循上述范围）。
- `.env` 不入库，示例配置放 `.env.example`。
- 阈值与业务参数统一走 `tests/config.json`（后续迁移到 `config/`）。
- 所有 merge 写入需保留审计日志（操作者、时间、目标表、变更摘要）。
- 目标流程为：`PDF -> 提取/归档 -> 待校验数据 -> 人工确认 -> merge -> Lark`。

## 前端并行开发提醒

- 优先保障上传/状态查询/校验提交/merge 调用链路闭环。
- 若后端 contract 发生版本升级，必须先明确版本切换窗口再联调。
