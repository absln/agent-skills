# -*- coding: utf-8 -*-
"""从 pi 会话 JSONL 里提取聊天图片（当前模型看不了图片时的唯一取图途径）

用法：
    python extract_session_images.py                 # 用 $PI_SESSION_FILE
    python extract_session_images.py <会话.jsonl> <输出目录>
    python extract_session_images.py -                # 显式用环境变量

图是 base64 存在 assistant/user 消息的 content[].type == "image" 里；
本脚本按出现顺序导出为 img_01.png / img_02.png … 并打印每张的字节数与尺寸。
"""
import base64
import io
import json
import os
import sys


def extract(session_path, outdir):
    os.makedirs(outdir, exist_ok=True)
    n = 0
    with io.open(session_path, encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            line = line.strip()
            if not line or "image" not in line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            msg = obj.get("message") or obj
            content = msg.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict) or part.get("type") != "image":
                    continue
                data = part.get("data") or ""
                if not data:
                    continue
                n += 1
                raw = base64.b64decode(data)
                ext = ".png"
                if raw[:3] == b"\xff\xd8\xff":
                    ext = ".jpg"
                elif raw[:4] == b"RIFF":
                    ext = ".webp"
                out = os.path.join(outdir, "img_%02d%s" % (n, ext))
                with open(out, "wb") as w:
                    w.write(raw)
                size = ""
                try:
                    from PIL import Image
                    size = "  %dx%d" % Image.open(io.BytesIO(raw)).size
                except Exception:
                    pass
                print("L%-6d %s  %d bytes%s" % (line_no, out, len(raw), size))
    if not n:
        print("未找到图片（该会话可能没有图片消息，或图未被写入会话文件）")
    return n


if __name__ == "__main__":
    arg1 = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PI_SESSION_FILE", "")
    if not arg1 or arg1 == "-":
        arg1 = os.environ.get("PI_SESSION_FILE", "")
    outdir = sys.argv[2] if len(sys.argv) > 2 else "docs/draft/_img"
    if not arg1:
        sys.exit("未提供会话文件，且 $PI_SESSION_FILE 为空")
    print("会话文件:", arg1)
    extract(arg1, outdir)
