#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PDF 生成与编辑工具箱（生成 / 合并 / 拆分 / 旋转 / 水印 / 加密 / 表单 / 校验）。

生成走 reportlab（含中文 CID 字体与 TrueType 注册），编辑走 pypdf，
校验走 pypdf 读回文本 + PyMuPDF 渲染首页 PNG 目视。

用法：
    python scripts/pdf_ops.py info report.pdf
    python scripts/pdf_ops.py md2pdf doc.md -o out.pdf --title "数据门禁设计说明"
    python scripts/pdf_ops.py merge out.pdf a.pdf b.pdf
    python scripts/pdf_ops.py split in.pdf --out-dir parts --pages 1-3,7
    python scripts/pdf_ops.py rotate in.pdf -o out.pdf --angle 90 --pages 1
    python scripts/pdf_ops.py watermark in.pdf -o out.pdf --text "内部资料"
    python scripts/pdf_ops.py encrypt in.pdf -o out.pdf --password 1234
    python scripts/pdf_ops.py decrypt in.pdf -o out.pdf --password 1234
    python scripts/pdf_ops.py form-fields form.pdf --json
    python scripts/pdf_ops.py fill-form form.pdf data.json -o out.pdf
    python scripts/pdf_ops.py check out.pdf --preview page1.png

为什么不用「Word 另存为 PDF」：命令行/CI 里没有 Word；reportlab + pypdf 纯 Python，
可复现、可 diff、无 GUI 依赖。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

CJK_FONT_NAME = "STSong-Light"          # reportlab 内置 CID 字体，免字体文件
MARGIN = 20 * 28.35 / 25.4              # 20mm，reportlab 单位是 pt


# ---------------------------------------------------------------- 字体
def register_cjk(font_path=None):
    """注册中文字体：默认用 reportlab 内置 STSong-Light（CID）；给了 ttf/otf 就用它。"""
    from reportlab.pdfbase import pdfmetrics
    if font_path:
        from reportlab.pdfbase.ttfonts import TTFont
        pdfmetrics.registerFont(TTFont("CJK", font_path))
        return "CJK"
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    pdfmetrics.registerFont(UnicodeCIDFont(CJK_FONT_NAME))
    return CJK_FONT_NAME


# ---------------------------------------------------------------- Markdown → PDF
def _styles(font):
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    base = dict(fontName=font, wordWrap="CJK", leading=18)
    return {
        "h1": ParagraphStyle("h1", fontSize=20, spaceAfter=14, spaceBefore=10,
                             alignment=TA_CENTER, **base),
        "h2": ParagraphStyle("h2", fontSize=15, spaceBefore=12, spaceAfter=8, **base),
        "h3": ParagraphStyle("h3", fontSize=13, spaceBefore=10, spaceAfter=6, **base),
        "body": ParagraphStyle("body", fontSize=11, spaceAfter=6, firstLineIndent=0, **base),
        "bullet": ParagraphStyle("bullet", fontSize=11, leftIndent=16, bulletIndent=6,
                                 spaceAfter=4, **base),
        "code": ParagraphStyle("code", fontSize=9, leftIndent=12,
                               backColor="#f5f5f5", **base),
    }


def _cells_ok(line):
    return line.strip().startswith("|") and line.strip().endswith("|")


def _split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def md_to_flowables(md, font):
    """Markdown 子集 → flowables：标题、段落、无序/有序列表、表格、围栏代码、分隔线。"""
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Preformatted
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    st = _styles(font)
    flow, lines, i = [], md.splitlines(), 0
    while i < len(lines):
        line = lines[i]
        raw = line.rstrip()
        stripped = raw.strip()
        if stripped.startswith("```"):                     # 代码块
            buf = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            flow.append(Preformatted("\n".join(buf), st["code"]))
            flow.append(Spacer(1, 8))
            continue
        if _cells_ok(raw) and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            rows, widths = [], None
            while i < len(lines) and _cells_ok(lines[i]):
                if not re.match(r"^\|[\s:|-]+\|$", lines[i].strip()):
                    rows.append(_split_row(lines[i]))
                i += 1
            cols = max(len(r) for r in rows)
            rows = [r + [""] * (cols - len(r)) for r in rows]
            table = Table(rows, repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#999999")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            flow.append(table)
            flow.append(Spacer(1, 10))
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            level = min(len(m.group(1)), 3)
            flow.append(Paragraph(_inline(m.group(2)), st["h%d" % level]))
            i += 1
            continue
        if re.match(r"^[-*+]\s+", stripped):
            flow.append(Paragraph(_inline(re.sub(r"^[-*+]\s+", "", stripped)),
                                  st["bullet"], bulletText="•"))
            i += 1
            continue
        if re.match(r"^\d+[.)]\s+", stripped):
            num = re.match(r"^(\d+)[.)]\s+", stripped).group(1)
            flow.append(Paragraph(_inline(stripped.split(".", 1)[-1].split(")", 1)[-1].strip()),
                                  st["bullet"], bulletText="%s." % num))
            i += 1
            continue
        if re.match(r"^([-*_])\1{2,}$", stripped):
            flow.append(Spacer(1, 10))
            i += 1
            continue
        if not stripped:
            flow.append(Spacer(1, 6))
            i += 1
            continue
        flow.append(Paragraph(_inline(stripped), st["body"]))
        i += 1
    return flow


def _inline(text):
    """行内 Markdown → reportlab 迷你标记；先转义 & < >，再处理 **粗体** `代码`"""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r"<font face='Courier'>\1</font>", text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1（\2）", text)
    return text


def cmd_md2pdf(args):
    from reportlab.lib.pagesizes import A4, LETTER
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER

    font = register_cjk(args.font)
    with open(args.input, encoding="utf-8") as f:
        md = f.read()
    title = args.title or _first_heading(md) or os.path.splitext(os.path.basename(args.input))[0]

    def _decorate(canvas, doc):
        canvas.saveState()
        canvas.setFont(font, 9)
        canvas.drawCentredString(size[0] / 2, 12 * mm, "第 %d 页" % doc.page)
        canvas.drawString(args.margin * mm, size[1] - 12 * mm, title)
        canvas.restoreState()

    size = A4 if args.page == "A4" else LETTER
    doc = SimpleDocTemplate(args.output, pagesize=size, title=title,
                            author=args.author, leftMargin=args.margin * mm,
                            rightMargin=args.margin * mm, topMargin=18 * mm,
                            bottomMargin=18 * mm)
    flow = []
    if args.title:
        flow.append(Paragraph(_inline(args.title),
                              ParagraphStyle("t", fontName=font, fontSize=22,
                                             alignment=TA_CENTER, spaceAfter=18)))
    flow += md_to_flowables(md, font)
    doc.build(flow, onFirstPage=_decorate, onLaterPages=_decorate)
    return args.output


def _first_heading(md):
    for line in md.splitlines():
        m = re.match(r"^#{1,3}\s+(.+)$", line.strip())
        if m:
            return m.group(1).strip()
    return ""


# ---------------------------------------------------------------- pypdf 编辑
def _reader(path, password=""):
    from pypdf import PdfReader
    reader = PdfReader(path)
    if reader.is_encrypted:
        if not password:
            raise SystemExit("该 PDF 已加密，需要 --password")
        reader.decrypt(password)
    return reader


def _parse_pages(spec, total):
    """'1-3,7' → [0,1,2,6]（1-based、含端点）"""
    if not spec:
        return list(range(total))
    out = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            out += list(range(int(a) - 1, int(b)))
        else:
            out.append(int(part) - 1)
    return [i for i in out if 0 <= i < total]


def cmd_info(args):
    reader = _reader(args.input, args.password)
    info = {
        "file": os.path.abspath(args.input),
        "pages": len(reader.pages),
        "encrypted": reader.is_encrypted,
        "metadata": {k: str(v) for k, v in (reader.metadata or {}).items()},
        "page_sizes_pt": [[round(float(p.mediabox.width), 1), round(float(p.mediabox.height), 1)]
                          for p in reader.pages[:3]],
        "form_fields": len(reader.get_fields() or {}),
    }
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return None


def cmd_merge(args):
    writer = _writer()
    for path in args.inputs:
        writer.append(path)
    return _save(writer, args.output)


def _writer():
    from pypdf import PdfWriter
    return PdfWriter()


def _save(writer, output):
    os.makedirs(os.path.dirname(os.path.abspath(output)) or ".", exist_ok=True)
    with open(output, "wb") as f:
        writer.write(f)
    return output


def cmd_split(args):
    reader = _reader(args.input, args.password)
    writer = _writer()
    for idx in _parse_pages(args.pages, len(reader.pages)):
        writer.add_page(reader.pages[idx])
    output = args.output or os.path.join(
        args.out_dir, os.path.splitext(os.path.basename(args.input))[0] + "-part.pdf")
    return _save(writer, output)


def cmd_rotate(args):
    reader = _reader(args.input, args.password)
    writer = _writer()
    targets = set(_parse_pages(args.pages, len(reader.pages)))
    for idx, page in enumerate(reader.pages):
        if idx in targets:
            page.rotate(args.angle)
        writer.add_page(page)
    return _save(writer, args.output)


def _watermark_pdf(width, height, text, font, gray, size):
    """生成与目标页同尺寸的水印层（尺寸不一致时 merge_page 会被裁切）"""
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import Color
    import io
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))
    c.saveState()
    c.setFont(font, size)
    c.setFillColor(Color(gray, gray, gray, alpha=0.35))
    c.translate(width / 2, height / 2)
    c.rotate(35)
    c.drawCentredString(0, 0, text)
    c.restoreState()
    c.save()
    buf.seek(0)
    return buf


def cmd_watermark(args):
    """合并水印层。pypdf ≥7 要求页面先挂到 writer 上才能 merge_page，故两段式。"""
    from pypdf import PdfReader
    reader = _reader(args.input, args.password)
    writer = _writer()
    font = register_cjk(args.font)
    for page in reader.pages:
        writer.add_page(page)
    for page in writer.pages:
        box = page.mediabox
        wm = PdfReader(_watermark_pdf(float(box.width), float(box.height), args.text,
                                      font, args.gray, args.size)).pages[0]
        page.merge_page(wm, over=True)
    return _save(writer, args.output)


def cmd_encrypt(args):
    reader = _reader(args.input, args.password)
    writer = _writer()
    writer.append(reader)
    writer.encrypt(user_password=args.password,
                   owner_password=args.owner or args.password,
                   algorithm="AES-128")
    return _save(writer, args.output)


def cmd_decrypt(args):
    reader = _reader(args.input, args.password)
    writer = _writer()
    for page in reader.pages:
        writer.add_page(page)
    return _save(writer, args.output)


def cmd_form_fields(args):
    reader = _reader(args.input, args.password)
    fields = reader.get_fields() or {}
    out = {name: {"type": str(f.get("/FT", "")), "value": str(f.get("/V", "")),
                  "required": bool(f.get("/Ff", 0) & 2)}
           for name, f in fields.items()}
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        for name, meta in out.items():
            print("%-28s %-8s 当前值=%-16s %s" % (name, meta["type"], meta["value"] or "-",
                                                 "必填" if meta["required"] else ""))
    return None


def cmd_fill_form(args):
    """填写 AcroForm。注意 pypdf 只能填「已有表单域」的 PDF，不能凭空造表单。"""
    reader = _reader(args.input, args.password)
    with open(args.data, encoding="utf-8") as f:
        data = json.load(f)
    known = set((reader.get_fields() or {}).keys())
    unknown = [k for k in data if k not in known]
    if unknown:
        raise SystemExit("表单里没有这些域：%s（现有域：%s）"
                         % (", ".join(unknown), ", ".join(sorted(known)) or "无"))
    writer = _writer()
    writer.append(reader)
    for page in writer.pages:
        writer.update_page_form_field_values(page, data, auto_regenerate=False)
    if args.flatten:
        try:
            writer.set_need_appearances_writer(False)
        except Exception:
            pass
    return _save(writer, args.output)


def cmd_check(args):
    """交付前自检：页数、每页字符数、可选渲首页 PNG 目视。"""
    reader = _reader(args.input, args.password)
    per_page = []
    for idx, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or "").strip()
        per_page.append({"page": idx, "chars": len(text)})
    empty = [p["page"] for p in per_page if p["chars"] < 10]
    result = {"file": args.input, "pages": len(per_page),
              "text_chars": sum(p["chars"] for p in per_page),
              "near_empty_pages": empty,
              "verdict": "ok" if not empty else "warning"}
    if args.preview:
        try:
            import pymupdf
            doc = pymupdf.open(args.input)
            doc[0].get_pixmap(dpi=110).save(args.preview)
            result["preview"] = args.preview
            doc.close()
        except Exception as exc:
            result["preview_error"] = str(exc)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return None


# ---------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description="PDF 生成与编辑工具箱",
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, out="required"):
        p.add_argument("input")
        p.add_argument("--password", default="", help="已加密 PDF 的打开密码")
        if out == "required":
            p.add_argument("-o", "--output", required=True, help="输出 PDF 路径")
        elif out == "optional":
            p.add_argument("-o", "--output", default="", help="输出 PDF 路径")

    p = sub.add_parser("info", help="读页数/元数据/表单域数量"); common(p, out=False)
    p.set_defaults(fn=cmd_info)

    p = sub.add_parser("md2pdf", help="Markdown → PDF（中文、表格、代码块、页码）"); common(p)
    p.add_argument("--title", default="", help="封面标题 + 页眉")
    p.add_argument("--author", default="")
    p.add_argument("--page", choices=("A4", "letter"), default="A4")
    p.add_argument("--margin", type=float, default=20, help="左右页边距(mm)，默认 20")
    p.add_argument("--font", default="", help="中文 ttf/otf 路径，默认内置 STSong-Light")
    p.set_defaults(fn=cmd_md2pdf)

    p = sub.add_parser("merge", help="按顺序合并多个 PDF")
    p.add_argument("inputs", nargs="+")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(fn=cmd_merge)

    p = sub.add_parser("split", help="抽取页码范围"); common(p, out="optional")
    p.add_argument("--pages", default="", help="如 1-3,7；默认整份复制")
    p.add_argument("--out-dir", default=".", help="未给 -o 时的输出目录")
    p.set_defaults(fn=cmd_split)

    p = sub.add_parser("rotate", help="旋转指定页"); common(p)
    p.add_argument("--angle", type=int, default=90, choices=(90, 180, 270))
    p.add_argument("--pages", default="", help="默认全部页")
    p.set_defaults(fn=cmd_rotate)

    p = sub.add_parser("watermark", help="加斜向文字水印"); common(p)
    p.add_argument("--text", default="内部资料")
    p.add_argument("--gray", type=float, default=0.5)
    p.add_argument("--size", type=int, default=40)
    p.add_argument("--font", default="")
    p.set_defaults(fn=cmd_watermark)

    p = sub.add_parser("encrypt", help="AES-128 加密"); common(p)
    p.add_argument("--owner", default="", help="所有者密码，默认同用户密码")
    p.set_defaults(fn=cmd_encrypt)

    p = sub.add_parser("decrypt", help="去密码"); common(p)
    p.set_defaults(fn=cmd_decrypt)

    p = sub.add_parser("form-fields", help="列出 AcroForm 表单域"); common(p, out=False)
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_form_fields)

    p = sub.add_parser("fill-form", help="按 JSON 填写表单域"); common(p)
    p.add_argument("data", help="JSON 文件：{域名: 值}")
    p.add_argument("--flatten", action="store_true", help="关闭域外观重生成（近似扁平化）")
    p.set_defaults(fn=cmd_fill_form)

    p = sub.add_parser("check", help="交付自检：页数/字符数/空页/首页预览"); common(p, out=False)
    p.add_argument("--preview", default="", help="渲染首页为该 PNG 路径")
    p.set_defaults(fn=cmd_check)

    args = ap.parse_args(argv)
    result = args.fn(args)
    if result:
        print("已生成 %s" % result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
