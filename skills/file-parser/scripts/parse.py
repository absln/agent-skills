#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一文档解析入口：任意格式 → 结构化 Markdown + 元数据 + 置信度。

三级 fallback（吸收自 doc-parse 技能），每级失败自动降级，并在结果里如实标注
`fallback_used` / `confidence` / `warnings`，不输出“假装成功”的空结果。

    PDF   : mineru → pymupdf → pdfplumber → 渲染成图后 OCR
    旧格式: anydoc(npx) → LibreOffice 转换 → 报错（BLOCKED）
    原生  : docx(python-docx) / pptx(python-pptx) / xlsx(openpyxl)
    图片  : ocr.py（Windows 内置 OCR → pytesseract）

用法：
    python scripts/parse.py report.pdf                       # 打印 markdown
    python scripts/parse.py docs/refs/ --out docs/temp --json # 批量 + 落 JSON
    python scripts/parse.py scan.pdf --ocr-scale 4 --no-cache
    python scripts/parse.py --engine-list                    # 看 OCR 引擎

产物（--out 指定，默认 docs/temp）：
    {stem}.md    markdown 正文
    {stem}.json  完整契约：markdown / metadata / confidence / fallback_used / blocks / warnings / status
    {stem}.md5   MD5 缓存校验；同名同 MD5 直接复用，不重复解析
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ocr as ocr_mod  # noqa: E402

# 解析器档位 → 基础置信度（细则见 refs/fallback-and-confidence.md）
TIER_BASE = {
    "mineru": 0.95, "pymupdf": 0.88, "pdfplumber": 0.82, "docx": 0.92,
    "pptx": 0.90, "xlsx": 0.92, "text": 0.98, "anydoc": 0.85,
    "libreoffice": 0.75, "image-ocr": 0.62, "pdf-ocr": 0.60,
}
IMG_EXT = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp")
TEXT_EXT = {".md": "text", ".markdown": "text", ".txt": "text", ".csv": "text",
            ".json": "text", ".yaml": "text", ".yml": "text", ".html": "text",
            ".htm": "text", ".xml": "text"}
LEGACY_EXT = (".doc", ".ppt", ".xls", ".odt", ".odp", ".ods", ".rtf", ".epub",
              ".docm", ".pptm", ".pps", ".ppsx", ".xlsm", ".xlsb", ".wps")
MIN_COVERAGE_CHARS = 30   # 每页低于这个字符数按“扫描页”处理


# ---------------------------------------------------------------- 通用工具
def md5_of(path, chunk=1 << 20):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _cell(value):
    """表格单元格 → 安全的 Markdown 单元格文本"""
    if value is None:
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text.replace("|", "\\|")


def table_to_md(rows):
    """二维数组 → Markdown 表格；列数取众数，超出的列丢弃并返回告警"""
    rows = [[_cell(c) for c in row] for row in rows if row]
    rows = [r for r in rows if any(r)]
    if not rows:
        return "", "空表格"
    width = max(set(len(r) for r in rows), key=lambda n: sum(len(r) == n for r in rows))
    warn = ""
    if any(len(r) != width for r in rows):
        warn = "表格存在合并单元格或列数不一致，已按众数 %d 列对齐" % width
    body = [r[:width] + [""] * (width - len(r)) for r in rows]
    head, rest = body[0], body[1:]
    out = ["| " + " | ".join(head) + " |",
           "| " + " | ".join(["---"] * width) + " |"]
    out += ["| " + " | ".join(r) + " |" for r in rest]
    return "\n".join(out), warn


def _heading(level, text):
    return "%s %s" % ("#" * max(1, min(6, level)), text.strip())


def _blocks_chars(blocks):
    return sum(b.get("chars", 0) for b in blocks)


# ---------------------------------------------------------------- docx
DOCX_STYLE = {"Title": 1, "Heading 1": 1, "Heading 2": 2, "Heading 3": 3,
              "Heading 4": 4, "Heading 5": 5, "Subtitle": 2,
              "标题 1": 1, "标题 2": 2, "标题 3": 3, "标题 4": 4}


def parse_docx(path):
    import docx
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    doc = docx.Document(path)
    out, warnings, tables, images = [], [], 0, []
    body = doc.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            para = Paragraph(child, doc)
            text = para.text.strip()
            if not text:
                continue
            style = para.style.name if para.style is not None else ""
            level = DOCX_STYLE.get(style)
            if level:
                out.append(_heading(level, text))
            elif style in ("List Bullet", "List Number", "列表段落"):
                out.append("- " + text)
            elif para._p.findall(".//" + qn("w:drawing")):
                images.append(len(images) + 1)     # 图片段落，文本另一路 OCR
            else:
                out.append(text)
        elif child.tag == qn("w:tbl"):
            tables += 1
            rows = [[c.text for c in row.cells] for row in Table(child, doc).rows]
            md, warn = table_to_md(rows)
            if warn:
                warnings.append(warn)
            out.append(md)
    meta = {"format": "docx", "tables": tables}
    core = doc.core_properties
    if core.title:
        meta["title"] = core.title
    if core.author:
        meta["author"] = core.author
    if core.created:
        meta["created"] = core.created.isoformat()
    return "\n\n".join(x for x in out if x), meta, warnings


# ---------------------------------------------------------------- pptx
def parse_pptx(path):
    from pptx import Presentation
    prs = Presentation(path)
    out, warnings, tables, pics = [], [], 0, 0
    for idx, slide in enumerate(prs.slides, 1):
        lines = ["## 幻灯片 %d" % idx]
        for shape in slide.shapes:
            if shape.has_text_frame:
                text = "\n".join(p.text for p in shape.text_frame.paragraphs).strip()
                if text:
                    lines.append(text)
            elif shape.has_table:
                tables += 1
                rows = [[c.text for c in row.cells] for row in shape.table.rows]
                md, warn = table_to_md(rows)
                if warn:
                    warnings.append("幻灯片 %d: %s" % (idx, warn))
                lines.append(md)
            elif shape.shape_type == 13:           # PICTURE
                pics += 1
        if len(lines) == 1:
            lines.append("（本页无可提取文本，可能是整页图片）")
        out.append("\n\n".join(lines))
    return "\n\n".join(out), {"format": "pptx", "pages": len(prs.slides),
                              "tables": tables, "images": pics}, warnings


# ---------------------------------------------------------------- xlsx
def parse_xlsx(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    out, warnings = [], []
    for ws in wb.worksheets:
        out.append("## %s" % ws.title)
        rows = []
        for row in ws.iter_rows(values_only=True):
            if all(c is None or str(c).strip() == "" for c in row):
                continue
            rows.append(["" if c is None else c for c in row])
        if not rows:
            out.append("（空表）")
            continue
        md, warn = table_to_md(rows)
        if warn:
            warnings.append("%s: %s" % (ws.title, warn))
        out.append(md)
    return "\n\n".join(out), {"format": "xlsx", "sheets": len(wb.worksheets)}, warnings


# ---------------------------------------------------------------- PDF 三级 fallback
def _try_mineru(path, timeout=600):
    """MinerU：强排版还原，需本机已装 `mineru`（或旧名 magic-pdf）CLI。缺失即跳过。"""
    exe = shutil.which("mineru") or shutil.which("magic-pdf")
    if not exe:
        raise RuntimeError("未安装 mineru CLI（pip install -U \"magic-pdf[full]\"）")
    tmpdir = tempfile.mkdtemp(prefix="mineru-")
    try:
        cmd = ([exe, "-p", path, "-o", tmpdir] if os.path.basename(exe) == "mineru"
               else [exe, "-p", path, "-o", tmpdir, "-m", "auto"])
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0:
            raise RuntimeError("mineru 退出码 %d: %s" % (proc.returncode, proc.stderr[-300:]))
        found = []
        for root, _dirs, files in os.walk(tmpdir):
            found += [os.path.join(root, f) for f in files if f.lower().endswith(".md")]
        if not found:
            raise RuntimeError("mineru 未产出 markdown")
        with open(max(found, key=os.path.getsize), encoding="utf-8") as f:
            return f.read()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _pdf_meta(doc, extra=None):
    meta = {"format": "pdf", "pages": doc.page_count}
    info = doc.metadata or {}
    for key, name in (("title", "title"), ("author", "author"),
                      ("creationDate", "created"), ("modDate", "modified")):
        value = str(info.get(key) or "").strip()
        if value and value.lower() not in ("untitled", "无标题", "none", "anonymous"):
            meta[name] = value
    if extra:
        meta.update(extra)
    return meta


def _try_pymupdf(path):
    """PyMuPDF：快，文本层还原好；每页字符数过低则整篇视为扫描件，交下一档。"""
    import pymupdf
    doc = pymupdf.open(path)
    try:
        pages, blocks, chars = [], [], 0
        for idx, page in enumerate(doc, 1):
            text = page.get_text("text").strip()
            chars += len(text)
            blocks.append({"page": idx, "type": "text", "chars": len(text)})
            pages.append("## 第 %d 页\n\n%s" % (idx, text) if text else "")
        if chars < MIN_COVERAGE_CHARS * doc.page_count:
            raise RuntimeError("文本层过薄（%d 字符 / %d 页），判定为扫描件"
                               % (chars, doc.page_count))
        return "\n\n".join(p for p in pages if p), _pdf_meta(doc), blocks, []
    finally:
        doc.close()


def _try_pdfplumber(path):
    """pdfplumber：兜底，顺带抽表格（PyMuPDF 抓不到表格线）。"""
    import pdfplumber
    out, blocks, warnings, tables = [], [], [], 0
    with pdfplumber.open(path) as pdf:
        for idx, page in enumerate(pdf.pages, 1):
            text = (page.extract_text() or "").strip()
            lines = ["## 第 %d 页" % idx]
            if text:
                lines.append(text)
            for rows in page.extract_tables() or []:
                tables += 1
                md, warn = table_to_md(rows)
                if warn:
                    warnings.append("第 %d 页: %s" % (idx, warn))
                lines.append(md)
            blocks.append({"page": idx, "type": "text", "chars": len(text)})
            out.append("\n\n".join(lines))
        meta = {"format": "pdf", "pages": len(pdf.pages), "tables": tables}
        chars = sum(b["chars"] for b in blocks)
        if chars < MIN_COVERAGE_CHARS * len(pdf.pages):
            raise RuntimeError("pdfplumber 文本层过薄（%d 字符 / %d 页），交给 OCR 档"
                               % (chars, len(pdf.pages)))
    return "\n\n".join(out), meta, blocks, warnings


def _try_pdf_ocr(path, scale=2.0, lang=""):
    """最后一档：逐页渲染成图再 OCR。无需 poppler（用 PyMuPDF 渲染）。"""
    import pymupdf
    doc = pymupdf.open(path)
    tmpdir = tempfile.mkdtemp(prefix="pdfocr-")
    out, blocks, warnings = [], [], []
    try:
        for idx, page in enumerate(doc, 1):
            png = os.path.join(tmpdir, "p%04d.png" % idx)
            page.get_pixmap(dpi=int(150 * scale)).save(png)
            try:
                text = "\n".join(ocr_mod.ocr_lines(png, lang=lang))
            except Exception as exc:
                text, _ = "", warnings.append("第 %d 页 OCR 失败: %s" % (idx, exc))
            blocks.append({"page": idx, "type": "ocr", "chars": len(text)})
            out.append("## 第 %d 页\n\n%s" % (idx, text) if text else "")
        return "\n\n".join(x for x in out if x), _pdf_meta(doc), blocks, warnings
    finally:
        doc.close()
        shutil.rmtree(tmpdir, ignore_errors=True)


def parse_pdf(path, mineru="auto", lang="", ocr_scale=2.0):
    """返回 (markdown, meta, blocks, warnings, tier, attempts)；全档失败抛 RuntimeError。

    attempts 记录每一档失败原因（降级轨迹），warnings 只记内容层面问题，
    两者分开，避免「降级」被当成「内容有缺陷」重复扣分。
    """
    errors = []
    chain = []
    if mineru != "off":
        chain.append(("mineru", lambda: (_try_mineru(path), "mineru")))
    chain += [("pymupdf", lambda: (_try_pymupdf(path), "pymupdf")),
              ("pdfplumber", lambda: (_try_pdfplumber(path), "pdfplumber")),
              ("pdf-ocr", lambda: (_try_pdf_ocr(path, ocr_scale, lang), "pdf-ocr"))]
    for name, fn in chain:
        try:
            result, tier = fn()
            md = result[0] if isinstance(result, tuple) else result
            if not (md or "").strip():
                raise RuntimeError("产出为空")
            if tier == "mineru":            # CLI 只回 markdown，补元数据
                import pymupdf
                doc = pymupdf.open(path)
                try:
                    meta, blocks = _pdf_meta(doc), [{"page": i + 1, "type": "mineru",
                                                     "chars": None}
                                                    for i in range(doc.page_count)]
                finally:
                    doc.close()
                return md, meta, blocks, list(result[3]), tier, errors
            return result[0], result[1], result[2], list(result[3]), tier, errors
        except Exception as exc:
            errors.append("%s: %s" % (name, exc))
    raise RuntimeError("PDF 四档解析全部失败 → " + " | ".join(errors))


# ---------------------------------------------------------------- 图片 / 旧格式 / 纯文本
def parse_image(path, lang="", scale=1.0):
    lines = ocr_mod.ocr_lines(path, lang=lang, scale=scale)
    md = "\n".join(lines)
    meta = {"format": os.path.splitext(path)[1].lstrip(".").lower(), "pages": 1}
    return md, meta, [{"page": 1, "type": "ocr", "chars": len(md)}], []


def parse_legacy(path):
    """旧二进制格式：anydoc(npx，免安装) → LibreOffice --headless 转换。"""
    anydoc = shutil.which("anydoc") or shutil.which("npx")
    if anydoc:
        cmd = ([anydoc, path] if os.path.basename(anydoc) == "anydoc"
               else [anydoc, "-y", "@firecrawl/anydoc", path])
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout, {"format": os.path.splitext(path)[1].lstrip(".")}, [], []
        if proc.returncode == 3:
            raise RuntimeError("anydoc: 该文档需要 OCR（扫描件），请先转成 PDF 走 PDF 链路")
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice:
        tmpdir = tempfile.mkdtemp(prefix="lo-")
        try:
            subprocess.run([soffice, "--headless", "--convert-to", "docx",
                            "--outdir", tmpdir, path],
                           capture_output=True, timeout=600, check=True)
            target = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir)
                      if f.lower().endswith(".docx")]
            if target:
                md, meta, warnings = parse_docx(target[0])
                return md, meta, [], warnings
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        raise RuntimeError("LibreOffice 转换后无产出")
    raise RuntimeError("旧格式需要 anydoc（npx -y @firecrawl/anydoc）或 LibreOffice；"
                       "建议先把文件另存为 .docx/.pptx/.xlsx")


def parse_text(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read(), {"format": os.path.splitext(path)[1].lstrip(".")}, [], []


# ---------------------------------------------------------------- 置信度
def score(blocks, tier, warnings, page_count, min_chars=None):
    """置信度 = 档位基础分 − 覆盖惩罚 − 告警惩罚 − OCR 惩罚（细则见 refs）"""
    base = TIER_BASE.get(tier, 0.70)
    min_chars = MIN_COVERAGE_CHARS if min_chars is None else min_chars
    pages = max(1, page_count or len(blocks) or 1)
    low = sum(1 for b in blocks if b.get("chars") is not None and b["chars"] < min_chars)
    cover = low / pages
    factors = {"tier_base": base, "pages": pages,
               "low_coverage_ratio": round(cover, 3)}
    conf = base - 0.30 * cover - 0.02 * min(len(warnings), 5)
    if tier.endswith("ocr"):
        conf -= 0.08
    conf = round(max(0.05, min(0.99, conf)), 2)
    factors["final"] = conf
    status = "ok" if conf >= 0.75 else ("degraded" if conf >= 0.5 else "blocked")
    return conf, status, factors


def _office_media_ocr(path, lang="", scale=2.0):
    """docx/pptx 内嵌图片 OCR：直接从 zip 里取 word/media、ppt/media 下的图。"""
    out = []
    try:
        with zipfile.ZipFile(path) as zf:
            names = [n for n in zf.namelist()
                     if re.search(r"/(media|embeddings)/", n)
                     and n.lower().endswith(IMG_EXT)]
            if not names:
                return []
            tmpdir = tempfile.mkdtemp(prefix="media-")
            try:
                for idx, name in enumerate(sorted(names), 1):
                    target = os.path.join(tmpdir, "img%03d%s" % (idx, os.path.splitext(name)[1]))
                    with open(target, "wb") as f:
                        f.write(zf.read(name))
                    try:
                        text = "\n".join(ocr_mod.ocr_lines(target, lang=lang, scale=scale))
                    except Exception as exc:
                        out.append("=== 图片%03d（%s）OCR 不可用: %s ===" % (idx, name, exc))
                        continue
                    if text.strip():
                        out.append("=== 图片%03d（%s）OCR ===\n%s" % (idx, name, text))
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
    except zipfile.BadZipFile:
        return []
    return out


# ---------------------------------------------------------------- 调度
def parse_file(path, args):
    """单文件解析 → 契约 dict（markdown/metadata/confidence/fallback_used/blocks/...）"""
    ext = os.path.splitext(path)[1].lower()
    warnings, blocks = [], []
    attempts = []
    if ext == ".pdf":
        md, meta, blocks, warnings, tier, attempts = parse_pdf(
            path, args.mineru, args.lang, args.ocr_scale)
    elif ext == ".docx":
        md, meta, warnings = parse_docx(path)
        tier = "docx"
        if args.ocr_images != "off":
            md = "\n\n".join(x for x in [md] + _office_media_ocr(path, args.lang, args.ocr_scale) if x)
    elif ext == ".pptx":
        md, meta, warnings = parse_pptx(path)
        tier = "pptx"
        if args.ocr_images != "off":
            md = "\n\n".join(x for x in [md] + _office_media_ocr(path, args.lang, args.ocr_scale) if x)
    elif ext == ".xlsx":
        md, meta, warnings = parse_xlsx(path)
        tier = "xlsx"
    elif ext in IMG_EXT:
        md, meta, blocks, warnings = parse_image(path, args.lang, args.ocr_scale)
        tier = "image-ocr"
    elif ext in LEGACY_EXT:
        md, meta, blocks, warnings = parse_legacy(path)
        tier = "anydoc" if shutil.which("anydoc") or shutil.which("npx") else "libreoffice"
    elif ext in TEXT_EXT:
        md, meta, blocks, warnings = parse_text(path)
        tier = "text"
    else:
        raise RuntimeError("不支持的扩展名 %s" % ext)

    pages = meta.get("pages") or len([b for b in blocks if b.get("type") in ("text", "ocr")]) or 1
    if tier == "image-ocr":
        min_chars = 5                     # 单图截图常常只有一行字
    elif tier.endswith("ocr"):
        min_chars = 10                    # OCR 页：低于 10 字符视为近空白页
    else:
        min_chars = MIN_COVERAGE_CHARS
    conf, status, factors = score(blocks, tier, warnings, pages, min_chars)
    meta.setdefault("chars", len(md))
    meta.setdefault("title", _guess_title(md) or os.path.basename(path))
    return {
        "source": os.path.abspath(path),
        "format": meta.get("format", ext.lstrip(".")),
        "markdown": md,
        "metadata": meta,
        "confidence": conf,
        "confidence_factors": factors,
        "fallback_used": tier,
        "fallback_attempts": attempts,
        "status": status,
        "blocks": blocks,
        "warnings": warnings,
    }


PAGE_TITLE = re.compile(r"^(第\s*\d+\s*页|幻灯片\s*\d+|page\s*\d+|slide\s*\d+)$", re.I)


def _guess_title(md):
    """取第一个像样的标题；页码/幻灯片占位标题不算标题。"""
    for line in md.splitlines():
        m = re.match(r"^#{1,2}\s+(.{2,80})$", line.strip())
        if m and not PAGE_TITLE.match(m.group(1).strip()):
            return m.group(1).strip()
    return ""


def _iter_inputs(paths):
    for p in paths:
        if os.path.isdir(p):
            for name in sorted(os.listdir(p)):
                full = os.path.join(p, name)
                if os.path.isfile(full) and not name.startswith("."):
                    yield full
        elif os.path.isfile(p):
            yield p
        else:
            print("ERR: 找不到 %s" % p, file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="多格式文档 → 结构化 Markdown + 元数据 + 置信度（三级 fallback）",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="*", help="文件或目录（可多个）")
    ap.add_argument("--out", default="docs/temp", help="产物目录，默认 docs/temp")
    ap.add_argument("--json", action="store_true", help="同时落 {stem}.json 契约文件")
    ap.add_argument("--mineru", choices=("auto", "off"), default="auto",
                    help="PDF 首选 MinerU，未安装会自动跳过")
    ap.add_argument("--ocr-images", choices=("auto", "off"), default="auto",
                    help="docx/pptx 内嵌图片是否 OCR")
    ap.add_argument("--lang", default="", help="OCR 语言，默认优先中文引擎")
    ap.add_argument("--ocr-scale", type=float, default=2.0, help="OCR 前放大倍数，默认 2")
    ap.add_argument("--no-cache", action="store_true", help="忽略 MD5 缓存，强制重解析")
    ap.add_argument("--engine-list", action="store_true", help="列出可用 OCR 引擎后退出")
    args = ap.parse_args(argv)

    if args.engine_list:
        return ocr_mod.main(["--list"])
    inputs = list(_iter_inputs(args.inputs))
    if not inputs:
        print("没有可处理的文件", file=sys.stderr)
        return 2

    os.makedirs(args.out, exist_ok=True)
    stems = [os.path.splitext(os.path.basename(x))[0] for x in inputs]
    dup = {x for x in stems if stems.count(x) > 1}     # 同名不同扩展名 → 带上扩展名防止覆盖
    failed = 0
    for path in inputs:
        stem = os.path.splitext(os.path.basename(path))[0]
        if stem in dup:
            stem += "." + os.path.splitext(path)[1].lstrip(".").lower()
        md5, md5_file = md5_of(path), os.path.join(args.out, stem + ".md5")
        json_file = os.path.join(args.out, stem + ".json")
        if not args.no_cache and os.path.exists(md5_file) and os.path.exists(json_file):
            if open(md5_file, encoding="utf-8").read().strip() == md5:
                print("[cache] %s → %s" % (path, json_file))
                continue
        try:
            record = parse_file(path, args)
        except Exception as exc:                       # 全部档位失败：如实标记 BLOCKED
            failed += 1
            print("[BLOCKED] %s: %s" % (path, exc), file=sys.stderr)
            record = {"source": os.path.abspath(path), "status": "blocked",
                      "markdown": "", "confidence": 0.0, "fallback_used": None,
                      "error": str(exc), "warnings": ["全部解析档位失败，需人工介入"]}
        record["md5"] = md5
        with open(os.path.join(args.out, stem + ".md"), "w", encoding="utf-8") as f:
            f.write(record.get("markdown", ""))
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        with open(md5_file, "w", encoding="utf-8") as f:
            f.write(md5)
        if args.inputs and len(inputs) == 1 and not args.json:
            print(record.get("markdown", ""))
        print("[%s] %s → %s.md (conf %.2f, parser=%s, %d 字符)" % (
            record["status"], path, stem, record.get("confidence", 0),
            record.get("fallback_used"), len(record.get("markdown", ""))),
            file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
