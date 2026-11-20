---
name: pdf-generation
description: 用 reportlab + pypdf 生成与编辑 PDF——Markdown 转 PDF（中文 CID/TrueType 字体、标题层级、表格、代码块、页眉页码）、合并拆分旋转、斜向水印、AES 加密解密、AcroForm 表单域读取与填写、交付前自检（页数/字符数/空页/首页预览）；当需要产出 PDF 报告或交付件、把 md 讲稿转成 PDF、给 PDF 加水印/密码、填写 PDF 申请单/合同表单、拆分合并扫描件、或排查「PDF 中文变方块 / 表格错位 / 交付前怎么验」时自动启用。

---

# pdf-generation

> 命令行里没有 Word，也没有 GUI：PDF 的**生成**用 reportlab（纯 Python，可复现），
> **编辑**用 pypdf，**校验**用 pypdf 读回文本 + PyMuPDF 渲染目视。

## 适用场景

| 触发条件 | 说明 |
|---------|------|
| "把这份 Markdown 转成 PDF" | `md2pdf`：标题/列表/表格/代码块 → 排版好的 A4 |
| "生成一份 PDF 报告 / 申请单 / 交付件" | `md2pdf` 出正文，再叠 `watermark`、`encrypt` |
| "把这几份 PDF 合成一份 / 只取第 1-3 页" | `merge` / `split` |
| "扫描件方向是歪的" | `rotate --angle 90 --pages 1,3` |
| "加水印 / 加密码再发出去" | `watermark` / `encrypt`（AES-128） |
| "填这张 PDF 申请单" | `form-fields` 先看域名 → `fill-form` 按 JSON 填 |
| "交付前怎么验" | `check`：页数、每页字符数、近空页、首页 PNG |

| 不适用 | 改用 |
|--------|------|
| 读取/解析已有 PDF（抽文本、抽表格、扫描件 OCR） | `file-parser`（四档 fallback + 置信度） |
| 生成 Word / PPT / Excel | `docx-generation` / `pptx-generation` / `weekly-report` |
| 要画图（架构图、流程图）再插进 PDF | `diagram-design`（出 PNG）或 `drawio-skill` |
| 要把 PDF 表单做成"可编辑 Word 模板" | 无对应技能，先确认交付格式 |

---

## 快速开始

```bash
python scripts/pdf_ops.py md2pdf doc.md -o out.pdf --title "数据门禁设计说明" --author 张三
python scripts/pdf_ops.py info out.pdf                     # 页数/元数据/表单域数量
python scripts/pdf_ops.py check out.pdf --preview p1.png   # 交付自检 + 首页预览
python scripts/pdf_ops.py merge -o all.pdf a.pdf b.pdf c.pdf
python scripts/pdf_ops.py split all.pdf --pages 1-3,7 -o part.pdf
python scripts/pdf_ops.py watermark all.pdf -o wm.pdf --text "内部资料 请勿外传"
python scripts/pdf_ops.py encrypt wm.pdf -o enc.pdf --password 1234
python scripts/pdf_ops.py form-fields form.pdf --json > fields.json
python scripts/pdf_ops.py fill-form form.pdf data.json -o filled.pdf
```

依赖：`pip install reportlab pypdf pymupdf`（pymupdf 仅 `check --preview` 用）。

---

## md2pdf：能排什么、不能排什么

| Markdown | 渲染结果 |
|----------|---------|
| `# / ## / ###` | 居中大标题 / 二级 / 三级标题 |
| 普通段落 | 正文，`wordWrap="CJK"`（中文按字断行，不会一个大词整体换行） |
| `- ` / `1. ` | 项目符号 / 编号列表 |
| `\| a \| b \|` 表 | 三线表（表头灰底、跨页自动重复表头） |
| ```` ``` ```` 代码块 | 灰底等宽块（`Courier`） |
| `**粗体**` `\`代码\`` `[x](url)` | `<b>` / 等宽 / "文字（url）" |
| 图片 `![](x.png)` | **不渲染**（先确认是否需要嵌图，需要就用 reportlab 的 `Image` 手写） |
| 目录（TOC） | 不自动生成，需要就手写章节列表（reportlab 无一键 TOC） |

`--title` 同时作为**封面标题**和**每页页眉**；页脚固定"第 N 页"（`_decorate` 回调）。

## 中文字体

| 方式 | 用法 | 说明 |
|------|------|------|
| 内置 CID（默认） | 不传 `--font` | `STSong-Light`，免字体文件，任何机器都能渲染，代价是**只有一个字重**（没有真正加粗） |
| 系统 TrueType | `--font C:/Windows/Fonts/msyh.ttc` | 有粗体需求时才用；`ttc` 集合默认取第一个字面 |
| 缺字形（方块/乱码） | — | 说明字体没有该字面：换 `--font`，别指望 reportlab 自动 fallback |

要点：
1. **`wordWrap="CJK"` 必须设**，否则长中文段落按空格断行，右侧留一大片空白；
2. 中英混排不用换字体：`STSong-Light` 的 Latin 字形可直接用，但**加粗无效**——要强调就用字号或颜色；
3. 表单域（AcroForm）**不接受 CID 字体名**，只认标准 14 字体（见下节）。

## 表单（AcroForm）

```bash
python scripts/pdf_ops.py form-fields form.pdf        # 域名 + 类型(/Tx /Btn /Ch) + 当前值
python scripts/pdf_ops.py fill-form form.pdf data.json -o filled.pdf   # data.json: {"applicant":"张三"}
```

- **只能填「已有表单域」的 PDF**：pypdf 不能凭空创建表单域；要造表单，用 Word/Acrobat 导出，或 reportlab `acroForm`（仅标准 14 字体）。
- 域名必须完全匹配：脚本会先比对现有域名，不认识就报错并列出可用域名，不会静默丢字段。
- 中文值：域字体非中文字体时，填进去会显示空白/方块——这种表单要么改域默认外观（`/DA`），要么把值改成英文/拼音，要么改为"生成新 PDF 盖章面"。
- `--flatten` 只是关闭域外观重生成，**不是真正扁平化**；需要不可编辑的定稿，用打印到 PDF（或 PyMuPDF 渲染成图回写）。

## 校验（交付前必做）

```bash
python scripts/pdf_ops.py check out.pdf --preview p1.png
```

| 检查项 | 判据 |
|--------|------|
| `pages` / `text_chars` | 页数与总字符数符合预期（0 字符 = 全是图片或生成失败） |
| `near_empty_pages` | 每页 <10 字符的页码列表；非空就得看是空白页还是图片页 |
| `verdict` | `ok` / `warning` |
| `--preview` | 渲染首页 PNG，**人工目视**（丢内容、字体、表格塌陷只有肉眼能发现） |

看预览图时若要用 OCR 复核文字：**按 ≥300dpi 裁剪渲染**，低 dpi 下 OCR 会把拉丁小字读成乱码（实测 `pdf-generation` 被读成 `pdf-generaüon`），那不是 PDF 的问题。

## 常见错误

| 问题 | 现象 | 处理 |
|------|------|------|
| 中文变方块/空白 | 只看到 `.notdef` 框 | 确认 `register_cjk()` 被调用、`fontName` 一致；TrueType 路径用绝对路径 |
| 中文段落右侧大片空白 | 一行只放得下几个字 | 忘了 `wordWrap="CJK"` |
| 表格文字塌成竖排 | 列宽不够，CJK 被逐字挤断 | 缩短单元格文本或减列；`Table(colWidths=[...])` 显式给宽度 |
| `ParagraphStyle() got multiple values for 'leading'` | 重复传 `leading` | 基础样式里已有 `leading`，子样式别再传 |
| `merge_page` 抛 `DeprecationError` | pypdf ≥7 移除未挂载页面的合并 | 先 `writer.add_page(page)`，再在 `writer.pages` 上 `merge_page` |
| `form font name ... is not one of the standard 14 fonts` | reportlab 建表单域用了 CID 字体 | 表单域用默认 Helvetica，中文标签画在正文层 |
| 水印只在部分页出现/被裁掉 | 水印页尺寸与目标页不一致 | 水印层按每个目标页的 `mediabox` 逐页生成 |
| 加密后自己的脚本读不了 | `is_encrypted` 为真且无密码 | 读时传 `--password`；给用户的只有用户密码 |
| 大文件 md2pdf 内存爆掉 | 一次性 build 上千 flowables | 分批 `doc.build()`（每批一个 PDF 再 `merge`） |
