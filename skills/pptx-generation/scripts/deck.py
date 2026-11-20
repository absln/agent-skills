# -*- coding: utf-8 -*-
"""pptx-generation · 可复用版式工具库

用 python-pptx 以「设计令牌 + 版式函数」方式生成 16:9 演示文稿。
本文件是**通用库**，不含任何具体项目文案——文案由调用方传入。

用法（同目录）::

    from deck import Deck

    d = Deck(theme="midnight")                 # 或 Deck(template=".../科技风通用模板.pptx")
    d.cover("作品名称", "副标题", ["演示人：XXX", "指导教师：YYY"])
    d.section(1, "背景")
    d.title_content("我们看到了什么", [
        ("普通要点", "body"),
        ("强调要点", "accent"),
        ("次要/历史信息", "dim"),
    ])
    d.kpi([("66%", "命中率"), ("50个", "样本")])
    d.closing("谢谢！", "一句话收束")
    d.save("out.pptx")

自检::

    python deck.py            # 生成 demo.pptx 并打印校验信息
"""
from __future__ import annotations

import os
from typing import Iterable, Sequence

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

__all__ = ["Deck", "THEMES", "inspect"]

# ---------------------------------------------------------------- 设计令牌

THEMES = {
    # 深色科技风（默认）：深蓝底 + 金色标题 + 亮蓝强调
    "midnight": {
        "bg":      RGBColor(0x0E, 0x1B, 0x33),
        "bg_alt":  RGBColor(0x16, 0x2A, 0x4A),
        "title":   RGBColor(0xF5, 0xC5, 0x42),
        "text":    RGBColor(0xFF, 0xFF, 0xFF),
        "accent":  RGBColor(0x5F, 0xB4, 0xE8),
        "dim":     RGBColor(0x9F, 0xB2, 0xCC),
        "rule":    RGBColor(0x2E, 0x4A, 0x73),
        "on_dark": True,
    },
    # 浅色商务风：白底 + 深蓝标题
    "light": {
        "bg":      RGBColor(0xFF, 0xFF, 0xFF),
        "bg_alt":  RGBColor(0xF2, 0xF6, 0xFB),
        "title":   RGBColor(0x12, 0x3A, 0x6B),
        "text":    RGBColor(0x22, 0x2A, 0x35),
        "accent":  RGBColor(0x1D, 0x9A, 0xF8),
        "dim":     RGBColor(0x6B, 0x7A, 0x8C),
        "rule":    RGBColor(0xD5, 0xDE, 0xE9),
        "on_dark": False,
    },
    # 白底青蓝科技风——对齐 assets/科技风通用模板.pptx 的 2AF8FF / 1D9AF8
    "techcyan": {
        "bg":      RGBColor(0xFF, 0xFF, 0xFF),
        "bg_alt":  RGBColor(0xF2, 0xF7, 0xFC),
        "title":   RGBColor(0x0A, 0x25, 0x40),
        "text":    RGBColor(0x23, 0x30, 0x3F),
        "accent":  RGBColor(0x1D, 0x9A, 0xF8),
        "dim":     RGBColor(0x7A, 0x8A, 0x9A),
        "rule":    RGBColor(0x2A, 0xF8, 0xFF),
        "on_dark": False,
    },
}


def _drop_fonts(prs):
    """从 Presentation 对象里摘掉内嵌字体（供 Deck 方法与文件级函数共用）。"""
    part = prs.part
    drop = [rId for rId, rel in part.rels.items() if rel.reltype.endswith("/font")]
    for rId in drop:
        part.drop_rel(rId)
    el = part._element.find(qn("p:embeddedFontLst"))
    if el is not None:
        el.getparent().remove(el)
    return len(drop)


def strip_embedded_fonts(path, font_map=None):
    """**就地**剔除任意 pptx 的内嵌字体（用于清理模板资产，不经过 Deck）。

    :param path: 目标 .pptx（会被覆写）
    :param font_map: 可选 ``{原字体: 新字体}``；给了就顺手调 ``unify_fonts``，
                     避免剔完字体后中文回落到宋体。
    :return: (删除的字体关系数, 替换的 typeface 处数)
    """
    prs = Presentation(path)
    n = _drop_fonts(prs)
    prs.save(path)
    m = unify_fonts(path, font_map) if font_map else 0
    return n, m


def unify_fonts(path, mapping):
    """保存后**就地**把所有 typeface 改写为指定字体（含 slide/layout/master/theme）。

    必要时配合 ``Deck.strip_embedded_fonts()``：删掉内嵌字体后，全文改用系统自带字体
    （微软雅黑），否则模板原字体缺失会回落宋体。返回替换处数。
    """
    import re
    import shutil
    import zipfile
    pat = re.compile(r'typeface="([^"]+)"')
    targets = ("ppt/slides/", "ppt/slideLayouts/", "ppt/slideMasters/", "ppt/theme/")
    cnt = [0]

    def sub(m):
        new = mapping.get(m.group(1))
        if new is None:
            return m.group(0)
        cnt[0] += 1
        return 'typeface="%s"' % new

    src = zipfile.ZipFile(path)
    tmp = path + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
        for it in src.infolist():
            data = src.read(it.filename)
            if it.filename.endswith(".xml") and it.filename.startswith(targets):
                data = pat.sub(sub, data.decode("utf-8")).encode("utf-8")
            out.writestr(it, data)
    src.close()
    shutil.move(tmp, path)
    return cnt[0]


def iter_text_frames(shapes):
    """递归遍历形状（含组合）产出其 text_frame。"""
    for sh in shapes:
        if sh.shape_type == 6 and hasattr(sh, "shapes"):        # GROUP
            yield from iter_text_frames(sh.shapes)
        elif sh.has_text_frame:
            yield sh.text_frame

# 字号阶梯（pt）：按 16:9 / 13.333×7.5 英寸 校准，1 屏 ≤ 6 行正文
TYPE_SCALE = {
    "cover_title": 44,
    "closing":     40,
    "slide_title": 28,
    "section_no":  60,
    "kpi_value":   40,
    "lead":        22,
    "body":        18,
    "small":       14,
    "footnote":    11,
}

CJK_FALLBACK = ("微软雅黑", "Microsoft YaHei", "思源黑体 CN", "Noto Sans CJK SC")

#: 传入 title_font/body_font 的**不写字体**哨兵值：让 run 继承模板主题字体
#: （套用自带字体的模板时用，配合内嵌字体可保字体不丢）
THEME_FONT = "@theme"

# 版心（英寸）：左右留白 1.3，正文顶边 1.55
GRID = {
    "margin_x": 1.3,
    "title_y":  0.40,
    "title_h":  0.85,
    "body_y":   1.55,
    "body_h":   5.20,
    "footer_y": 6.95,
}


# ---------------------------------------------------------------- 底层工具

def _set_font(run, *, size, color, bold=False, font=None):
    """设置 run 字体，**同时写 latin / ea / cs 三个 typeface**。

    只设 font.name 只影响西文字符，中文会回落到主题东亚字体（常见为宋体/等线），
    这是「代码里设了字体但 PPT 里没生效」的根因。
    """
    f = run.font
    f.size = Pt(size)
    f.bold = bold
    f.color.rgb = color
    name = font or CJK_FALLBACK[0]
    if name == THEME_FONT:                            # 不写字体 → 继承模板主题字体
        return
    f.name = name                                     # -> a:latin
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):                      # 顺序：latin, ea, cs
        el = rPr.find(qn(tag))
        if el is None:
            el = rPr.makeelement(qn(tag), {})
            rPr.insert_element_before(
                el, "a:cs" if tag == "a:ea" else "a:sym"
            )
        el.set("typeface", name)


def _para(tf, first: bool):
    return tf.paragraphs[0] if first else tf.add_paragraph()


# ---------------------------------------------------------------- 主类

class Deck:
    """演示文稿构建器。

    :param theme:      THEMES 中的主题名（自建版式时使用）
    :param template:   模板 .pptx 路径（套用模板时使用，theme 仅作配色兜底）
    :param title_font: 标题中文字体
    :param body_font:  正文中文字体
    """

    def __init__(self, theme: str = "midnight", template: str | None = None,
                 title_font: str | None = None, body_font: str | None = None,
                 size: tuple[float, float] = (13.333, 7.5),
                 keep_template_slides: bool = False):
        self.prs = Presentation(template) if template else Presentation()
        if not template:
            self.prs.slide_width = Inches(size[0])
            self.prs.slide_height = Inches(size[1])
        self.W = self.prs.slide_width / 914400
        self.H = self.prs.slide_height / 914400
        self.c = dict(THEMES[theme])
        self.title_font = title_font or CJK_FALLBACK[0]
        self.body_font = body_font or CJK_FALLBACK[0]
        self._blank = self._pick_blank_layout()
        self._n = 0                                          # 已加页数
        self._page_no = 0
        if template and not keep_template_slides:
            self.strip_slides()

    def strip_slides(self, keep: int = 0):
        """删除模板自带页（只留母版/版式/配色），从 keep 之后全删。"""
        sldIdLst = self.prs.slides._sldIdLst
        for sldId in list(sldIdLst)[keep:]:
            self.prs.part.drop_rel(sldId.get(qn("r:id")))
            sldIdLst.remove(sldId)
        self._n = 0
        self._page_no = 0
        return self

    # -------------------------------------------------- 套用模板

    def keep_slides(self, indices):
        """只保留指定的原有页（0-based，保持原顺序），其余删除。

        用途：从模板里只留封面/感谢页，中间换成自己的内容页。
        """
        sldIdLst = self.prs.slides._sldIdLst
        sldIds = list(sldIdLst)
        keep = {sldIds[i] for i in indices}
        for sldId in sldIds:
            if sldId not in keep:
                self.prs.part.drop_rel(sldId.get(qn("r:id")))
                sldIdLst.remove(sldId)
        return self

    def move_slide(self, i, j):
        """把第 i 页移到位置 j（0-based）——新页总追加在末尾，靠它调序。"""
        lst = self.prs.slides._sldIdLst
        el = list(lst)[i]
        lst.remove(el)
        lst.insert(j, el)
        return self

    def frame_texts(self, slide):
        """列出某页所有文本框的文本（已 strip），用于定位模板占位符。"""
        return [tf.text.strip() for tf in iter_text_frames(slide.shapes)]

    def set_template_text(self, slide, mapping, *, contains=False):
        """改写模板页文字，**保留原 run 的字体/字号/颜色**。

        mapping: ``{"原文字": "新文字"}``；默认整框精确匹配，contains=True 时子串匹配。
        只改第一个 run，删掉其余 run 与多余段落，避免格式回退。返回替换处数。
        """
        hits = 0
        for tf in iter_text_frames(slide.shapes):
            cur = tf.text.strip()
            for old, new in mapping.items():
                if (old in cur) if contains else (cur == old):
                    p0 = tf.paragraphs[0]
                    if not p0.runs:
                        p0.add_run()
                    p0.runs[0].text = new
                    for r in list(p0.runs[1:]):
                        r._r.getparent().remove(r._r)
                    for p in list(tf.paragraphs[1:]):
                        p._p.getparent().remove(p._p)
                    hits += 1
                    break
        return hits

    # -------------------------------------------------- 基础

    def _pick_blank_layout(self):
        """优先找名为「空白」的版式，否则取最后一个（通常是空白）。"""
        for m in self.prs.slide_masters:
            for l in m.slide_layouts:
                if l.name.strip() in ("空白", "Blank"):
                    return l
        return self.prs.slide_layouts[-1]

    def add_slide(self, bg: str = "bg", page_no: bool = False):
        """新增一页。page_no=True 时在右下角加页码（内容页已有左上角编号，一般不必开）。"""
        s = self.prs.slides.add_slide(self._blank)
        self._fill(s.background.fill, self.c[bg])
        self._n += 1
        if page_no:
            self._page_no += 1
            self.footer(s, self._page_no)
        return s

    def _fill(self, fill, rgb):
        fill.solid()
        fill.fore_color.rgb = rgb

    # -------------------------------------------------- 文本原子

    def text(self, slide, x, y, w, h, s: str, *, size=None, color=None,
             bold=False, align=PP_ALIGN.LEFT, font=None, anchor=MSO_ANCHOR.TOP,
             line_spacing: float | None = None):
        size = size or TYPE_SCALE["body"]
        color = color or self.c["text"]
        tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = anchor
        lines = s.split("\n")
        for i, ln in enumerate(lines):
            p = _para(tf, i == 0)
            p.alignment = align
            if line_spacing:
                p.line_spacing = line_spacing
            r = p.add_run()                     # 必须 add_run()，用 p.text= 会丢控点
            r.text = ln
            _set_font(r, size=size, color=color, bold=bold, font=font or self.body_font)
        return tb

    def bullets(self, slide, items: Sequence, *, x=None, y=None, w=None, h=None,
                size=None, gap=10, line_spacing=1.15, indent_by_space=True):
        """items 元素支持两种写法：

        - ``"文本"``                      → 普通正文
        - ``("文本", "accent")``           → 按语义样式（body/accent/dim/title/lead）
        - ``("文本", "accent", "• ")``     → 追加自定义行首符号
        - ``("",)``                        → 空行（占位，不会被跳过）
        """
        size = size or TYPE_SCALE["body"]
        x = GRID["margin_x"] if x is None else x
        y = GRID["body_y"] if y is None else y
        w = (self.W - 2 * GRID["margin_x"]) if w is None else w
        h = GRID["body_h"] if h is None else h
        tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame
        tf.word_wrap = True
        for i, item in enumerate(items):
            if isinstance(item, str):
                txt, style, mark = item, "body", ""
            elif len(item) == 1:
                txt, style, mark = item[0], "body", ""
            elif len(item) == 2:
                txt, style, mark = item[0], item[1], ""
            else:
                txt, style, mark = item[0], item[1], item[2]
            color = self.c.get(style, self.c["text"])
            bold = style in ("accent", "title", "lead")
            p = _para(tf, i == 0)
            p.space_after = Pt(gap)
            p.line_spacing = line_spacing
            if indent_by_space and mark:
                txt = mark + txt
            r = p.add_run()
            r.text = txt
            _set_font(r, size=size, color=color, bold=bold, font=self.body_font)
        return tb

    def strip_embedded_fonts(self):
        """删除内嵌字体（``ppt/fonts/*.fntdata``）——常可把文件从几十 MB 降到 1 MB 级。

        代价：放映机未装对应字体时字形回退（中文常见回落宋体）。
        因此删前必须把全文改成系统自带字体（如 微软雅黑），见 ``unify_fonts``。
        返回删除的字体关系数。
        """
        return _drop_fonts(self.prs)

    def notes(self, slide, text):
        """写演讲者备注（放映时不占画面）。"""
        slide.notes_slide.notes_text_frame.text = text
        return slide

    def footer(self, slide, num: int, text: str | None = None):
        tb = slide.shapes.add_textbox(
            Inches(self.W - 1.5), Inches(self.H - 0.62), Inches(1.1), Inches(0.4)
        )
        p = tb.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.RIGHT
        r = p.add_run()
        r.text = f"{num:02d}" if text is None else text
        _set_font(r, size=TYPE_SCALE["small"], color=self.c["dim"], font="Arial")
        return tb

    # -------------------------------------------------- 版式

    def title_slide(self, num, title, subtitle=None, *, body_y=None):
        """内容页：左上角编号 + 标题 +（可选）副标题，返回 slide。"""
        s = self.add_slide()
        tb = s.shapes.add_textbox(Inches(GRID["margin_x"] - 0.9), Inches(GRID["title_y"] + 0.08),
                                  Inches(0.85), Inches(0.6))
        r = tb.text_frame.paragraphs[0].add_run()
        r.text = f"{num:02d}" if isinstance(num, int) else str(num)
        _set_font(r, size=TYPE_SCALE["slide_title"], color=self.c["accent"], bold=True, font="Arial")

        self.text(s, GRID["margin_x"], GRID["title_y"], self.W - 2 * GRID["margin_x"], GRID["title_h"],
                  title, size=TYPE_SCALE["slide_title"], color=self.c["title"], bold=True,
                  font=self.title_font)
        # 标题下划线
        ln = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(GRID["margin_x"]), Inches(GRID["title_y"] + 0.88),
                                Inches(self.W - 2 * GRID["margin_x"]), Pt(1))
        self._fill(ln.fill, self.c["rule"])
        ln.line.fill.background()
        ln.shadow.inherit = False
        if subtitle:
            self.text(s, GRID["margin_x"], GRID["title_y"] + 1.0,
                      self.W - 2 * GRID["margin_x"], 0.45, subtitle,
                      size=TYPE_SCALE["small"], color=self.c["dim"])
        return s

    def title_content(self, title, items, *, num=None, subtitle=None, **kw):
        s = self.title_slide(num if num is not None else self._n + 1, title, subtitle)
        self.bullets(s, items, **kw)
        return s

    def cover(self, title, subtitle=None, meta: Iterable[str] = (), *, deco_dots=True):
        s = self.add_slide(bg="bg_alt")
        if deco_dots:
            import math
            for i in range(5):
                a = math.radians(90 - 72 * i)
                dot = s.shapes.add_shape(
                    MSO_SHAPE.OVAL,
                    Inches(self.W / 2 + 2.2 * math.cos(a) - 0.12),
                    Inches(2.6 + 2.2 * math.sin(a) - 0.12),
                    Inches(0.24), Inches(0.24),
                )
                self._fill(dot.fill, self.c["accent"])
                dot.line.fill.background()
                dot.shadow.inherit = False
        cx = self.W / 2
        self.text(s, cx - 5.6, 2.35, 11.2, 1.1, title, size=TYPE_SCALE["cover_title"],
                  color=self.c["title"], bold=True, align=PP_ALIGN.CENTER, font=self.title_font)
        if subtitle:
            self.text(s, cx - 5.6, 3.60, 11.2, 0.8, subtitle, size=TYPE_SCALE["lead"],
                      color=self.c["text"], align=PP_ALIGN.CENTER)
        lines = list(meta)
        for i, ln in enumerate(lines):
            self.text(s, cx - 5.6, 4.75 + i * 0.45, 11.2, 0.45, ln,
                      size=TYPE_SCALE["small"], color=self.c["dim"], align=PP_ALIGN.CENTER)
        return s

    def section(self, num, title, subtitle=None):
        """章节封面页。"""
        s = self.add_slide(bg="bg_alt")
        self.text(s, GRID["margin_x"], 2.6, 3.0, 1.5, f"{num:02d}", size=TYPE_SCALE["section_no"],
                  color=self.c["rule"], bold=True, font="Arial")
        self.text(s, GRID["margin_x"] + 1.9, 2.85, self.W - 2 * GRID["margin_x"] - 1.9, 0.9,
                  title, size=34, color=self.c["title"], bold=True, font=self.title_font)
        if subtitle:
            self.text(s, GRID["margin_x"] + 1.9, 3.75, self.W - 2 * GRID["margin_x"] - 1.9, 0.5,
                      subtitle, size=TYPE_SCALE["small"], color=self.c["dim"])
        return s

    def kpi(self, items: Sequence[tuple[str, str]], *, slide=None, y=None, columns=None):
        """数字卡片版式：[(数值, 说明), ...]，2~5 张。默认贴在最后一张幻灯片上。"""
        y = 1.9 if y is None else y
        n = len(items) if columns is None else columns
        gap = 0.4
        w = (self.W - 2 * GRID["margin_x"] - gap * (n - 1)) / n
        s = slide if slide is not None else self.prs.slides[-1]
        for i, (val, label) in enumerate(items):
            x = GRID["margin_x"] + i * (w + gap)
            box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y),
                                     Inches(w), Inches(1.7))
            self._fill(box.fill, self.c["bg_alt"])
            box.line.color.rgb = self.c["rule"]
            box.shadow.inherit = False
            box.text_frame.word_wrap = True
            self.text(s, x, y + 0.22, w, 0.8, val, size=TYPE_SCALE["kpi_value"],
                      color=self.c["accent"], bold=True, align=PP_ALIGN.CENTER, font="Arial")
            self.text(s, x, y + 1.05, w, 0.5, label, size=TYPE_SCALE["small"],
                      color=self.c["text"], align=PP_ALIGN.CENTER)
        return s

    def image(self, slide, path, x, y, w=None, h=None):
        """按宽度或高度等比贴图（两者都给时以宽度为准）。"""
        kw = {}
        if w is not None:
            kw["width"] = Inches(w)
        if h is not None:
            kw["height"] = Inches(h)
        return slide.shapes.add_picture(path, Inches(x), Inches(y), **kw)

    def table(self, slide, data, x, y, w, h, *, col_widths=None, size=None,
              header=True):
        size = size or TYPE_SCALE["small"]
        rows, cols = len(data), len(data[0])
        shp = slide.shapes.add_table(rows, cols, Inches(x), Inches(y), Inches(w), Inches(h))
        tbl = shp.table
        if col_widths:
            for i, cw in enumerate(col_widths):
                tbl.columns[i].width = Emu(int(Inches(w) * cw / sum(col_widths)))
        for ri, row in enumerate(data):
            for ci, val in enumerate(row):
                cell = tbl.cell(ri, ci)
                cell.text_frame.word_wrap = True
                p = cell.text_frame.paragraphs[0]
                r = p.add_run()
                r.text = str(val)
                is_head = header and ri == 0
                _set_font(r, size=size,
                          color=self.c["title"] if is_head and self.c["on_dark"] else self.c["text"],
                          bold=is_head, font=self.body_font)
        return tbl

    def closing(self, title, line=None, note=None):
        s = self.add_slide(bg="bg_alt")
        cx = self.W / 2
        self.text(s, cx - 5.6, 2.55, 11.2, 1.0, title, size=TYPE_SCALE["closing"],
                  color=self.c["title"], bold=True, align=PP_ALIGN.CENTER, font=self.title_font)
        if line:
            self.text(s, cx - 5.6, 3.80, 11.2, 0.8, line, size=TYPE_SCALE["lead"],
                      color=self.c["text"], align=PP_ALIGN.CENTER)
        if note:
            self.text(s, cx - 5.6, 5.10, 11.2, 0.6, note, size=TYPE_SCALE["body"],
                      color=self.c["accent"], align=PP_ALIGN.CENTER)
        return s

    # -------------------------------------------------- 输出

    def save(self, path):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.prs.save(path)
        return path

    @property
    def slide_count(self):
        return len(self.prs.slides._sldIdLst)


# ---------------------------------------------------------------- 自检

def inspect(path: str):
    """轻量校验：页数 / 空 run / 字体是否三件套齐全 / 文本框外溢估算。"""
    prs = Presentation(path)
    W, H = prs.slide_width / 914400, prs.slide_height / 914400
    issues = []
    for si, s in enumerate(prs.slides, 1):
        for sh in s.shapes:
            if sh.has_text_frame:
                for p in sh.text_frame.paragraphs:
                    if not p.runs and p.text.strip():
                        issues.append(f"P{si} 段落无 run（样式会丢）: {p.text[:20]}")
                    for r in p.runs:
                        rPr = r.font._rPr
                        if rPr.find(qn("a:ea")) is None and r.text.strip():
                            issues.append(f"P{si} 缺东亚字体 a:ea: {r.text[:16]}")
            if sh.top is not None and sh.height is not None:
                if (sh.top + sh.height) / 914400 > H + 0.02:
                    issues.append(f"P{si} 形状下溢出: {sh.name}")
        # 粗略估算：正文文本量 vs 版心容量
        text_len = sum(len(sh.text_frame.text) for sh in s.shapes if sh.has_text_frame)
        if text_len > 700:
            issues.append(f"P{si} 文本量偏大({text_len} 字)，考虑拆页")
    print(f"页数={len(prs.slides._sldIdLst)}  尺寸={W:.3f}x{H:.3f}in  问题={len(issues)}")
    for i in issues[:40]:
        print("  -", i)
    return issues


# ---------------------------------------------------------------- demo

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "demo.pptx")
    d = Deck(theme="midnight")
    d.cover("示例作品名", "—— 一句话副标题 ——",
            ["汇报人：XXX", "指导教师：YYY", "20XX-XX-XX"])
    d.title_content("这是内容页", [
        ("普通要点，用于陈述事实", "body"),
        ("强调要点，用于关键结论", "accent"),
        ("次要信息，如已废弃方案", "dim"),
        ("",),
        ("行首符号可自定义：", "lead"),
        ("① 第一条", "body", "  "),
        ("② 第二条", "body", "  "),
    ])
    d.section(2, "章节标题", "SECTION TITLE")
    d.title_content("数字版式", [("用 kpi() 展示量化结果", "body")])
    d.kpi([("66%", "命中率"), ("50个", "样本量"), ("3天", "耗时")])
    d.save(out)
    print("已生成:", out)
    inspect(out)
