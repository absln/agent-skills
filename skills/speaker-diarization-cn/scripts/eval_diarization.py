#!/usr/bin/env python
"""eval_diarization.py —— 说话人分离的真值回归评测（技能自带工具）

指标（帧级，默认 20ms）：
    每人 precision / recall / F1、语音总时长偏差
    边界：预测段与真值段按最大重叠配对 → 起止 MAE

用法：
    python eval_diarization.py --pred pred.json --gt gt.json --total 22.8 [--hop 0.02]

输入格式：
    pred.json  {"segments":[{"start":..,"end":..,"speaker":"wife"}, ...]}
    gt.json    {"wife":[[start,end], ...], "husband":[[...], ...]}
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def frame_f1(pred, gt, total, hop):
    n = int(math.ceil(total / hop))
    pa, ga = bytearray(n), bytearray(n)
    for s, e in pred:
        for k in range(int(s / hop), min(n, int(math.ceil(e / hop)))):
            pa[k] = 1
    for s, e in gt:
        for k in range(int(s / hop), min(n, int(math.ceil(e / hop)))):
            ga[k] = 1
    tp = sum(1 for a, b in zip(pa, ga) if a and b)
    fp = sum(1 for a, b in zip(pa, ga) if a and not b)
    fn = sum(1 for a, b in zip(pa, ga) if b and not a)
    p = tp / max(tp + fp, 1)
    r = tp / max(tp + fn, 1)
    return {"precision": round(p, 4), "recall": round(r, 4),
            "f1": round(2 * p * r / max(p + r, 1e-9), 4),
            "pred_speech_s": round(sum(pa) * hop, 2), "gt_speech_s": round(sum(ga) * hop, 2)}


def boundary(pred, gt):
    errs_s, errs_e, matched = [], [], 0
    for gs, ge in gt:
        best, ov = None, 0.0
        for ps, pe in pred:
            o = max(0.0, min(ge, pe) - max(gs, ps))
            if o > ov:
                best, ov = (ps, pe), o
        if best and ov > 0.2 * (ge - gs):
            matched += 1
            errs_s.append(abs(best[0] - gs))
            errs_e.append(abs(best[1] - ge))
    mean = lambda v: round(sum(v) / len(v), 3) if v else None  # noqa: E731
    return {"matched": matched, "gt_segments": len(gt),
            "start_mae_s": mean(errs_s), "end_mae_s": mean(errs_e)}


def main() -> int:
    ap = argparse.ArgumentParser(description="分离结果 vs 真值")
    ap.add_argument("--pred", required=True)
    ap.add_argument("--gt", required=True)
    ap.add_argument("--total", type=float, required=True)
    ap.add_argument("--hop", type=float, default=0.02)
    args = ap.parse_args()

    pred = json.loads(Path(args.pred).read_text(encoding="utf-8"))["segments"]
    gt = json.loads(Path(args.gt).read_text(encoding="utf-8"))
    scores, f1s = {}, []
    for who, segs in gt.items():
        p = [(s["start"], s["end"]) for s in pred if s.get("speaker") == who]
        f, b = frame_f1(p, [tuple(x) for x in segs], args.total, args.hop), boundary(p, segs)
        scores[who] = {"frame": f, "boundary": b}
        f1s.append(f["f1"])
        print(f"  {who:<8} F1 {f['f1']:.3f}（P {f['precision']:.3f} / R {f['recall']:.3f}）"
              f"｜语音 {f['pred_speech_s']}s vs 真值 {f['gt_speech_s']}s"
              f"｜边界 MAE 起 {b['start_mae_s']}s 止 {b['end_mae_s']}s（配到 {b['matched']}/{b['gt_segments']}）")
    print(f"  平均帧级 F1 = {sum(f1s) / max(len(f1s), 1):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
