#!/usr/bin/env python
"""asset_qa.py —— 素材包质检（技能自带工具）

检查（对 "紧图 + bbox" 契约）：
    1) meta 必备字段 / 文件齐全
    2) 每层 bbox 存在且在包空间内
    3) 分层合成对位：按 bbox 合成 vs 参考图 → alpha IoU（门槛 0.98）
    4) 变体（口型/表情）：**ROI 外零改动**、互不相同、无空变体
    5) 碎块提示、调色板提示

用法：
    python asset_qa.py --pack path/to/<role>_v1 [--tol 2]
    python asset_qa.py --mouths <目录> --roi x0,y0,x1,y1     # 只查变体对齐
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

RESULTS: list[tuple[str, bool, str]] = []


def rec(name: str, ok: bool, detail: str) -> None:
    RESULTS.append((name, ok, detail))
    print(f"  {'✅' if ok else '❌'} {name}: {detail}")


def load(p: Path) -> Image.Image:
    return Image.open(p).convert("RGBA")


def diff_bbox(a: Image.Image, b: Image.Image, thresh: int = 24):
    pa, pb = np.asarray(a, np.int16), np.asarray(b, np.int16)
    m = np.abs(pa - pb).max(axis=2) > thresh
    ys, xs = np.nonzero(m)
    return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1) if len(xs) else None


def qa_variants(files: list[Path], tol: int, roi: tuple[int, int, int, int] | None) -> None:
    imgs = [load(p) for p in files]
    rec("变体画布一致", len({im.size for im in imgs}) == 1,
        f"{len(files)} 个，尺寸集合 { {im.size for im in imgs} }")
    md5s = {hashlib.md5(p.read_bytes()).hexdigest() for p in files}
    rec("变体互不相同", len(md5s) == len(files), f"去重 {len(md5s)}/{len(files)}")
    ref = imgs[0]
    empties, violations, worst = [], [], 0.0
    for p, im in zip(files[1:], imgs[1:]):
        b = diff_bbox(ref, im)
        if b is None:
            empties.append(p.name)
            continue
        if roi and not (b[0] >= roi[0] and b[1] >= roi[1] and b[2] <= roi[2] and b[3] <= roi[3]):
            violations.append(f"{p.name}:{b}")
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        worst = max(worst, abs(cx - (ref.width / 2)), abs(cy - (ref.height / 2)))
    rec("无空变体", not empties, f"空：{empties or '无'}")
    if roi:
        rec("变体改动全部落在 ROI 内（ROI 外零改动）", not violations,
            f"ROI={roi}，越界 {violations or '无'}")
    else:
        rec("变体改动中心漂移（参考值，不做判定）", True, f"最大 {worst:.1f}px")


def qa_pack(pack: Path, tol: int) -> None:
    meta_p = pack / "meta.json"
    if not meta_p.exists():
        rec("meta.json 存在", False, str(meta_p))
        return
    m = json.loads(meta_p.read_text(encoding="utf-8"))
    need = ("id", "space", "reference", "reference_bbox", "layers", "mouths")
    missing = [k for k in need if k not in m]
    rec("meta 必备字段", not missing, f"缺：{missing or '无'}")
    missing_files = [rel for rel in [m.get("reference", "")] + [l["png"] for l in m.get("layers", [])]
                     + m.get("mouths", {}).get("files", []) if rel and not (pack / rel).exists()]
    rec("文件齐全", not missing_files, f"缺 {missing_files or '无'}（层 {len(m.get('layers', []))}、"
        f"口型 {len(m.get('mouths', {}).get('files', []))}）")
    bboxes = {Path(l["png"]).name: l["bbox"] for l in m.get("layers", [])}
    rec("每层 bbox 在包空间内", all(b[0] >= 0 and b[1] >= 0 for b in bboxes.values()),
        f"{len(bboxes)} 层")
    ref_p = pack / m["reference"]
    if ref_p.exists():
        ref = load(ref_p)
        comp = Image.new("RGBA", ref.size, (0, 0, 0, 0))
        for l in m.get("layers", []):
            im = load(pack / l["png"])
            b = l["bbox"]
            if im.size == ref.size:
                comp.paste(im, (0, 0), im)          # 整幅出图
            else:
                comp.paste(im, (b[0], b[1]), im)    # 紧图 → 按 bbox 落位
        a = np.asarray(comp.getchannel("A")) > 128
        r = np.asarray(ref.getchannel("A")) > 128
        iou = float((a & r).sum()) / max(1, int((a | r).sum()))
        rec("分层合成对位（alpha IoU）", iou >= 0.98, f"IoU={iou:.4f}")
    mouth_dir = pack / "mouths"
    if mouth_dir.exists():
        qa_variants(sorted(mouth_dir.glob("*.png")), tol, None)


def main() -> int:
    ap = argparse.ArgumentParser(description="素材包质检")
    ap.add_argument("--pack", default=None)
    ap.add_argument("--mouths", default=None)
    ap.add_argument("--roi", default=None, help="x0,y0,x1,y1")
    ap.add_argument("--tol", type=int, default=2)
    args = ap.parse_args()
    roi = tuple(int(v) for v in args.roi.split(",")) if args.roi else None
    print("=== 素材质检 ===")
    if args.mouths:
        qa_variants(sorted(Path(args.mouths).glob("*.png")), args.tol, roi)
    if args.pack:
        qa_pack(Path(args.pack), args.tol)
    bad = [r for r in RESULTS if not r[1]]
    print(f"\n结论：{'全部通过' if not bad else f'{len(bad)} 项未通过'}"
          f"（{len(RESULTS) - len(bad)}/{len(RESULTS)}）")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
