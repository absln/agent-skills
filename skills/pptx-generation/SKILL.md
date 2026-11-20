---
name: pptx-generation
description: 用 python-pptx 生成或修改真实 PowerPoint 演示文稿（.pptx）——含 16:9 设计令牌版式库、中文东亚字体设置、PPT 模板套用、结构质检与 PDF 校验；当需要生成答辩/汇报/路演/培训 PPT、把 Markdown 大纲转成 pptx、套用现有 PPT 模板、或排查"中文字体不生效 / 文字溢出 / 排版错乱"时自动启用。
---

# pptx-generation

用代码生成**能在 PowerPoint 里直接放映**的 16:9 演示文稿：先定内容与设计令牌，再用版式库组装，最后用质检脚本与 PDF 目视验收。

---

## 适用场景

| 触发条件 | 说明 |
|---------|------|
| "生成一份 PPT / 演示文稿 / 幻灯片" | 从大纲、文档或口头需求产出 `.pptx` |
| "把这份 md/讲稿做成 PPT" | Markdown 大纲 → pptx |
| "套用这个 PPT 模板" | `assets/科技风通用模板.pptx` 或用户提供的 .pptx 当主题 |
| "PPT 里中文变宋体了 / 字体不生效" | 东亚字体 `a:ea` 未设置 |
| "PPT 文字溢出 / 排版乱了" | 用 `inspect_pptx.py` 定位并调容量 |
| 需要交付 PPT 的正式场合（答辩、路演、汇报） | 要求 PDF 目视校验 |

| 不适用 | 原因 |
|--------|------|
| 只要 Markdown 讲稿，不做 pptx | 直接写 `.md`，不要引入本技能 |
| 要的是**画图**（架构图/ERD/流程图） | 用 `drawio-skill` |
| 要的是 Word 文档 | 用 `docx-generation` |
| 图片铺页式 PPT（一图一页） | 用 `drawio-skill`  |

---

## 执行步骤

### 1. 锁定输入（先不写代码）

```
收集并确认：受众 / 场景（答辩·汇报·路演）/ 时长 / 页数上限
内容来源：已有 md 讲稿 > 文档 > 用户口述（缺信息就问，不要编数据）
模板：用 assets/科技风通用模板.pptx，还是用户给的 .pptx，还是从零自建
产出清单：out.pptx + 同名 .md 讲稿（同源同版，禁止双源）
```

> 时长 → 页数：5 分钟 ≈ 6~8 页，8~10 分钟 ≈ 10~14 页，见 `refs/layout-guide.md` §6。
> 讲"现状-问题-方案-要什么"这类汇报时，先按 `refs/storyline.md` 排叙事线（标题即结论），再进大纲——
> 版式救不了没有论点的内容。

### 2. 先出大纲（Markdown，先确认再生成）

```
每行一个版式：封面 / 章节页 / 要点页 / 数字页 / 图文页 / 表格页 / 结尾
每页写：标题 + 3~6 条要点（每条 ≤ 28 字）
标出每页用到的素材（图片路径、数据来源）
→ 给用户确认大纲，再进入编码
```

### 3. 定设计令牌

```
主题：midnight（深色科技）/ light（浅色商务），或对齐作品/品牌主色
字体：中文用系统自带（微软雅黑 / 等线），英文 Arial —— 交付方无需装字体
字号：只用 标题 28 / 正文 18 两级，次级信息用颜色或 14 号
颜色：背景 + 标题 + 正文 + 强调 ≤ 4 种
```

### 4. 用版式库组装

```python
import sys; sys.path.insert(0, r"{skill}/scripts")
from deck import Deck

d = Deck(theme="midnight")                 # 或 Deck(template=r"{skill}/assets/科技风通用模板.pptx")
d.cover("作品名", "副标题", ["汇报人：XXX", "指导教师：YYY"])
d.title_content("标题", [("要点", "body"), ("关键结论", "accent"), ("旧方案", "dim")])
d.kpi([("66%", "命中率"), ("50个", "样本")])      # 数字页：先 title_content 再 kpi
d.closing("谢谢！", "一句话收束", "欢迎上手试玩")
d.save(r"out.pptx")
```

图文页 / 表格页要自己开页再贴（`image`/`table` 的第一个参数是 slide）：

```python
s = d.add_slide()                                   # 空白页
d.text(s, 0.9, 0.6, 11.5, 0.9, "架构总览", size=28)
d.image(s, "docs/temp/arch.png", 1.87, 1.7, w=9.6)  # w/h 二选一，同时给以 w 为准；16:9 图按 w 换算高须 ≤5.4，否则溢出页底
d.table(d.add_slide(), [["阶段", "产出"], ["设计", "SRS"]], 0.9, 1.7, 11.5, 2.4)
```

```
版式 → 方法：封面 cover(标题,副标题) / 章节 section(序号,标题) / 要点 title_content(标题,条目) / 数字 kpi(条目) / 结尾 closing(标题,收束)
图文与表格需先有 slide：image(slide, 图片路径, x, y, w=) / table(slide, 二维数组, x, y, w, h)
语义样式：body 陈述 · accent 关键结论 · dim 次要/已废弃 · lead 引导句（一页 accent ≤ 2 处）
完整坐标与容量上限：refs/layout-guide.md
```

#### 4.1 套用模板（保留模板原页）

模板的装饰（背景图/箭头/色块）画在 **slide 上而非母版**，所以 `strip_slides()` 只能拿到主题字体配色。
要“原味”，就用下面四个原语把模板页真正留下来：

```python
d = Deck(theme="techcyan", template=TPL, keep_template_slides=True)
d.keep_slides([0, 16])              # 只留模板封面页与感谢页（0-based，保持原序）
d.set_template_text(d.prs.slides[0], {      # 改写占位文字，保留原字体字号
    "科技风通用模板": "作品名",
    "汇报人：xxx": "演示人：XXX",
})
d.move_slide(1, d.slide_count - 1)  # 新页总追加在末尾 → 把感谢页调回最后
d.notes(slide, "【演讲提示】…")      # 写入备注，不占画面
```

| 原语 | 作用 |
|---|---|
| `keep_slides([i, j])` | 仅保留指定原页，其余删除 |
| `move_slide(i, j)` | 调页序（新页只能追加） |
| `set_template_text(slide, {...})` | 保留格式改写模板文字 |
| `frame_texts(slide)` | 先打印模板各框文字，找出要改的占位符 |
| `notes(slide, text)` | 写演讲者备注 |
| `strip_embedded_fonts()` | 剔除内嵌字体（常能从几十 MB 降到 1 MB 级） |
| `unify_fonts(path, {...})` | 保存后全文替换 typeface（与上一行配套用） |
| `strip_embedded_fonts(path, font_map)` | **文件级**剔内嵌字体（不用建 Deck，用于清理模板资产）；给了 font_map 会顺手 `unify_fonts` |
| `Deck(title_font=THEME_FONT)` | 不写字体、有意继承主题字体 |

**字体决策（套模板最容易翻车处）**：
0. **默认不保留内嵌字体**。很多模板的 `.fntdata` 是 Office 专有压缩格式，PowerPoint 会报
   “Cannot be installed / Font Decompression Failed”——装不上就等于没嵌，白担 60MB 体积。
   先查：`python -c "import zipfile;print([n for n in zipfile.ZipFile(r'模板.pptx').namelist() if n.startswith('ppt/fonts')])"`
   （本技能自带模板已清理干净，此步主要针对外部拿到的模板。）
1. 确认要保留时：内嵌字体可直接用其字体名，**换机不掉字体**（代价：文件大）。
2. 剔除内嵌字体时：`strip_embedded_fonts()` + `unify_fonts()` 全文改系统自带字体（微软雅黑），
   否则标题字体会回落宋体。
3. 不要想当然用主题继承：主题 `<a:ea typeface=""/>` 为空时，中文会回落到 `等线`，与模板自身字体不一致。

### 5. 质检（必做，不可跳过）

```
python {skill}/scripts/inspect_pptx.py out.pptx --text
  → issues 必须为 0（空 run / 只设 latin 缺 a:ea / 形状溢出 / 文本量超限）
```

> 注：“完全不写字体”（有意继承主题）不算缺陷，质检器只报“写了 latin 却没写 a:ea”这种中英不一致。

### 6. 交付

```
out.pptx（可放映）+ 同名 .md 讲稿（含【备注】提示）
告知：页数、时长匹配、使用的模板与字体、未完成项
若 PPT 由 md 讲稿派生：后续内容变更必须两边同步，禁止只改一边
```

---

## 常见错误

| 问题 | 现象 | 处理 |
|------|------|------|
| 中文引号写成 ASCII `"` | `SyntaxError: invalid syntax` 指向中文串 | 文案一律用 `“ ”`；见 `refs/pitfalls.md` §1 |
| `p.runs[0]` 空段落 | `IndexError` | 用 `p.add_run()` 写字 |
| 设了字体不生效 | PPT 里中文仍是宋体/等线 | 必须同时写 `a:latin`/`a:ea`/`a:cs`（`deck._set_font` 已处理） |
| 默认 4:3 | 版面两侧留黑 | 显式 13.333×7.5 |
| 文字溢出 | 放映时被裁 | 按容量上限控量 + 跑 `inspect_pptx.py` |
| 套模板后新页在最后 | 模板原页还在 | `Deck(template=...)` 默认已 `strip_slides()` |
| 文案与讲稿不一致 | 双源 | 以 md 讲稿为准，改后重生成 pptx |

---

## 技能内资源

| 路径 | 用途 |
|------|------|
| `scripts/deck.py` | 版式库（设计令牌 + 版式函数 + `inspect()` 自检）；`python deck.py` 生成 demo 自测 |
| `scripts/inspect_pptx.py` | 结构检查 / 质检 CLI（`--text` `--fonts` `--json`） |
| `assets/科技风通用模板.pptx` | 科技风通用模板（18 页样例：封面/目录/章节/数据页/时间线/感谢页 + 1 页字体配色说明；色板 2AF8FF 青 + 1D9AF8 蓝；来源 freepik）。**已做资产清理（2026-09-21）**：剔除了原文件内嵌的 8 个 `.fntdata`（63 MB，且在本机 PowerPoint 报 `Font Decompression Failed` 装不上），并把全部 typeface 统一为 微软雅黑——**65.8 MB → 2.0 MB**，18 页与 13 个媒体部件均保留。如需原版需重新下载 |
| `themes` 含 `techcyan` | 白底青蓝主题，对齐上述模板色板（新建页与模板页视觉衔接用） |
| `refs/layout-guide.md` | 16:9 坐标网格、字号阶梯、容量上限、版式清单、时长→页数、配色 |
| `refs/pitfalls.md` | 生成/排版/模板/交付四类实战坑清单与自检表 |
| `refs/storyline.md` | 步骤 2 之前：汇报叙事结构（铺垫-冲突-解法、标题写结论、三种骨架、视觉技法、叙事病） |

---

## 质量门槛

- [ ] 16:9（13.333×7.5），页数与时长匹配
- [ ] 中文 run 均设置 `a:ea`；字体为通用自带字体
- [ ] 每页正文 ≤ 6 行、每行 ≤ 28 字、`accent` ≤ 2 处
- [ ] `inspect_pptx.py` issues = 0
- [ ] 交付 `.pptx` 与 `.md` 讲稿一致，无第二份来源

---

## 禁止事项

| 禁止 | 说明 |
|------|------|
| 跳过大纲确认直接生成 | 版式返工成本高 |
| 编造数据/结论 | 缺失信息标注"待确认" |
| 只给 `.md` 却说"PPT 做好了" | 交付物必须是可放映的 `.pptx` |
| 把业务细节写进本技能 | 技能只存通用方法，项目文案归项目文档 |
| 同一份 PPT 维护两个内容源 | md 讲稿为准单向生成 |
