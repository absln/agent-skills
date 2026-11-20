# 台词样板 / Example scripts

本目录只放 `render-script` 的输入样板：9 份已复核的 `script.json`，中、英、韩各 3 份。成品图不随库分发（会随源视频权利变动），需要时按下面命令自己出图。

```bash
python3 scripts/native_subtitle_stitch.py render-script VIDEO \
  --script examples/scripts/zh/chen-shu-simple-life.json \
  --out example.jpg --aspect 3:4 --width 1440
```

把 `VIDEO` 换成你有权处理的视频路径。样板里的时间点是原视频的绝对秒数，只对原片成立；换视频必须重新定位时间点，不要照搬。`source_text` 字段是人工转录的原文，只用于核对，不参与渲染。

## 中文样板

| 样板 | 字幕模式 | 来源 | 台词文件 |
| --- | --- | --- | --- |
| 《大巴上的女孩》：生命属于你自己 | 原生字幕 · 中英双语 · 5 句 | [Bilibili 搬运视频](https://www.bilibili.com/video/BV1jT42117zW/) | [json](scripts/zh/girls-on-the-bus-native.json) |
| 里克·鲁宾：创意像一片变化的云 | 脚本字幕 · 中文翻译 · 5 句 | [YouTube](https://www.youtube.com/watch?v=QP8Kpf1UQwM) | [json](scripts/zh/rick-rubin-creative-clouds.json) |
| 陈数：工作投入，生活简单 | 脚本字幕 · 据原字幕整理 · 5 句 | [网易谈心社 / Bilibili](https://www.bilibili.com/video/BV1Ym4y1W7CJ/) | [json](scripts/zh/chen-shu-simple-life.json) |

## English samples

| Sample | Mode | Source | Script |
| --- | --- | --- | --- |
| Mikayla Johnson: Define the outcome first | Scripted · edited English · 5 lines | [YouTube](https://www.youtube.com/watch?v=5JOL8qYed-c) | [json](scripts/en/mikayla-johnson-define-outcome.json) |
| Rick Rubin: Be yourself, not a mask | Scripted · edited English · 5 lines | [YouTube](https://www.youtube.com/watch?v=butCyO_LccY) | [json](scripts/en/rick-rubin-be-yourself.json) |
| Darby Saxbe: Share the load early | Scripted · edited English · 5 lines | [YouTube](https://www.youtube.com/watch?v=Ppyt3MptX5k) | [json](scripts/en/darby-saxbe-shared-care.json) |

## 한국어 예시

| 예시 | 모드 | 출처 | 대본 |
| --- | --- | --- | --- |
| 마수드 후세인: 모든 행동 앞에는 시작의 언덕이 있다 | 스크립트 자막 · 한국어 번역 · 5줄 | [YouTube](https://www.youtube.com/watch?v=58-k4F7-AoA) | [json](scripts/ko/masud-husain-starting-hill.json) |
| 코디 산체스: 3-2-1 말하기 | 스크립트 자막 · 한국어 번역 · 5줄 | [YouTube](https://www.youtube.com/watch?v=t260757b_vU) | [json](scripts/ko/codie-sanchez-321-speaking.json) |
| 이나야 맥밀런: 돈의 운영체제 | 스크립트 자막 · 한국어 번역 · 5줄 | [YouTube](https://www.youtube.com/watch?v=U81bsDC8oP0) | [json](scripts/ko/inaya-mcmillan-money-program.json) |

样板内容均为后期整理或翻译，不是视频原字幕，也不作为人物的逐字引语。

## 权利说明 / Rights / 권리 안내

样例台词与来源链接只用于演示输入格式。画面、人物肖像、节目标识与台词的权利归各自权利人，本仓库的 MIT 许可证不授予这些素材的使用权，原视频也不随仓库分发。

The sample scripts demonstrate the input format only. Footage, likenesses, logos, and quoted text remain subject to their respective rights holders; the repository's MIT license grants no rights to this material, and source videos are not included.
