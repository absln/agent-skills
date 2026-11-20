#!/usr/bin/env python
"""cells_from_cues.py —— 秒级 cue → 逐帧口型序列（技能自带工具）

为什么：口型识别的导出格式帧号约定各异（常见 ceil(t×fps) 且首帧被强制成静止），
以**秒级 cue 为唯一事实来源**、自行量化最稳。

用法：
    python cells_from_cues.py --cues cues.json --fps 24 --total-frames 548 \
        --shape-frame '{"MBP":27,"etc":9,"E":11,"AI":30,"O":7,"U":14,"FV":6,"L":13,"WQ":4,"rest":25}' \
        --out cells.json

cues.json 支持两种写法：
    [{"start":0.05,"end":2.00,"shape":"MBP"}, ...]
    {"cues":[{"start":...,"end":...,"shape":"..."}, ...]}
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="cue(秒) → 逐帧口型序列 + runs")
    ap.add_argument("--cues", required=True)
    ap.add_argument("--fps", type=float, default=24.0)
    ap.add_argument("--total-frames", type=int, default=None,
                    help="不填则按最后一个 cue 的结束时间向上取整")
    ap.add_argument("--shape-frame", required=True, help='JSON: {"形状名": 帧号}')
    ap.add_argument("--rest", default="rest", help="静止形状名（默认 rest）")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    raw = json.loads(Path(args.cues).read_text(encoding="utf-8"))
    cues = raw["cues"] if isinstance(raw, dict) else raw
    cues = sorted(cues, key=lambda c: c["start"])
    sf = json.loads(args.shape_frame)
    total = args.total_frames or int(math.ceil((cues[-1]["end"] if cues else 0) * args.fps))

    cells, shapes = [], []
    i = 0
    for k in range(total):
        t = k / args.fps
        while i + 1 < len(cues) and t >= cues[i]["end"]:
            i += 1
        c = cues[i] if cues else {"shape": args.rest}
        shape = c.get("shape", args.rest)
        if shape not in sf:
            raise SystemExit(f"形状 {shape!r} 不在 --shape-frame 里：{sorted(sf)}")
        cells.append(int(sf[shape]))
        shapes.append(shape)

    runs = []
    for k, shape in enumerate(shapes):
        if runs and runs[-1]["shape"] == shape:
            runs[-1]["count"] += 1
        else:
            runs.append({"from": k, "count": 1, "shape": shape, "frame": int(sf[shape])})

    out = {"fps": args.fps, "total_frames": total, "cells": cells, "runs": runs,
           "shape_frame": sf, "switches": max(len(runs) - 1, 0)}
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")
    print(f"{total} 帧 / {total / args.fps:.2f}s，run 段 {len(runs)}，切换 {out['switches']} 次 → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
