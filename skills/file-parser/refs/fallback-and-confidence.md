# 解析降级链与置信度

`scripts/parse.py` 的核心契约：**宁可如实报告「解析不完整」，也不输出假装成功的空结果。**

---

## 1. 降级链（按格式）

| 格式 | 档位顺序 | 每档依赖 | 判定要点 |
|------|---------|---------|---------|
| `.pdf` | `mineru` → `pymupdf` → `pdfplumber` → `pdf-ocr` | MinerU CLI（可选）/ PyMuPDF / pdfplumber / PyMuPDF 渲染 + OCR | 文本层每页 < 30 字符视为扫描件，自动往下走 |
| `.docx` | `docx`（python-docx） → 失败即 BLOCKED | python-docx | 段落样式映射标题、表格转 MD、内嵌图片走 OCR |
| `.pptx` | `pptx`（python-pptx） → 失败即 BLOCKED | python-pptx | 每页一章，表格/图片单独处理 |
| `.xlsx` | `xlsx`（openpyxl） | openpyxl | 每表一章，空行跳过，合并单元格只留左上角 |
| 图片 | `image-ocr` | ocr.py（winsdk → pytesseract） | 单图失败只记告警，不中断批量 |
| 旧格式 `.doc/.ppt/.xls/.odt/.rtf/.epub` | `anydoc`（`npx -y @firecrawl/anydoc`） → `libreoffice` | Node 20+ 或 LibreOffice | anydoc 退出码 3 表示「需 OCR」，提示先转 PDF |
| `.md/.txt/.csv/.json` | `text` | 无 | 直读，`utf-8` + `errors=replace` |

MinerU 未安装时**不算错误**，只记一条 `fallback_attempts`，直接由 PyMuPDF 接管。

## 2. 两个记录字段，不要混用

| 字段 | 含义 | 例子 |
|------|------|------|
| `warnings` | **内容层面**的问题，影响置信度 | 「表格存在合并单元格，已按众数 3 列对齐」「第 4 页 OCR 失败」 |
| `fallback_attempts` | **降级轨迹**，说明为什么不走首选档 | 「mineru: 未安装 mineru CLI」「pymupdf: 文本层过薄（0 字符 / 2 页）」 |
| `fallback_used` | 最终生效的档位名 | `pymupdf` / `pdf-ocr` |
| `status` | 结论 | `ok` / `degraded` / `blocked` |

把降级轨迹写进 `warnings` 会被重复扣分（同一问题扣两次），所以两者必须分开。

## 3. 置信度算法

```
conf = 档位基础分
       − 0.30 × 近空白块占比      # 每页字符数 < 阈值(默认 30，OCR 档 10，单图 5)
       − 0.02 × min(告警条数, 5)
       − 0.08（档位名以 ocr 结尾时）
clamp 到 [0.05, 0.99]，保留两位
```

| 档位 | 基础分 | 理由 |
|------|-------|------|
| `text` | 0.98 | 原文直读 |
| `mineru` | 0.95 | 有排版还原（标题层级、公式、表格结构） |
| `docx` | 0.92 | 样式/表格/元数据齐全 |
| `xlsx` | 0.92 | 结构化程度最高 |
| `pptx` | 0.90 | 版式信息（位置）丢失 |
| `pymupdf` | 0.88 | 文本层好，但表格线抓不到 |
| `anydoc` | 0.85 | 第三方转换，结构信息弱 |
| `pdfplumber` | 0.82 | 兜底，逐页文本质量参差 |
| `libreoffice` | 0.75 | 二次转换，格式漂移 |
| `image-ocr` | 0.62 | 识错字不可避免 |
| `pdf-ocr` | 0.60 | 渲染 + OCR，双重损耗 |

判定：`status = ok`（≥0.75）/ `degraded`（0.50–0.75）/ `blocked`（<0.50 或全档失败）。

**下游怎么用**：`ok` 可直接进 RAG/引用；`degraded` 必须交叉核对原文关键数字；`blocked` 不得作为事实依据，
标记「人工介入」并回传失败原因（对应 doc-parse 原契约里的 `BLOCKED` 语义）。

## 4. 失败与人工介入

| 情形 | 行为 |
|------|------|
| 单档失败 | 记 `fallback_attempts`，自动降级，不中断 |
| 全部档位失败 | `status=blocked`、`markdown=""`、`error` 写原因，退出码 1，**不输出残缺正文** |
| 单页 OCR 失败 | 该页留空 + `warnings` 记录，块级 `chars=0`，整篇降为 `degraded` |
| 超大文件（>200 页） | 先用页码范围切分再解析，避免内存与超时；块级失败只影响该块 |

## 5. 与 antinet `doc-parse` 的对应关系

| doc-parse 原设计 | 本技能落点 |
|------------------|-----------|
| MinerU 首选、PyMuPDF 次选、pdfplumber 兜底 | `scripts/parse.py` 前三个 PDF 档位，一字对应 |
| 新增第四档「扫描件 OCR」 | `pdf-ocr`（用 PyMuPDF 渲染，不额外依赖 poppler） |
| `fallback_used` / `confidence` 输出 | 同一字段名，JSON 契约兼容 |
| 「三级全失败 → 标记人工介入，不输出残缺结果」 | `status=blocked` + `error`，正文留空 |
| `metadata`（标题/页数/表格数/作者） | `metadata`（另补 `chars`、`created`、`modified`、`sheets`、`images`） |
| 依赖 `core.runtime.AgentSession`（不可移植） | 纯 CLI + 纯 Python，可离线单跑，无私有包依赖 |
| 无缓存 | 复用本技能 MD5 缓存（`docs/temp/{stem}.md5`） |
| 无图片/旧格式处理 | docx/pptx 内嵌图 OCR + anydoc/LibreOffice 旧格式链 |
