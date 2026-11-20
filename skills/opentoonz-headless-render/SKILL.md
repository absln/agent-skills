---
name: opentoonz-headless-render
description: 用 OpenToonz（tcomposer）无头渲染与生成 .tnz 场景：相机标定、素材出图、xsheet 列/单元格文字手术、逐帧像素验收；当需要通过命令行批量渲染 OpenToonz 场景、由脚本生成/改写 .tnz、或排查 tcomposer 不渲染/无产物/死等时自动启用。
---

# opentoonz-headless-render

用命令行（`tcomposer.exe`）+ 文本手术驱动 OpenToonz 场景，产出 PNG 序列；所有结论靠**像素验收**，不靠退出码。

---

## 适用场景

| 触发条件 | 说明 |
|---|---|
| 要用命令行批量渲染 OpenToonz 场景 | 无 GUI、可脚本化、可复现 |
| 需要脚本生成/改写 `.tnz`（相机、列、单元格） | 模板 + 定点文字手术，不做全量重写 |
| `tcomposer` 退出码 0 却没产物 / 卡住不返回 | 见「常见错误」1、2 |
| 素材（PSD/PNG）要按图层或序列出图 | 一次调用出多元素「接触表」 |

| 不适用 | 原因 |
|---|---|
| 有 GUI 手工做绑定/特效 | 本项目只做确定性、可复现的渲染 |
| 非 OpenToonz 渲染器（ffmpeg/AE） | 不同工具链 |

---

## 执行步骤

### 1. 环境与工作目录

```
先定位 tcomposer（Windows 默认在 `C:/Program Files/OpenToonz 1.7/stuff/tcomposer.exe`，
实际以 `where /r "C:\Program Files" tcomposer.exe` 结果为准；找不到 ⇒ 见「常见错误」末行）
tcomposer 的 cwd 必须是 OpenToonz 安装根（安装根/stuff 为 TOONZROOT）
参数：tcomposer.exe <场景.tnz> -o <输出..png> -range <from> <to> -TOONZROOT <安装根/stuff>
- help 用 -help（-h 无效）；-range 不含 to；输出文件名编号 = 场景帧号 + 1
```

### 2. 素材出图：一次调用出多个元素（接触表法）

```
构造「逐帧多元素」场景：第 f 帧只显示目标元素，10 列全部显式写 cells
  <cell>f 1 <level id='X'/>%04d <step></cell>
未被引用的填充列必须指向**自建的真空白序列**（旧 level 不是真空）
```

### 3. 相机标定（画布↔渲染映射）

```
渲染 4 个纯色色标（画布内已知坐标）→ 量测其渲染坐标 → 拟合 render = canvas×s + b
dpi=72 的 level：相机可见窗口（画布像素）= cameraSize × 72；相机中心是固定偏移（不可假设为画布中心）
```

### 4. 场景生成：模板文字手术

```
只改必要处：cameraSize/cameraRes、framecount、level 的名称+路径、各列 <cells>
改列引用而不是删列（删空列会破坏 xsheet 解析）；删 <meshColumn>（它会吃掉紧邻左列）
```

### 5. 渲染与验收

用技能自带脚本（自带正确 cwd，避开"退出码 0 却无产物"）：

```bash
python scripts/render_verify.py render --scene <绝对路径.tnz> --out <前缀..png>     --first 0 --last 24 --toonz-root <安装根>
python scripts/render_verify.py compare --a <渲染帧.png> --b <设计图.png> [--step 2]
```

```
验收口径：尺寸校验 + 与「设计图（Python 侧合成）」逐像素比对（alpha 不一致率、RGB 平均绝对差）
再按业务语义做自动判定（例：某元素差异框必须落在预期矩形内）
```

---

## 常见错误

| 问题 | 现象 | 处理 |
|---|---|---|
| cwd 不是安装根 | **退出码 0、无产物、CPU 空闲、无限死等**（当前工程按相对安装根存在 `profiles/env/<用户>.env`） | 统一 `cwd=安装根` |
| `<path>` 用正斜杠或相对路径 | 静默跳过（当作相对路径） | 一律**反斜杠绝对路径** |
| raster level 用单张图 | 不渲染（连字节相同的改名拷贝也不渲染） | 用**编号序列**：磁盘 `name.0001.png`，tnz 写 `name..png` |
| 图层级 level 只改 name 不改 path | 整幅 PSD 被当扁平图；层帧序列只有第 1 帧有效 | 路径必须带图层标记：`girl.psd` 取 `Head` 层 → `girl#Head.psd`；层帧序列 → `口型#frames.psd` |
| `<meshColumn>` 存在 | **紧邻其左侧的 levelColumn 整列消失**（该层完全不出现） | 生成场景时一律删除 meshColumn |
| 列的前后关系搞反 | 该被遮的没遮、该露的被盖 | 实测：**最左列在最底层**（右列覆盖左列） |
| 缺素材不报错 | 退出码 0 但画面缺东西 | 缺 level/帧一律**静默跳过** → 必须查像素，不能只看退出码 |
| `-range a b` 少一帧 | 以为含 `b` | 不含 `b`；输出编号 = 帧号 + 1 |
| bash 管道取退出码 | 拿到的是 `tail` 的退出码 | 重定向到日志文件后再看 `$?` |
| 找不到 `tcomposer.exe` | 命令直接 not found | 先 `where /r "C:\Program Files" tcomposer.exe` 定位；安装根 = 该 exe 上两级目录（`stuff` 的父目录） |

> 完整坑表与证据见 `refs/pitfalls.md`。

---

## 输出

```
<输出目录>/<前缀>.%04d.png     渲染帧（编号 = 场景帧 + 1）
<work>/calibration.json        画布↔渲染 映射（s / b）
<work>/verify.json             逐帧像素验收结果
```
