#!/usr/bin/env python3
"""UI 原型自检：结构、Token 化、缩放方案、占位符、外部依赖。

用法:
    python check_prototype.py <prototype.html> [more.html ...]

退出码: 0 = 无 FAIL（可能有 WARN）；1 = 存在 FAIL；2 = 参数错误
"""
import re
import sys
from pathlib import Path

FAIL = "FAIL"
WARN = "WARN"
OK = "PASS"


def analyze(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    findings = []

    def add(level, msg):
        findings.append((level, msg))

    # ---- 结构 ----
    if not re.search(r'<meta\s+charset', text, re.I):
        add(FAIL, "缺少 <meta charset>")
    if not re.search(r'<meta\s+name=["\']viewport["\']', text, re.I):
        add(FAIL, "缺少 viewport meta（小屏/预览会按 980px 渲染）")
    if "<title>" not in text.lower():
        add(WARN, "缺少 <title>")

    # ---- Token 化 ----
    root_block = re.search(r':root\s*\{(.*?)\}', text, re.S)
    var_defs = re.findall(r'--[\w-]+\s*:', root_block.group(1)) if root_block else []
    if not root_block:
        add(FAIL, "未找到 :root，颜色/字号未 Token 化")
    elif len(var_defs) < 8:
        add(WARN, f":root 仅 {len(var_defs)} 个变量，Token 覆盖偏少")

    # 组件区域内裸色值（排除 :root 与 data-uri）
    if root_block:
        body_css = text.replace(root_block.group(0), "")
        body_css = re.sub(r'data:image/svg\+xml[^"\']*', "", body_css)
        hexes = re.findall(r'#[0-9a-fA-F]{3,8}\b', body_css)
        if len(hexes) > 12:
            add(WARN, f"组件区域出现 {len(hexes)} 处裸色值，建议收敛到 Token")

    # ---- 缩放方案 ----
    if not re.search(r'html\s*\{[^}]*font-size', text, re.S):
        add(FAIL, "未设置根字号（无法按基准分辨率等比缩放）")
    else:
        if "clamp" not in text:
            add(WARN, "根字号未用 clamp 限制上下界")
        if re.search(r'font-size\s*:\s*calc\(\s*100vw', text):
            add(WARN, "根字号疑似用 calc(100vw/…) 且无上限，小屏会过大")
    if "rem" not in text:
        add(FAIL, "全文未使用 rem，尺寸无法随屏幕等比缩放")
    if re.search(r'(^|[;{\s])zoom\s*:', text):
        add(WARN, "使用了 zoom，跨浏览器不一致，改用 rem")

    # ---- 外部依赖 ----
    ext = re.findall(r'<(?:script|link)[^>]+(?:src|href)=["\'](https?:)?//', text, re.I)
    if ext:
        add(WARN, f"引用 {len(ext)} 处外部资源，单文件交付建议内联")

    # ---- 表格兜底 ----
    if "<table" in text.lower():
        if "min-width" not in text:
            add(WARN, "表格缺少 min-width，窄屏会被压变形")
        if "overflow-x" not in text:
            add(WARN, "表格容器缺少 overflow-x，无法横向滚动")

    # ---- 占位符 / 半成品 ----
    for token in ("TODO", "lorem ipsum", "FIXME", "XXX"):
        if token.lower() in text.lower():
            add(WARN, f"含占位标记 `{token}`，交付前清理")
    if "待补充" in text or "待确认" in text:
        add(WARN, "含「待补充/待确认」文本：确认是设计标注还是未完成内容")

    # ---- 交互可达性 ----
    pages = re.findall(r'<section[^>]*class=["\'][^"\']*\bpage\b[^"\']*["\'][^>]*id=["\']([^"\']+)', text)
    if len(pages) > 1:
        if "data-page" not in text:
            add(WARN, f"存在 {len(pages)} 个页面但无 data-page 切换入口")
        else:
            targets = set(re.findall(r'data-page=["\']([^"\']+)["\']', text))
            missing = [p for p in pages if p not in targets]
            if missing:
                add(WARN, f"页面无入口可到达: {', '.join(missing)}")

    # ---- id 唯一性 ----
    ids = re.findall(r'\sid=["\']([^"\']+)["\']', text)
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        add(FAIL, f"重复 id: {', '.join(dup)}")

    # ---- 体积 ----
    kb = path.stat().st_size / 1024
    if kb > 500:
        add(WARN, f"文件 {kb:.0f}KB，偏大；考虑拆 CSS 或精简示例数据")

    return findings, kb, len(pages)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    worst = 0
    for raw in argv[1:]:
        path = Path(raw)
        print(f"\n== {path} ==")
        if not path.exists():
            print(f"{FAIL}  文件不存在")
            worst = 1
            continue
        findings, kb, pages = analyze(path)
        order = {FAIL: 0, WARN: 1, OK: 2}
        findings.sort(key=lambda f: order[f[0]])
        if not findings:
            print(f"{OK}    结构、Token、缩放、依赖检查全部通过")
        for level, msg in findings:
            print(f"{level:<5} {msg}")
        fails = sum(1 for lv, _ in findings if lv == FAIL)
        warns = sum(1 for lv, _ in findings if lv == WARN)
        print(f"-- {pages} 个页面 / {kb:.0f}KB / FAIL {fails} / WARN {warns}")
        worst = max(worst, 1 if fails else 0)
    return worst


if __name__ == "__main__":
    sys.exit(main(sys.argv))
