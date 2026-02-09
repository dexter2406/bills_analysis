# AGENTS.md

## 1) Project 介绍
本项目是一个面向餐馆内部使用的账单归档与分析 Web App。核心场景：
- daily：店长每天上传当日结算小票和零星支出 PDF，系统提取 Brutto/Netto/store_name 等并人工校验后入库（当前载体为 Excel）。
- office：每月上传银行支出/发票 PDF，系统提取 brutto/netto/sender/tax_id/receiver等 校验信息，人工确认后追加到月度数据中。
- 上传 PDF 会做压缩归档，并生成可预览链接，便于人工核查。

当前技术方向：
- 前端：Azure Static Web Apps（计划）
- 后端：FastAPI + Python（Azure Functions / Queue 模式计划）
- 文档识别：Azure Document Intelligence（office 还使用 Azure OpenAI 做语义补充）

## 2) 当前进展（已验证脚本）
以下脚本已用于本地流程验证（主要在 tests/ 与 src/）：

### Pipeline / 提取
- `tests/run_with_category.py`
  - 总入口；按类别组织输入（daily: bar/zbon；office）。
- `tests/vlm_pipeline_api.py`
  - 主处理流程：调用 Azure DI 提取、归档压缩 PDF、产出结果 JSON。
- `src/bills_analysis/extract_by_azure_api.py`
  - Azure DI + Office 场景补充语义提取逻辑。
- `src/bills_analysis/preprocess.py`
  - 图像预处理与 PDF 压缩相关逻辑。
- `src/bills_analysis/render.py`
  - PDF 渲染相关。

### JSON -> 待校验 Excel
- `tests/json_to_excel_map.py`（daily）
- `tests/json_to_excel_office.py`（office）
- `src/bills_analysis/excel_ops.py`
  - 日期规范化、阈值判断、映射和通用 Excel 操作函数。

### 校验后合并
- `tests/merge_excel_entry.py`（合并入口）
- `tests/merge_daily_excel.py`
- `tests/merge_office_excel.py`

### 其他
- `tests/config.json`：静态阈值/参数配置（data-driven）
- `tests/cleanup_outputs.py`：中间产物清理
- `tests/vlm_pipeline_report.py`：报告实验脚本（后续可产品化）
- 注意：`playground/` 下内容为实验性，不作为主线代码依据。

## 3) 代码与架构规划
### 3.1 目标目录
- `src/bills_analysis/api/`：FastAPI routes（HTTP 输入输出）
- `src/bills_analysis/services/`：业务编排（process/review/merge）
- `src/bills_analysis/integrations/`：外部适配（azure/excel/storage/queue/repo）
- `src/bills_analysis/models/`：schema/contract（API、任务、结果模型）
- `src/bills_analysis/workers/`：异步任务处理（queue consumer）
- `frontend/`：前端工程（SWA 部署）

### 3.2 代码生成要求
- 对新增或者修改的函数、class定义，或者新脚本，必须有注释，可以视功能复杂度选择一句话或者一段话注释，统一用3对引号的形式。
- 对于枚举定义，需要给出注释（每个enum项后用#号注释即可），但如果是通过Pydantic定义的枚举类，也要遵循上述对类的注释要求。


## 4) 双 Session 协作规则（核心）
### 4.1 角色边界
- Session A（Backend）仅改：
  - `src/bills_analysis/**`
  - 后端相关 `tests/*.py`（迁移期）
  - `README.md` 后端段落
- Session B（Frontend）仅改：
  - `frontend/**`
  - 前端相关文档与 API 调用示例

### 4.2 禁止互改
- 前端 session 不改 `src/bills_analysis/**` 业务逻辑。
- 后端 session 不改 `frontend/**` UI/样式/构建配置。

### 4.3 分支与提交约定
- Backend 分支：`main`或者`feat-backend*`
- Frontend 分支：`feat-frontend*`
- Commit 前缀：
  - Backend: `backend: ...`
  - Frontend: `frontend: ...`
- 不允许在同一 commit 混合前后端改动。

### 4.4 Session Notes 机制（个人多 Session，必做）
本项目是个人开发，统一使用 `SESSION_NOTES.md` 记录多 session 交接。

记录方式（半自动）：
- session 开始时执行：
  - `python scripts/session_notes.py start --session <session-name>`
- session 结束时执行：
  - `python scripts/session_notes.py end --session <session-name> --next "<next>" --risk "<risk>"`

说明：
1. `start` 自动记录分支、HEAD、worktree、时间。
2. `end` 自动记录最近一次 commit、改动文件列表。
3. `next` 和 `risk` 由人工填写，保证后续 session 可直接接续。

强制规则（防止前后端记录不一致）：
1. 所有 Agent（含 Frontend/Backend）在开始实际编码/改文件前，必须先执行一次 `start`；未记录 `START` 的 session 视为不合规，不应提交。
2. 所有 Agent 在结束工作（即将交接/暂停）时必须执行一次 `end`，即使本次 session 没有产生 commit 也要记录（`end` 允许记录 WIP/无提交，但必须填写 next/risk）。
3. 同一 `session-name` 允许多次调用 `end`：后一次 `end` 必须覆盖同 session 的上一条 `END` 记录（不追加重复 END），以最后一次为准。

### 4.5 API 契约优先
- 前后端统一读 `src/bills_analysis/models/` 中的 schema。
- API 变更必须先更新 schema，再更新调用方。
- breaking change 必须在 `SESSION_NOTES.md` 标红说明（在 `risk_or_note` 中明确）。

### 4.6 配置与密钥
- `.env` 不入库。
- 示例放 `.env.example`。
- 阈值与业务参数统一走 `tests/config.json`（后续迁移到 `config/`）。



## 5) 近期里程碑
- M1：把 tests 中已验证业务逻辑下沉到 `services/integrations`，保持行为不变。
- M2：开放 API（create batch / query status / submit review / merge）。
- M3：前端完成上传-校验-确认-下载闭环。

## 5.1 启动与验证最小命令
- 旧流程（真实业务链）：  
  `uv run python tests/run_with_category.py --bar <bar.pdf> --zbon <zbon.pdf> --run_date 04/02/2026`
- 新 API 启动：  
  `uv run invoice-web-api`
- API 健康检查：  
  `GET http://127.0.0.1:8000/healthz`
- Schema 契约测试：  
  `uv run pytest tests/test_api_schema_v1.py -q`
- 导出 OpenAPI v1 基线：  
  `uv run python scripts/export_openapi_v1.py`

## 5.2 当前里程碑冻结点
- `v1` API schema 已冻结（`src/bills_analysis/models/`）。
- 非兼容变更禁止：不得删除/重命名/改类型已发布字段。
- 如需变更，必须先版本升级（如 `v1.1`/`v2`）并在 `SESSION_NOTES.md` 标注 breaking change。

## 6) 从本地 Excel 过渡到 Lark 的目标工作流
当前流程：`PDF -> 识别 JSON -> 待校验 Excel -> 人工修正 -> merge Excel`。

目标流程（Web App）：
1. 用户在 Web App 选择类型（daily/office）、上传 PDF、设置 run_date。
2. 后端异步处理（提取 + 压缩归档 + 预览链接）并产出待校验数据（JSON/DB）。
3. 前端展示可编辑表单（替代本地“待校验 Excel”）并提供 PDF 预览按钮。
4. 用户确认后点击 merge。
5. 后端将确认数据写入标准中间层，再调用 Lark API 写入目标表。
6. Web App 返回 merge 结果（成功条数、失败条数、失败原因、导出链接）。

Lark 接入策略：
- 支持前端输入 Lark 链接，但默认不建议业务用户手填完整链接。
- 推荐后端配置 `app_id/app_secret/base_id/table_id`，前端仅选择目标模板，降低误填风险。
- 所有 merge 写入需保留审计日志（操作者、时间、目标表、变更摘要）。

## 7) Definition of Done（每个任务）
- 功能可运行（本地最小命令）
- 有日志和错误提示
- 不破坏既有脚本主流程
- 文档同步更新（README + SESSION_NOTES.md）
