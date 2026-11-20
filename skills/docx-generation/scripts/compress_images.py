#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch compress PNG screenshots for docx embedding.

Usage:
    python compress_images.py <input-dir> <output-dir> [--max-width 900] [--quality 7]

Example:
    python compress_images.py UI/ UI_compressed/ --max-width 800
"""
import argparse
import io
import os
import sys
from pathlib import Path

from PIL import Image


def compress_image(src: Path, dst: Path, max_width: int):
    """Compress a single image, preserving aspect ratio."""
    img = Image.open(src)
    w, h = img.size

    if w > max_width:
        new_h = int(h * max_width / w)
        img = img.resize((max_width, new_h), Image.Resampling.LANCZOS)

    # Convert RGBA/P to RGB for docx compatibility
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, format="PNG", optimize=True)
    return img.size


def main():
    parser = argparse.ArgumentParser(description="Batch compress images for docx embedding")
    parser.add_argument("input_dir", type=str, help="Source directory with PNG images")
    parser.add_argument("output_dir", type=str, help="Output directory for compressed images")
    parser.add_argument("--max-width", type=int, default=900, help="Maximum width in pixels (default: 900)")
    args = parser.parse_args()

    src_dir = Path(args.input_dir)
    dst_dir = Path(args.output_dir)

    if not src_dir.exists():
        print(f"Error: input directory '{src_dir}' does not exist", file=sys.stderr)
        sys.exit(1)

    png_files = list(src_dir.rglob("*.png")) + list(src_dir.rglob("*.PNG"))
    if not png_files:
        print(f"No PNG files found in {src_dir}")
        sys.exit(1)

    total_before = 0
    total_after = 0

    for src_path in png_files:
        rel_path = src_path.relative_to(src_dir)
        dst_path = dst_dir / rel_path

        before_size = src_path.stat().st_size
        compressed_size = compress_image(src_path, dst_path, args.max_width)
        after_size = dst_path.stat().st_size

        total_before += before_size
        total_after += after_size

        ratio = (1 - after_size / before_size) * 100 if before_size > 0 else 0
        print(f"  {rel_path}: {before_size/1024:.0f}KB → {after_size/1024:.0f}KB ({ratio:.0f}% saved)")

    total_ratio = (1 - total_after / total_before) * 100 if total_before > 0 else 0
    print(f"\nTotal: {total_before/1024:.0f}KB → {total_after/1024:.0f}KB ({total_ratio:.0f}% saved) ({len(png_files)} files)")


if __name__ == "__main__":
    main()
