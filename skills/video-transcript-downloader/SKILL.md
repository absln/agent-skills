---
name: video-transcript-downloader
description: 内容创作者与自媒体创作者在需要下载视频、提取视频网站字幕时，当需要获取纯文本稿或本地媒体文件请一键调用。自动清洗时间轴与杂音标记，一键下载音视频并生成干净的段落式字幕，大幅提升二创与内容处理效率。
---

# Video Transcript Downloader

`./scripts/vtd.js` can:
- Print a transcript as a clean paragraph (timestamps optional).
- Download video/audio/subtitles.

Transcript behavior:
- YouTube: fetch via `youtube-transcript-plus` when possible.
- Otherwise: pull subtitles via `yt-dlp`, then clean into a paragraph.

## Setup

Run from this skill directory. `npm ci` is optional: it installs `youtube-transcript-plus`, which only serves the direct-YouTube-transcript fast path. Without it the script falls back to `yt-dlp` automatically instead of crashing.

```bash
npm ci          # optional
node scripts/vtd.js transcript --url 'https://…'
```

## Transcript (default: clean paragraph)

```bash
./scripts/vtd.js transcript --url 'https://…'
./scripts/vtd.js transcript --url 'https://…' --lang en
./scripts/vtd.js transcript --url 'https://…' --timestamps
./scripts/vtd.js transcript --url 'https://…' --keep-brackets
```

## Download video / audio / subtitles

```bash
./scripts/vtd.js download --url 'https://…' --output-dir ~/Downloads
./scripts/vtd.js audio --url 'https://…' --output-dir ~/Downloads
./scripts/vtd.js subs --url 'https://…' --output-dir ~/Downloads --lang en
```

## Formats (list + choose)

List available formats (format ids, resolution, container, audio-only, etc):

```bash
./scripts/vtd.js formats --url 'https://…'
```

Download a specific format id (example):

```bash
./scripts/vtd.js download --url 'https://…' --output-dir ~/Downloads -- --format 137+140
```

Prefer MP4 container without re-encoding (remux when possible):

```bash
./scripts/vtd.js download --url 'https://…' --output-dir ~/Downloads -- --remux-video mp4
```

## Notes

- Default transcript output is a single paragraph. Use `--timestamps` only when asked.
- Bracketed cues like `[Music]` are stripped by default; keep them via `--keep-brackets`.
- Pass extra `yt-dlp` args after `--` for `transcript` fallback, `download`, `audio`, `subs`, `formats`.

```bash
./scripts/vtd.js formats --url 'https://…' -- -v
```

## Troubleshooting (only when needed)

- Missing `yt-dlp` / `ffmpeg`:

```bash
brew install yt-dlp ffmpeg                   # macOS
winget install yt-dlp.yt-dlp Gyan.FFmpeg     # Windows
sudo apt install yt-dlp ffmpeg               # Debian/Ubuntu
```

- Verify:

```bash
yt-dlp --version
ffmpeg -version | head -n 1
```

- Binary discovery is platform-aware: `PATH` is probed with `PATHEXT` on Windows (so `yt-dlp.exe` / `.cmd` resolve correctly), then common install dirs per platform (Python `Scripts`, WinGet Links, `/opt/homebrew/bin`, `/usr/local/bin`, `~/.local/bin`). No hard-coded homebrew-only path.
