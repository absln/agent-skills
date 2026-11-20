---
name: file-parser
description: 把 PDF/Word/PPT/Excel/图片/旧版 Office/EPUB 等文档解析成结构化 Markdown，带元数据、解析置信度与降级轨迹（PDF 四档 fallback：MinerU → PyMuPDF → pdfplumber → 渲染+OCR），含 Windows 内置 OCR 识别、表格抽取与 MD5 缓存；当需要读取 docs/refs 下的资料、提取扫描件文字、把文档转成可检索 Markdown、或排查「PDF 抽不出文字 / 表格错位 / 中文 OCR 乱码 / 解析结果能不能信」时自动启用。
---

# file-parser

> 文档解析的唯一入口：**任意格式 → 结构化 Markdown + 元数据 + 置信度**。
> 解析结论是可审计的——档位（`fallback_used`）、降级原因（`fallback_attempts`）、
> 可信度（`confidence` / `status`）三者随正文一起产出，下游据此决定「直接用 / 核对 / 人工介入」。

## 快速开始（v1.2）

```bash
python scripts/parse.py docs/refs/需求说明.docx          # 打印 Markdown
python scripts/parse.py docs/refs/ --out docs/temp --json # 批量：.md + .json + .md5 缓存
python scripts/parse.py scan.pdf --ocr-scale 4 --no-cache # 扫描件：放大 OCR、跳过缓存
python scripts/parse.py --engine-list                    # 看本机 OCR 引擎与语言包
```

一次产出三件东西：`{stem}.md`（正文）、`{stem}.json`（完整契约）、`{stem}.md5`（缓存键）。
同名同 MD5 再来一次直接命中缓存；同名不同扩展名自动带上扩展名，避免互相覆盖。

### 产物契约（`{stem}.json`）

| 字段 | 含义 |
|------|------|
| `markdown` | 结构化正文（标题层级、表格、图片 OCR 段落） |
| `metadata` | `format / pages / title / author / tables / sheets / images / chars / created` |
| `confidence` | 0–1 解析置信度，算法与档位基础分见 [`refs/fallback-and-confidence.md`](refs/fallback-and-confidence.md) |
| `confidence_factors` | 打分明细（`tier_base`、`low_coverage_ratio`、`final`），便于追责 |
| `fallback_used` | 最终生效档位：`mineru / pymupdf / pdfplumber / pdf-ocr / docx / pptx / xlsx / anydoc / image-ocr / text` |
| `fallback_attempts` | 降级轨迹（每档失败原因）；**与 `warnings` 分开记，不重复扣分** |
| `warnings` | 内容层面问题（表格列数不一致、某页 OCR 失败…） |
| `status` | `ok`(≥0.75) / `degraded`(0.50–0.75) / `blocked`(<0.50 或全档失败) |

**下游用法**：`ok` 可直接引用；`degraded` 关键数字必须回原文核对；`blocked` 不得当事实依据，标记人工介入。

### 合并自 doc-parse 的部分

原 antinet 的 `doc-parse`（密卷房 Worker）与本技能合并，取其可移植的部分：三级 fallback、
置信度透明、`BLOCKED` 语义、元数据契约；丢弃其 `core.runtime` 私有包依赖与「输出预存全文」的假降级。
逐项映射表见 [`refs/fallback-and-confidence.md`](refs/fallback-and-confidence.md) §5。
表格抽取细则（无线框 PDF、跨页表、合并单元格）见 [`refs/pdf-tables.md`](refs/pdf-tables.md)。

---

## 目录约定（v1.1 新增）

| 目录 | 用途 | 权限 | 说明 |
|------|------|------|------|
| **`docs/draft/`** | **产出文档目录** | 写入 | 正式设计文档、报告、草稿、建议稿等**最终产物** |
| **`docs/temp/`** | **解析缓存目录** | 自动维护 | 解析缓存（txt/ocr/md5/图片）为**临时产物**，可随时清理 |

**区分原则**：
- `docs/temp/` 仅存放**机器可再生的中间产物**（解析缓存、OCR 结果、MD5、原始图片）
- `docs/draft/` 存放**对用户有交付价值的内容**（设计文档、汇报材料、技能更新稿等）
- 严禁将正式产出写入 `docs/temp/`，严禁将缓存写入 `docs/draft/`
- `docs/temp/` 清理不影响任何正式文档

---

## 适用场景

| 触发条件 | 说明 |
|---------|------|
| 任务涉及 `docs/refs/` 或用户指定的 `.docx` / `.pdf` / `.pptx` / `.xlsx` / 图片文件 | 提取结构化文本供后续分析、引用、设计 |
| 文档含图片/扫描件、或 PDF 抽不出文字 | 降级到 OCR 档，逐页识别并标注置信度 |
| `.doc` / `.ppt` / `.xls` / `.rtf` / `.epub` 等旧格式 | `anydoc`（免安装 npx）或 LibreOffice 转 Markdown |
| 需要缓存解析结果 | 同名文件 MD5 未变时跳过解析（缓存于 `docs/temp/`） |
| 下游要判断「这份解析能不能信」 | 读 `confidence` / `status` / `fallback_attempts` |

| 不适用 | 原因 |
|--------|------|
| 加密/密码保护的文档 | 需用户先解密 |
| 纯手写扫描件（无印刷文字） | OCR 识别率过低，需人工转录 |
| 要「生成」Word/PPT/PDF | 分别用 `docx-generation` / `pptx-generation` / `pdf-generation` |
| 要画图（流程图/架构图） | 用 `drawio-skill` 或 `diagram-design` |

---

## 执行步骤

### 1. 前置检查

```bash
# 检查核心依赖（docx/pdf/pptx/xlsx 解析）
python3 -c "import docx, pdfplumber, openpyxl; from pptx import Presentation; from PIL import Image; print('OK')"

# 缺依赖时安装
pip install python-docx python-pptx pdfplumber openpyxl Pillow pdf2image   # 必装
pip install winsdk          # OCR 推荐后端（Windows 内置引擎，不装 tesseract）
pip install pytesseract     # OCR 备选后端（另需 tesseract 引擎）

# 走 tesseract 后端时才需要的系统级安装（Windows 内置 OCR 不需要）
# Ubuntu: sudo apt install tesseract-ocr tesseract-ocr-chi-sim
# Windows: 下载 UB-Mannheim.TesseractOCR 安装包并配置 PATH
```

OCR 只有一个入口 `scripts/ocr.py`（纯 Python，**没有任何 .ps1**），后端自动挑选：先 `winsdk`，再 `pytesseract`。

```bash
python scripts/ocr.py --list        # 先确认本机有哪些引擎和语言包
```

### 2. 检查缓存

```
路径：docs/temp/{文件名}.md5
逻辑：
  - 若文件存在 且 MD5一致 → 读取 docs/temp/{文件名}.txt，结束
  - 若不存在或MD5不一致 → 继续步骤3
```

### 3. 按格式解析

> **有 `scripts/parse.py` 就用它**，本节是等价的实现说明（无脚本环境/需要定制时照此手写）。
> 脚本已覆盖：降级链、表格对齐、内嵌图片 OCR、元数据、置信度、缓存。

#### 3.1 .docx（Word）

```
1. doc = docx.Document(path)
2. 遍历 paragraphs → 按样式转 Markdown：
   Heading 1 → "# "
   Heading 2 → "## "
   Heading 3 → "### "
   Normal    → 直接输出
   List Bullet → "- "
   List Number → "1. "
3. 遍历 tables → 转 Markdown 表格
4. 提取图片（遍历 inline_shapes + runs）：
   - 检查 header / footer 中的图片
   - 保存到 docs/temp/{文件名}_imgs/
5. 异常时在文本中标记异常位置，不中断流程
```

#### 3.2 .pdf（PDF）

```
1. 尝试 pdfplumber 提取文本：
   with pdfplumber.open(path) as pdf:
       for page in pdf.pages:
           text = page.extract_text()
2. 若提取结果为空或每页字符数 < 50 → 判断为扫描件：
   a. pdf2image 转为图片
   b. pytesseract OCR 逐页识别
3. 提取页面中的表格 → page.extract_table()
```

#### 3.3 .pptx（PPT）

```
1. prs = Presentation(path)
2. 遍历 slides → 遍历 shapes：
   - 有 text 属性 → 提取文本
   - shape_type == 13（图片）→ 提取并 OCR
3. 每张 slide 内容用空行分隔
```

#### 3.4 图片（.jpg/.png/.bmp）

```
1. 直接调用 OCR：pytesseract.image_to_string(img, lang='chi_sim+eng')
2. 复杂图表可先用 layoutparser 分析版面再逐区域 OCR
```

#### 3.5 .xlsx（Excel，v1.1 新增）

```
1. wb = openpyxl.load_workbook(path)（需 pip install openpyxl）
2. 遍历 worksheets → 遍历行/单元格：
   - 有值单元格输出为 "{坐标}: {值}"，换行符替换为 " / "
   - 保留工作表名作为章节标题
3. 合并单元格：仅输出左上角值，其余为 None 跳过
4. 输出到 docs/temp/{文件名}.txt
```

### 4. 图片 OCR

统一用 `scripts/ocr.py`，Windows 内置 OCR 与 tesseract 只是它的两个后端，命令不变。

**方式 A：Windows 内置 OCR（推荐）**

```bash
pip install winsdk                                  # 一次性，不用装 tesseract
python scripts/ocr.py docs/temp/{文件名}_imgs/           # 传目录 = 逐张识别
python scripts/ocr.py --scale 4 shot.png            # 小字/截图：先放大 4 倍（推荐）
python scripts/ocr.py --md docs/temp/{文件名}.ocr.txt docs/temp/{文件名}_imgs/
```

- 调 `Windows.Media.Ocr`（WinRT）。**默认优先中文引擎**：`TryCreateFromUserProfileLanguages` 在英文档案系统上只给 `en-US`，中文会整段漏掉，因此脚本按 `zh-Hans-CN` → `zh-Hans` → `en-US` 挑，`--lang` 可强制指定
- 小图放大已内置：`--scale 4`（原 ps1 时代要手工跑 PIL 命令）；图超过引擎上限 10000px 时自动缩回
- 中文逐字带空格（`数 据 门 禁`）已自动合并汉字与全角标点间的空格；要原样保留引擎输出加 `--raw`
- 自动合并 Windows OCR 在汉字/全角标点之间插的空格：`数 据 门 禁` → `数据门禁`，`待确认 ： 是否` → `待确认：是否`
- 单图失败只打印 `ERR: ...` 并继续下一张，不中断整批
- 表格/两列排版会丢结构（单元格串成一行），只能用来“看懂内容”，不要当唯一依据
- 局限：截图里的中文字体名等专有名词容易被识别错（如「思源黑体」→乱码），需结合上下文校对

**方式 B：pytesseract（需另装引擎）**

```bash
pip install pytesseract && python scripts/ocr.py --engine tesseract a.png
```

- `--engine tesseract` 强制走后端；默认 `auto` 先试 Windows OCR，失败再落到这里
- `lang` 自动映射到 tesseract 语言码：`zh-Hans-CN` → `chi_sim+eng`、`en-US` → `eng`，传其他值原样使用
- 只装了 tesseract、没装 winsdk 时无需额外参数，`auto` 自动选它

**落盘**：两种后端输出格式一致，`--md` 直接产出

```
===== docs/temp/{文件名}_imgs/{文件名}_img_001.png =====
引擎语言: zh-Hans-CN
[识别文本]
```

再按下面格式归并进 `docs/temp/{文件名}.ocr.txt`，并在文本缓存对应位置插入标记 `[图片001 → {文件名}.ocr.txt]`：

```
=== 图片001 (位置: 第N页, 第M段后) ===
[识别文本]
---
```

> **聊天里的截图怎么拿到？** 当前模型看不了图片时，图会以 base64 存在 pi 会话文件
> (`$PI_SESSION_FILE`，JSONL) 里。用 Python 逐行 `json.loads` 找 `content[].type == "image"`，
> 把 `data` 字段 base64 解码写盘，再走上面 OCR。见 scripts/extract_session_images.py。

### 5. 校验与登记

```
1. 计算 MD5 → 写入 docs/temp/{文件名}.md5
2. 写入 `docs/temp/cache_index.md`（运行时产物，不随技能分发）：
<!-- audit-ignore: docs/temp/cache_index.md -->
   | 源文件 | 时间 | 格式 | 文本 | OCR | 图片数 |
   |-------|------|------|------|-----|-------|
   | docs/refs/xxx.docx | 2026-07-23 | docx | ✅ | ✅ | 3 |
3. 异常时在缓存中标记异常位置，不中断流程
```

---

## 常见错误

| 问题 | 现象 | 处理 |
|------|------|------|
| 缺依赖 | ModuleNotFoundError | 执行前置检查安装 |
| PDF 无文本 | 提取结果为空 | 自动切换为 OCR 模式 |
| OCR 中文乱码 | 结果全 ASCII | Windows OCR：`--lang zh-Hans-CN`，用 `--list` 确认有该语言包（设置→语言→中文→OCR）；tesseract：装 `tesseract-ocr-chi-sim` |
| Windows OCR 不可用 | `缺少 WinRT 绑定` | `pip install winsdk`；装不上就 `--engine tesseract` |
| 图片未提取 | 图片数=0 | 检查 header/footer/幻灯片母版/文档尾部；仍失败则标记"待手动提取" |
| MD5 不匹配 | 缓存失效 | 重新解析 |
| 大文档超时 | >200页或>50图 | 分片解析：先处理前50页 |
| docx 图片遗漏 | header/footer 图片未提取 | 遍历 runs 中的图片；仍遗漏则标记"待手动提取" |
| 格式丢失 | 样式标记不准 | 文件头注明"部分样式可能丢失" |
| 表格解析异常 | 合并单元格导致错位 | 保留原始文本顺序，标注"表格解析可能不完整" |
| 缓存目录 | 正式文档写入 docs/temp/ | 按目录约定区分：docs/draft/ 产出、docs/temp/ 缓存 |
| MinerU 未安装 | 首档直接跳过 | 正常降级，`fallback_attempts` 里有记录；要强排版还原再 `pip install -U "magic-pdf[full]"` |
| PDF 抽出的字全是空白框 | 字体未嵌入/CID 字体 | 降到 `pdf-ocr` 档：`--mineru off` 逼它走 OCR |
| 置信度偏低（degraded） | 扫描件、表格错位、OCR 识错 | 看 `confidence_factors.low_coverage_ratio` 与 `warnings` 定位；关键数字回原文核对 |
| 状态 blocked | 全档失败 | 读 `error` 字段；不要拿空正文继续推理，标记人工介入 |
| 同名文件互相覆盖 | 同名不同扩展名 | 脚本已自动加扩展名后缀；手写流程需自行区分 |

---

## 追踪机制

格式：`DOC-PARSE-{序号}.{子任务}.{执行点}`

```
示例：
DOC-PARSE-001        任务     docs/refs/需求说明.docx       ✅ 完成
DOC-PARSE-001.1      子任务   文本提取                 ✅ 完成 (45段, 3表格)
DOC-PARSE-001.1.1    执行点   样式映射                ✅ 完成 (5个Heading)
DOC-PARSE-001.2      子任务   图片OCR                 ⚠️ 部分完成 (3/4张)
DOC-PARSE-001.3      子任务   缓存写入                ✅ 完成
```

状态：✅ 完成 | ⚠️ 部分完成 | ❌ 失败 | ⏳ 待执行 | 🔄 进行中

---

## 输出

`scripts/parse.py --out docs/temp` 的产物（临时，可清理）：

```
docs/temp/                       # 解析缓存（机器可再生的中间产物）
├── {文件名}.md                  # 结构化 Markdown 正文（对下游有价值的可直接引用）
├── {文件名}.json                # 契约：markdown/metadata/confidence/fallback_used/status/warnings
├── {文件名}.md5                 # MD5 缓存键
├── {文件名}.ocr.txt             # （手工流程）OCR 文本汇总
├── cache_index.md               # 缓存索引
└── {文件名}_imgs/               # 提取出的原始图片
    ├── {文件名}_img_001.png
    └── ...
```

要交付给用户的解析结论（如「这份合同的关键条款梳理」）写 `docs/draft/`，不要把临时解析结果当交付物。
