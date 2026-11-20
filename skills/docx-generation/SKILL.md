---
name: docx-generation
description: 用 python-docx 或 Node.js docx 生成、读取、修复 .docx Word 文档——含中文字体（东亚轴）、图片压缩嵌入与题注、目录域代码、A4 页边距版式、Word COM 校验；当需要产出 Word 报告/正式文档、给图片加题注、生成自动目录、批量压缩图片体积、或排查"Word 打不开 / 图片丢失 / 中文字体不生效 / 目录不更新"时自动启用。
---

# DOCX Generation

Generate well-formed .docx documents with images, Chinese fonts, and table of contents.

## Quick Decision: Python vs Node.js

| Criterion | Python (python-docx) | Node.js (docx) |
|-----------|---------------------|-----------------|
| Stability | High | Moderate |
| Chinese font support | Native via `rFonts` | Manual XML manipulation |
| Image embedding | Stable | Known pitfalls (see below) |
| TOC generation | XML field code | Built-in `TableOfContents` |
| **Recommendation** | **Use for production** | Use only for simple text-only docs |

**Default choice: Python python-docx.** Only use Node docx when Python is unavailable or the project is Node-only with a trivial document structure.

## Python Workflow

### Setup

```bash
pip install python-docx pillow pywin32   # pywin32 仅 Validation 段用
```

```python
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from PIL import Image
import io
```

### Chinese Font Configuration

Set fonts on both the Western and East-Asian axes:

```python
run = para.add_run("中文文本")
run.font.name = "SimSun"
run._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")
```

For document-wide defaults:

```python
style = document.styles["Normal"]
style.font.name = "SimSun"
style._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")
```

### Image Embedding with Captions

Always compress images before embedding. Use Pillow to resize and optimize:

```python
def compress_image(src_path, max_width=900) -> io.BytesIO:
    img = Image.open(src_path)
    w, h = img.size
    if w > max_width:
        img = img.resize((max_width, int(h * max_width / w)), Image.Resampling.LANCZOS)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")  # avoid transparency breaking PNG
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf
```

Insert image and caption:

```python
img_io = compress_image("screenshot.png")
p = document.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run().add_picture(img_io, width=Cm(12))

cap = document.add_paragraph()
cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
cap_run = cap.add_run("图 1-1 截图说明")
cap_run.font.size = Pt(10)
```

### Table of Contents (TOC)

python-docx has no built-in TOC API. Use field codes:

```python
def add_toc(document):
    paragraph = document.add_paragraph()
    run = paragraph.add_run()
    fldChar_begin = OxmlElement("w:fldChar")
    fldChar_begin.set(qn("w:fldCharType"), "begin")
    instrText = OxmlElement("w:instrText")
    instrText.set(qn("xml:space"), "preserve")
    instrText.text = 'TOC \\o "1-3" \\h \\z \\u'
    fldChar_sep = OxmlElement("w:fldChar")
    fldChar_sep.set(qn("w:fldCharType"), "separate")
    fldChar_end = OxmlElement("w:fldChar")
    fldChar_end.set(qn("w:fldCharType"), "end")
    run._r.append(fldChar_begin)
    run._r.append(instrText)
    run._r.append(fldChar_sep)
    run._r.append(fldChar_end)
```

User must press F9 in Word to update the TOC field.

### Page Setup (A4)

```python
section = document.sections[0]
section.page_width = Cm(21)
section.page_height = Cm(29.7)
section.top_margin = Cm(2.54)
section.bottom_margin = Cm(2.54)
section.left_margin = Cm(3.17)
section.right_margin = Cm(3.17)
```

## Node.js Docx Pitfalls (Avoid)

If forced to use Node `docx` library, be aware of these fatal pitfalls discovered on docx v9.7.1:

```bash
npm i docx adm-zip fast-xml-parser   # adm-zip / fast-xml-parser 用于下文校验
```

### Pitfall 1: `type` parameter on `ImageRun`

**Must** specify `type: "png"` explicitly. Without it, images get `.undefined` extension in the zip archive, and Word refuses to open the file.

```javascript
// CORRECT
new ImageRun({ data: buffer, transformation: { width, height }, type: "png" })

// BROKEN - missing type
new ImageRun({ data: buffer, transformation: { width, height } })
```

### Pitfall 2: Reusing `ImageRun` instances

Each `ImageRun` object must be inserted exactly **once**. Do not reuse across paragraphs. Reusing causes duplicate `r:embed` refs (2x per image), which breaks the relationship count.

```javascript
// CORRECT - create new instance for each insertion
children.push(new ImageRun({ data: buf, transformation: { width: w, height: h }, type: "png" }));

// BROKEN - reusing the same instance
const img = new ImageRun({ data: buf, transformation: { width: w, height: h }, type: "png" });
children.push(img);
children.push(img);  // duplicate reference!
```

### Pitfall 3: Empty `word/media/` directory entry

Node docx may create an empty `word/media/` zip directory entry. While OOXML allows it, some Word versions reject it. Verify with:

```javascript
const zip = new AdmZip("output.docx");
const hasEmptyDir = zip.getEntries().some(
  e => e.entryName === "word/media/" && e.isDirectory
);
```

### Pitfall 4: `HeadingLevel` is an enum, not a constructor

In docx v9.x, `HeadingLevel` is a static enum. Do not use `new HeadingLevel(...)` in `TableOfContents` options:

```javascript
// CORRECT (v9.x)
new TableOfContents("目录", { hyperlink: true, headingStyleRange: "1-3" })

// BROKEN
new TableOfContents("目录", { stylesWithLevels: [new HeadingLevel({ ... })] })
```

## Validation

### With Word COM Automation (Windows)

The definitive way to verify a docx opens correctly:

```python
import win32com.client as win32
word = win32.Dispatch("Word.Application")
word.Visible = False
try:
    doc = word.Documents.Open(r"./docs/draft/output.docx")
    print(f"Opened: {doc.Paragraphs.Count} paragraphs, {doc.InlineShapes.Count} images")
    doc.Close(SaveChanges=False)
finally:
    word.Quit()
```

### Re-save with Word (Compatibility Fix)

After generating with any library, re-save with Word's `SaveAs2` to normalize the XML:

```python
doc.SaveAs2(r"./docs/draft/output.docx", FileFormat=16)  # wdFormatDocumentDefault
```

### Quick XML Check

At minimum, verify well-formedness:

```javascript
const zip = new AdmZip("output.docx");
const xml = zip.readAsText("word/document.xml");
const parser = new (require("fast-xml-parser").XMLParser)();
try { parser.parse(xml); } catch (e) { /* broken */ }
```

Check for common issues:
- `embed` count must equal `image relationship` count
- No `undefined` or `NaN` in XML
- All `r:embed` IDs must have matching `Target` in `word/_rels/document.xml.rels`

## Image Size Budget

| Scenario | Max width | Expected size per image | 30 images total |
|----------|-----------|------------------------|-----------------|
| Embedded in docx | 800-900 px | 100-400 KB | ~3-12 MB |
| Original screenshots | ~1920 px | 500 KB - 2 MB | ~25-50 MB |

Use `scripts/compress_images.py` to batch-compress before embedding.

## Resources

### scripts/compress_images.py
Batch image compressor. Run standalone to pre-process screenshots before embedding:
```bash
python scripts/compress_images.py <input-dir> <output-dir> --max-width 900
```

### refs/pitfalls.md
Detailed case studies of docx generation failures and their root causes.
