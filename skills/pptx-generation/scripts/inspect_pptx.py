#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pptx 结构检查 / 质检工具。

    python inspect_pptx.py deck.pptx              # 概览 + 质检
    python inspect_pptx.py deck.pptx --text       # 逐页文本
    python inspect_pptx.py deck.pptx --fonts      # 字体统计
    python inspect_pptx.py deck.pptx --json       # 机读输出

依赖 python-pptx。质检项见 refs/pitfalls.md。
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from pptx import Presentation
from pptx.oxml.ns import qn

EMU = 914400


def walk(shapes):
    for sh in shapes:
        yield sh
        if sh.shape_type == 6 and hasattr(sh, "shapes"):     # GROUP
            yield from walk(sh.shapes)


def analyze(path):
    prs = Presentation(path)
    W, H = prs.slide_width / EMU, prs.slide_height / EMU
    slides, issues, fonts = [], [], Counter()

    for si, s in enumerate(prs.slides, 1):
        texts, chars = [], 0
        for sh in walk(s.shapes):
            if sh.has_text_frame:
                t = sh.text_frame.text
                if t.strip():
                    texts.append(t)
                    chars += len(t)
                for p in sh.text_frame.paragraphs:
                    if p.runs == [] and p.text.strip():
                        issues.append(f"P{si} 段落无 run（字号/颜色会丢）: {p.text[:24]}")
                    for r in p.runs:
                        rPr = r.font._rPr
                        face = rPr.find(qn("a:latin"))
                        fonts[(face.get("typeface") if face is not None else None)] += 1
                        if (r.text.strip() and rPr.find(qn("a:ea")) is None
                                and rPr.find(qn("a:latin")) is not None):
                            # 只报了 latin 没写 ea → 中英文体不一致（真 bug）
                            # 两者都没写 = 有意继承主题字体（套模板时正常）
                            issues.append(f"P{si} 只设了 latin 缺 a:ea（中文回落）: {r.text[:16]}")
            if sh.top is not None and sh.height is not None and \
                    (sh.top + sh.height) / EMU > H + 0.02:
                issues.append(f"P{si} 形状超出下边界: {sh.name}")
        if chars > 700:
            issues.append(f"P{si} 文本量偏大（{chars} 字），建议拆页")
        slides.append({"page": si, "layout": s.slide_layout.name,
                       "shapes": len(list(walk(s.shapes))), "chars": chars,
                       "text": texts})

    return {"file": path, "size_in": [round(W, 3), round(H, 3)],
            "slide_count": len(prs.slides._sldIdLst),
            "ratio": "16:9" if abs(W / H - 16 / 9) < 0.01 else "非16:9",
            "fonts": {str(k): v for k, v in fonts.most_common()},
            "issues": issues, "slides": slides}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("pptx")
    ap.add_argument("--text", action="store_true", help="逐页打印文本")
    ap.add_argument("--fonts", action="store_true", help="字体统计")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    a = ap.parse_args(argv)
    r = analyze(a.pptx)

    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0

    print(f"文件: {r['file']}")
    print(f"页数: {r['slide_count']}    尺寸: {r['size_in'][0]}x{r['size_in'][1]}in ({r['ratio']})")
    if a.fonts:
        print("字体:", r["fonts"])
    if a.text:
        for s in r["slides"]:
            print(f"\n== P{s['page']} [{s['layout']}] {s['chars']} 字")
            for t in s["text"]:
                print("   " + t.replace("\n", " | ")[:160])
    print(f"\n质检问题: {len(r['issues'])}")
    for i in r["issues"][:50]:
        print("  -", i)
    return 1 if r["issues"] else 0


if __name__ == "__main__":
    sys.exit(main())
