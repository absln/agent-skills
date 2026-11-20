---
name: edge-tts
description: 用 uvx edge-tts 把文字转成语音（微软 Edge 神经 TTS，免申请 key、免装服务）——支持中英日多语种音色、语速/音量/音调调节与字幕导出；当需要把文案或讲稿转成 mp3、给视频配音、做无障碍朗读、或指定音色与语速时自动启用。
---

# Edge-TTS

Generate high-quality text-to-speech audio using Microsoft Edge's neural TTS service via the `uvx edge-tts` command.
Supports multiple languages, voices, adjustable speed/pitch, and subtitle generation.

## 前置

```bash
# uvx 随 uv 一起提供，二者都没有时任选其一
pip install uv          # 或 Windows: winget install astral-sh.uv
uvx edge-tts --version  # 首次会拉取虚拟环境，需联网
```

下文命令里的 `{msg}` = 要朗读的文本，`{tempdir}` = 临时目录，`{filename}` = 输出文件名（不含扩展名），按实际替换。

## Usage
```shell
uvx edge-tts --text "{msg}" --write-media {tempdir}/{filename}.mp3

# With subtitles（- 表示字幕同时打到 stdout；给文件名则落盘为 .srt）
uvx edge-tts --text "{msg}" --write-media {tempdir}/{filename}.mp3 --write-subtitles {tempdir}/{filename}.srt
```

## Changing rate(speed), volume and pitch
```shell
uvx edge-tts --text "{msg}" --write-media {tempdir}/{filename}.mp3 --rate=+50%
uvx edge-tts --text "{msg}" --write-media {tempdir}/{filename}.mp3 --volume=+50% --pitch=-50Hz
```

## Changing the voice
```shell
uvx edge-tts --text "{msg}" --write-media {tempdir}/{filename}.mp3 --voice zh-CN-XiaoxiaoNeural
```

## Available voices
```
Name                               Gender    ContentCategories      VoicePersonalities
en-GB-LibbyNeural                  Female    General                Friendly, Positive
en-GB-RyanNeural                   Male      General                Friendly, Positive
en-GB-SoniaNeural                  Female    General                Friendly, Positive
en-GB-ThomasNeural                 Male      General                Friendly, Positive
en-HK-SamNeural                    Male      General                Friendly, Positive
en-HK-YanNeural                    Female    General                Friendly, Positive
en-US-AnaNeural                    Female    Cartoon, Conversation  Cute
en-US-AndrewMultilingualNeural     Male      Conversation, Copilot  Warm, Confident, Authentic, Honest
en-US-AndrewNeural                 Male      Conversation, Copilot  Warm, Confident, Authentic, Honest
en-US-AriaNeural                   Female    News, Novel            Positive, Confident
en-US-AvaMultilingualNeural        Female    Conversation, Copilot  Expressive, Caring, Pleasant, Friendly
en-US-AvaNeural                    Female    Conversation, Copilot  Expressive, Caring, Pleasant, Friendly
en-US-BrianMultilingualNeural      Male      Conversation, Copilot  Approachable, Casual, Sincere
en-US-BrianNeural                  Male      Conversation, Copilot  Approachable, Casual, Sincere
en-US-ChristopherNeural            Male      News, Novel            Reliable, Authority
en-US-EmmaMultilingualNeural       Female    Conversation, Copilot  Cheerful, Clear, Conversational
en-US-EmmaNeural                   Female    Conversation, Copilot  Cheerful, Clear, Conversational
en-US-EricNeural                   Male      News, Novel            Rational
en-US-GuyNeural                    Male      News, Novel            Passion
en-US-JennyNeural                  Female    General                Friendly, Considerate, Comfort
en-US-MichelleNeural               Female    News, Novel            Friendly, Pleasant
en-US-RogerNeural                  Male      News, Novel            Lively
en-US-SteffanNeural                Male      News, Novel            Rational
fr-FR-DeniseNeural                 Female    General                Friendly, Positive
fr-FR-HenriNeural                  Male      General                Friendly, Positive
zh-CN-XiaoxiaoNeural               Female    News, Novel            Warm
zh-CN-YunjianNeural                Male      Sports,  Novel         Passion
zh-CN-liaoning-XiaobeiNeural       Female    Dialect                Humorous
zh-CN-shaanxi-XiaoniNeural         Female    Dialect                Bright
zh-HK-HiuGaaiNeural                Female    General                Friendly, Positive
zh-HK-WanLungNeural                Male      General                Friendly, Positive
zh-TW-HsiaoChenNeural              Female    General                Friendly, Positive
zh-TW-YunJheNeural                 Male      General                Friendly, Positive
```

Retrieve all available voices using shell commands:
```shell
uvx edge-tts --list-voices
```

## 输出

```
{tempdir}/{filename}.mp3     音频（默认 24kHz 单声道，--rate/--volume/--pitch 已生效）
{tempdir}/{filename}.srt     字幕（仅当给了 --write-subtitles）
```

验收：`ffprobe -v error -show_entries format=duration <mp3>` 的时长应与文本长度量级相符；明显偏短多为文本被截断或网络中断。

## 排错

| 问题 | 现象 | 处理 |
|------|------|------|
| `uvx: command not found` | 命令不存在 | `pip install uv`；装完确认 `uv --version` 可用 |
| 首次运行卡住 | 拉取依赖慢 | 属正常，换镜像：`set UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple` |
| `ClientRequestError` / 超时 | 连接微软 TTS 服务失败 | 需能访问 `speech.platform.bing.com`；代理环境下先 `set HTTPS_PROXY=...`，仍失败则换 `speaker-diarization` 之外的本地 TTS |
| 语速/音调不生效 | 参数被忽略 | `--rate=+50%` 等必须带 `=`，且值要带 `%` 或 `Hz`（`--rate +50%` 会被当成文本） |
| 音色名无效 | 报 `Invalid voice` | 先 `uvx edge-tts --list-voices` 核对，不要凭下文快照猜 |
| 中文读音怪 | 多音字/英文混读 | 换 `zh-CN-XiaoxiaoNeural`/`zh-CN-YunjianNeural`；专有名词在文本里加空格或换写法 |

> 下文音色表是常见子集快照（33 条），完整列表以 `--list-voices` 为准。
