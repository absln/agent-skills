# -*- coding: utf-8 -*-
"""图片 OCR —— 纯 Python 实现，不依赖 PowerShell

后端（自动挑选，可用 --engine 强制）：
  1. winocr    Windows 内置 OCR（Windows.Media.Ocr / WinRT），需 pip install winsdk，
               不用装 tesseract；语言包跟随系统，中文输出 zh-Hans-CN
  2. tesseract pytesseract，需另装 tesseract 引擎与 chi_sim 语言包

用法：
    python ocr.py <图片|目录> ...              # 自动选后端
    python ocr.py --scale 4 shot.png           # 小字/截图先放大 4 倍（推荐）
    python ocr.py --lang zh-Hans-CN a.png      # 指定语言（默认优先中文引擎）
    python ocr.py --engine tesseract a.png     # 强制走后端
    python ocr.py --list                       # 看有哪些引擎和语言包
    python ocr.py --md out.md imgs/            # 写文件而不是 stdout
    python ocr.py --raw a.png                  # 不压缩中文之间的空格

输出格式：每张图一段
    ===== <路径> =====
    引擎语言: zh-Hans-CN
    <识别文本，一行一条>
单图失败只打印 `ERR: ...` 并继续处理下一张。
"""
import argparse
import asyncio
import importlib
import os
import re
import sys
import tempfile

IMG_EXT = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp")
# 汉字 + 全角标点：Windows OCR 在这两类字符间也会插空格（"待确认 ： 是否"）
_CJK = ("\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
        "\u3000-\u303f\uff01-\uff20\uff3b-\uff40\uff5b-\uff65")
_TESS_LANG = {
    "zh": "chi_sim+eng", "zh-Hans-CN": "chi_sim+eng", "zh-Hans": "chi_sim+eng",
    "zh-CN": "chi_sim+eng", "en": "eng", "en-US": "eng",
}


def _winrt(path):
    """导入 WinRT 类型，兼容 winsdk 与新版 winrt-* 两种 pip 包"""
    mod, name = path.rsplit(".", 1)
    for root in ("winsdk", "winrt"):
        try:
            return getattr(importlib.import_module(root + "." + mod), name)
        except (ImportError, AttributeError):
            continue
    raise ImportError("缺少 WinRT 绑定：pip install winsdk")


def squeeze(text):
    """Windows OCR 会把中文逐字用空格隔开（数 据 门 禁），这里合回去"""
    return re.sub(r"(?<=[%s])[ \t]+(?=[%s])" % (_CJK, _CJK), "", text).strip()


def _expand(paths):
    """展开目录，过滤掉不存在的路径"""
    out = []
    for p in paths:
        if os.path.isdir(p):
            out += [os.path.join(p, f) for f in sorted(os.listdir(p))
                    if f.lower().endswith(IMG_EXT)]
        elif os.path.isfile(p):
            out.append(p)
        else:
            print("ERR: 找不到 %s" % p, file=sys.stderr)
    return out


def _prepare(path, scale, max_dim):
    """按需放大/缩到引擎限制内，返回 (待识别路径, 需清理的临时文件)"""
    from PIL import Image
    im = Image.open(path)
    w, h = im.size
    k = scale * min(1.0, float(max_dim) / max(w * scale, h * scale))
    nw, nh = max(1, int(round(w * k))), max(1, int(round(h * k)))
    if (nw, nh) == (w, h):
        return path, None
    fd, tmp = tempfile.mkstemp(suffix=".png", prefix="ocr_")
    os.close(fd)
    im.convert("RGB").resize((nw, nh), Image.LANCZOS).save(tmp)
    return tmp, tmp


def _winsdk_engine(lang):
    OcrEngine = _winrt("windows.media.ocr.OcrEngine")
    Language = _winrt("windows.globalization.Language")
    avail = [l.language_tag for l in OcrEngine.available_recognizer_languages]
    # 默认优先中文引擎：TryCreateFromUserProfileLanguages 在英文档案系统上只给 en-US，
    # 会把中文整段漏掉
    cands = ([lang] if lang else []) + ["zh-Hans-CN", "zh-Hans", "en-US"] + avail
    for tag in cands:
        try:
            eng = OcrEngine.try_create_from_language(Language(tag))
        except Exception:
            eng = None
        if eng is not None:
            return eng
    return OcrEngine.try_create_from_user_profile_languages()


async def _winsdk_ocr(engine, path, scale, raw):
    StorageFile = _winrt("windows.storage.StorageFile")
    FileAccessMode = _winrt("windows.storage.FileAccessMode")
    BitmapDecoder = _winrt("windows.graphics.imaging.BitmapDecoder")
    SoftwareBitmap = _winrt("windows.graphics.imaging.SoftwareBitmap")
    PixelFormat = _winrt("windows.graphics.imaging.BitmapPixelFormat")
    max_dim = _winrt("windows.media.ocr.OcrEngine").max_image_dimension

    target, tmp = _prepare(path, scale, max_dim)
    try:
        f = await StorageFile.get_file_from_path_async(os.path.abspath(target))
        stream = await f.open_async(FileAccessMode.READ)
        dec = await BitmapDecoder.create_async(stream)
        bmp = await dec.get_software_bitmap_async()
        if bmp.bitmap_pixel_format != PixelFormat.BGRA8:   # OCR 只吃 BGRA8
            try:
                conv = SoftwareBitmap.convert(bmp, PixelFormat.BGRA8)
                if conv is not None:
                    bmp = conv
            except Exception:
                pass
        res = await engine.recognize_async(bmp)
        return [line.text if raw else squeeze(line.text) for line in res.lines]
    finally:
        if tmp:
            try:
                os.remove(tmp)
            except OSError:
                pass


def _tess_ocr(path, lang, scale):
    import pytesseract
    from PIL import Image
    im = Image.open(path)
    if scale != 1:
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
    code = _TESS_LANG.get(lang or "", lang or "chi_sim+eng")
    return pytesseract.image_to_string(im, lang=code).splitlines()


def _resolve_engine(name, lang):
    """返回 (后端名, 引擎对象)；都不可用时 (None, None)"""
    if name in ("auto", "winocr"):
        try:
            eng = _winsdk_engine(lang)
            if eng is not None:
                return "winocr", eng
        except Exception as exc:
            if name == "winocr":
                raise
            print("提示: Windows OCR 不可用(%s)，改用 tesseract" % exc, file=sys.stderr)
    if name in ("auto", "tesseract"):
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return "tesseract", None
        except Exception as exc:
            if name == "tesseract":
                raise
            print("提示: pytesseract 不可用(%s)" % exc, file=sys.stderr)
    return None, None


def _show(out):
    print("== Windows 内置 OCR ==", file=out)
    try:
        eng = _winsdk_engine(None)
        tags = [l.language_tag for l in _winrt("windows.media.ocr.OcrEngine")
                .available_recognizer_languages]
        print("  可用，默认引擎 %s；语言包: %s"
              % (eng.recognizer_language.language_tag, ", ".join(tags)), file=out)
    except Exception as exc:
        print("  不可用(%s) —— pip install winsdk" % exc, file=out)
    print("== pytesseract ==", file=out)
    try:
        import pytesseract
        print("  可用，版本 %s" % pytesseract.get_tesseract_version(), file=out)
        try:
            print("  语言包: %s" % ", ".join(pytesseract.get_languages()), file=out)
        except Exception:
            pass
    except Exception as exc:
        print("  不可用(%s) —— 装 tesseract 后 pip install pytesseract" % exc, file=out)


def ocr_lines(path, lang="", scale=1.0, engine="auto", raw=False):
    """供其它脚本复用：返回单张图的文本行；没有可用引擎时抛 RuntimeError。"""
    backend, eng = _resolve_engine(engine, lang)
    if backend is None:
        raise RuntimeError("未找到可用 OCR 引擎（Windows: pip install winsdk；"
                           "或装 tesseract + pip install pytesseract）")
    if backend == "winocr":
        return asyncio.run(_winsdk_ocr(eng, path, scale, raw))
    return [ln if raw else squeeze(ln) for ln in _tess_ocr(path, lang, scale)]


def _parse_args(argv):
    ap = argparse.ArgumentParser(
        description="图片 OCR：优先 Windows 内置 OCR，回退 pytesseract",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="*", help="图片文件或目录（多个）")
    ap.add_argument("--engine", choices=("auto", "winocr", "tesseract"), default="auto")
    ap.add_argument("--lang", default="", help="语言标签，如 zh-Hans-CN / en-US")
    ap.add_argument("--scale", type=float, default=1.0, help="识别前放大倍数，默认 1")
    ap.add_argument("--md", default="", help="写入该文件而非 stdout")
    ap.add_argument("--raw", action="store_true", help="不压缩中文之间的空格")
    ap.add_argument("--list", action="store_true", help="列出可用引擎与语言包")
    return ap.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    out = open(args.md, "w", encoding="utf-8") if args.md else sys.stdout
    count = 0
    try:
        if args.list:
            _show(out)
            return 0
        paths = _expand(args.images)
        count = len(paths)
        if not paths:
            print("没有可处理的图片", file=sys.stderr)
            return 2
        try:
            backend, engine = _resolve_engine(args.engine, args.lang)
        except Exception as exc:                      # --engine 指定的后端不可用
            print("ERR: %s" % exc, file=sys.stderr)
            return 3
        if backend is None:
            print("未找到可用 OCR 引擎：Windows 上 pip install winsdk，"
                  "或装 tesseract 引擎 + pip install pytesseract", file=sys.stderr)
            return 3

        if backend == "winocr":
            tag = engine.recognizer_language.language_tag
            for path in paths:                       # 一张图一个 loop，失败不拖累其余
                print("===== %s =====" % path, file=out)
                print("引擎语言: %s" % tag, file=out)
                try:
                    for line in asyncio.run(_winsdk_ocr(engine, path, args.scale, args.raw)):
                        print(line, file=out)
                except Exception as exc:
                    print("ERR: %s" % exc, file=out)
        else:
            for path in paths:
                print("===== %s =====" % path, file=out)
                print("引擎语言: tesseract/%s"
                      % _TESS_LANG.get(args.lang or "", args.lang or "chi_sim+eng"), file=out)
                try:
                    for line in _tess_ocr(path, args.lang, args.scale):
                        print(line if args.raw else squeeze(line), file=out)
                except Exception as exc:
                    print("ERR: %s" % exc, file=out)
        return 0
    finally:
        if args.md:
            out.close()
            if count:
                print("已写入 %s（%d 张图）" % (args.md, count))


if __name__ == "__main__":
    sys.exit(main())
