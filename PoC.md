目标：把“可交付的MVP里的一切”先拆掉，只围绕**本地纯后端 CLI**把最硬的链路打通：**PDF输入 → 预处理 → OCR/解析 → 字段抽取 → 置信度与告警 → 坐标/证据截图 → 结构化输出**。下面按“你实际写代码的顺序”给出具体步骤（每一步都能独立跑、可回归）。

---

## 0) 建仓与可回归骨架（半天）

1. 建 repo 与目录骨架（先不管前端/云/DB）

   * `src/`：核心库
   * `cli/`：命令行入口（Typer/Click）
   * `tests/`：最小回归（golden files）
   * `data/samples/`：样例 PDF（电子版/扫描版各 ≥5）
   * `outputs/`：运行产物（JSON、截图、debug图）
2. 定义**统一输出契约**（先写空结构也行）

   * `extraction.json`：字段、数值、置信度、来源页码、bbox、证据截图路径、告警列表
3. 选定运行方式

   * `make run` / `poetry run` / `uv run` 固定下来
   * 依赖锁定（OCR、PDF渲染、图像处理、布局/文字提取）

---

## 1) 输入与PDF渲染层（先解决“看得见”）(0.5–1天)

目标：任何 PDF 都能稳定变成逐页图像，并保留页尺寸/缩放关系。

1. CLI：`invoice extract <pdf_path> --out outputs/run1/`
2. 渲染模块：

   * `render_pdf_to_images(pdf) -> [PageImage]`
   * 输出：每页 PNG（固定 DPI，比如 200/300 可切换）+ 元数据（页宽高、DPI、页号）
3. Debug：保存每页缩略图，保证你肉眼能检查“歪斜/模糊/阴影”类型

---

## 2) 预处理管线（只做扫描件必要项）(1天)

目标：让扫描件 OCR 可用、且每一步可视化对比。

1. 判别页面类型（启发式即可）：

   * 电子PDF（可文本层提取） vs 扫描图像（几乎无文本层）
2. 图像预处理（按开关组合，便于AB测试）：

   * 去噪/锐化（轻量）
   * 二值化（自适应阈值）
   * 倾斜校正（deskew）
   * 对比度增强
3. 输出：`page_01.preproc.png`，并记录用了哪些开关参数（写入 run metadata）

---

## 3) OCR/文本获取的“双通道策略”（关键）(1–2天)

目标：电子PDF尽量走文本层；扫描件走OCR；两者输出统一为“tokens with bbox”。

1. 通道A：**电子PDF文本层提取**

   * 产物：每个词/行的文本 + bbox + 页号
2. 通道B：**OCR**（扫描件或A失败时）

   * 产物同上：`Token(text, conf, bbox, page)`
3. 统一结构：

   * `DocumentTokens = {pages: [ {page_no, width, height, tokens:[...]} ] }`
4. Debug：把 tokens bbox 画框叠加到页面图上输出（`page_01.tokens_overlay.png`）

---

## 4) 字段抽取 V0：先用规则把“能用的80%”拿下（1–2天）

目标：先别追求泛化，先把你已对齐的核心字段跑通：日期、发票号、税号/UID、净额/税额/总额、税率。

1. 先做**候选定位**（Candidate Generation）

   * 基于关键词集合（德语为主，英语兜底）：

     * 总额：`Brutto`, `Gesamt`, `Summe`, `Total`…
     * 净额：`Netto`, `Zwischensumme`…
     * 税：`MwSt`, `USt`, `VAT`…
     * 税号：`Steuernummer`, `USt-IdNr`, `USt-Id`, `VAT ID`…
     * 日期：`Rechnungsdatum`, `Datum`…
   * 候选数字识别：金额正则（德式逗号小数）、日期正则、税号格式
2. 再做**候选配对与打分**（Candidate Scoring）

   * 距离：关键词与数字的空间距离（同一行优先，其次邻近行）
   * 语义：同一块区域内同时出现 Netto/Brutto/MwSt 的一致性
   * 业务一致性：`Brutto ≈ Netto + Steuer`、税率是否合理（7%/19%为常见，但不要写死）
3. 输出抽取结果（即使不确定也要输出候选Top3，附置信度与告警）
4. Debug：打印一份 `extraction.md`（方便你快速肉眼验）

---

## 5) 证据截图（你提到的“敏感+可核对”核心）(0.5–1天)

目标：每个字段都能回指到原PDF的“证据图”。

1. 以字段的 bbox 为中心做裁剪（可扩边距 10–30px 或按比例）
2. 输出：`evidence/brutto_p1.png`, `evidence/ustid_p1.png` …
3. 在 `extraction.json` 里记录：`page_no`, `bbox`, `evidence_path`
4. Debug：同时输出“带框的整页图”，方便定位字段在全页的语境

---

## 6) 置信度与告警策略（先做可解释的规则）(0.5–1天)

目标：不用ML也能把“哪些需要人工确认”标出来。

1. OCR置信度低：字段来自 tokens 的平均 conf < 阈值
2. 业务校验失败：Brutto/Netto/税不一致（允许小误差）
3. 缺失关键字段：比如没找到日期/总额/税号
4. 多税率/多行金额：提示“可能存在多税率拆分”，需要人工确认
5. 告警写入：`warnings:[{code, message, severity, evidence_refs}]`

---

## 7) CLI 体验做到“可回归 + 可批处理”（0.5天）

目标：你能对一批PDF跑回归，对比差异。

1. `invoice extract file.pdf --out runX/ --debug`
2. `invoice batch data/samples/*.pdf --out runs/2025-12-30/`
3. 产物固定化：

   * `extraction.json`（机器读）
   * `extraction.md`（人读）
   * `evidence/`（核对）
   * `overlays/`（debug）

---

## 8) 最小回归集（立刻做，持续增量）

目标：以后你换OCR、调参数、加规则，不会“越改越乱”。

1. 每种类型挑 2–3 个“黄金样本”
2. 保存期望输出（至少关键字段）
3. 每次改动跑：对比 `extraction.json` 的关键字段与告警数量

---

# 你这条PoC链路完成的“验收标准”

* 输入电子PDF与扫描PDF各 ≥5 个：都能生成逐页图片
* 至少 1 个电子PDF走文本层成功，1 个扫描PDF走OCR成功
* 对每个字段输出：值 + 页码 + bbox + evidence截图
* 有明确告警：低置信度/字段缺失/金额不一致能触发
* 批处理跑完能生成稳定目录结构与结果文件

---

如果你需要我把以上步骤进一步落到“目录结构 + Python模块接口签名 + CLI命令定义（含输出JSON schema）”，我可以直接给出一版可复制的骨架。你要用 Typer 还是 Click？OCR倾向 Tesseract 还是 PaddleOCR/DocTR？
