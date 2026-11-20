#!/usr/bin/env python
"""render_verify.py —— OpenToonz 无头渲染 + 像素验收（技能自带工具）

用法：
    # 1) 渲染（自动使用正确的 cwd，避免"退出码 0 却无产物/死等"）
    python render_verify.py render --scene <绝对路径.tnz> --out <前缀..png> \
        --first 0 --last 24 --toonz-root D:/Program/OpenToonz
    # 2) 验收：与"设计图"逐像素比对（alpha 不一致率 + RGB 平均绝对差）
    python render_verify.py compare --a <渲染帧.png> --b <设计图.png> [--step 2]

约定（实测）：-range 不含 to；输出编号 = 场景帧号 + 1；缺素材会被静默跳过 → 必须比对像素。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def render(args: argparse.Namespace) -> int:
    root = Path(args.toonz_root)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(root / "tcomposer.exe"), str(Path(args.scene)), "-o", str(out),
           "-range", str(args.first), str(args.last),
           "-TOONZROOT", str(root / "stuff")]
    log = out.parent / (out.stem.rstrip(".") + ".render.log")
    print("$ " + " ".join(cmd) + f"   (cwd={root})")
    with log.open("w", encoding="utf-8") as fh:
        proc = subprocess.run(cmd, cwd=str(root), stdout=fh, stderr=subprocess.STDOUT,
                              stdin=subprocess.DEVNULL)
    made = sorted(out.parent.glob(out.stem + "*.png"))
    print(f"exit={proc.returncode} 产出 {len(made)} 个 → {out.parent}（日志 {log.name}）")
    if proc.returncode != 0:
        print(log.read_text(encoding="utf-8", errors="replace")[-600:], file=sys.stderr)
        return 1
    if not made:
        print("！退出码 0 但没有产物：检查 cwd 是否为安装根、level 路径是否为反斜杠绝对路径、"
              "raster level 是否为编号序列", file=sys.stderr)
        return 1
    return 0


def compare(args: argparse.Namespace) -> int:
    import numpy as np
    from PIL import Image

    a = Image.open(args.a).convert("RGBA")
    b = Image.open(args.b).convert("RGBA")
    if a.size != b.size:
        print(f"❌ 尺寸不同：{a.size} vs {b.size}")
        return 1
    pa = np.asarray(a, dtype=np.int16)[:: args.step, :: args.step]
    pb = np.asarray(b, dtype=np.int16)[:: args.step, :: args.step]
    oa, ob = pa[..., 3] > args.alpha, pb[..., 3] > args.alpha
    mismatch = float((oa != ob).mean())
    both = oa & ob
    rgb = float(np.abs(pa[..., :3][both] - pb[..., :3][both]).mean()) if both.any() else 0.0
    ok = mismatch <= args.max_mismatch and rgb <= args.max_rgb
    print(f"{'✅' if ok else '❌'} alpha 不一致率 {mismatch:.2%}（阈值 {args.max_mismatch:.1%}）｜"
          f"共同不透明区 RGB 平均差 {rgb:.2f}/255（阈值 {args.max_rgb}）")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="OpenToonz 渲染 + 像素验收")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render", help="调用 tcomposer 渲染")
    r.add_argument("--scene", required=True)
    r.add_argument("--out", required=True, help="输出前缀，形如 dir/name..png")
    r.add_argument("--first", type=int, required=True)
    r.add_argument("--last", type=int, required=True)
    r.add_argument("--toonz-root", default="D:/Program/OpenToonz")
    r.set_defaults(func=render)

    c = sub.add_parser("compare", help="两张图逐像素比对")
    c.add_argument("--a", required=True)
    c.add_argument("--b", required=True)
    c.add_argument("--step", type=int, default=2)
    c.add_argument("--alpha", type=int, default=128)
    c.add_argument("--max-mismatch", type=float, default=0.02)
    c.add_argument("--max-rgb", type=float, default=12.0)
    c.set_defaults(func=compare)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
