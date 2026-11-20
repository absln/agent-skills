# python-pptx 中文演示文稿 · 实战坑清单

> 全部条目均为**真实踩过的坑**（含本项目 `docs/gen_ppt.py` 的实际故障），按"症状 → 根因 → 处理"排列。

---

## 1. 生成类（脚本直接报错）

| 症状 | 根因 | 处理 |
|------|------|------|
| `SyntaxError: invalid character '、' (U+3001)` / `invalid syntax` 指向某个中文串 | 文案里把中文引号写成了 **ASCII `"`**，字符串提前闭合。真实案例：`("设计理念：不是"锁定不让你玩"，而是…")` | 生成前统一清洗：`re.sub(r'(?<=[\u4e00-\u9fff])"(?=[\u4e00-\u9fff])', '”', s)`；写文案一律用 `“ ”`，或整段用 `'''` 包裹 |
| `AttributeError: '_Background' object has no attribute 'solid'` | `slide.background` 是 `_Background`，需先取 `.fill` | `slide.background.fill.solid()` |
| `IndexError: list index out of range`（在 `p.runs[0]`） | 先 `p.text = ""` 再取 `runs[0]`；空段落没有 run | 一律 `r = p.add_run(); r.text = ...`，空行也不要取 `runs[0]` |
| `KeyError` / 形状画错位置 | `add_shape(1, ...)` 用魔术数字 | 改用 `from pptx.enum.shapes import MSO_SHAPE`，如 `MSO_SHAPE.OVAL` |
| 提示"文件被占用"/保存失败 | 目标 pptx 正在 PowerPoint 中打开 | 关闭文件后重跑；脚本里输出前可先试 `os.replace` |

---

## 2. 排版类（能生成但不好看/不对）

| 症状 | 根因 | 处理 |
|------|------|------|
| 代码里设了中文字体，PPT 里没生效（仍是宋体/等线） | `font.name` 只写 `<a:latin>`，中文走 `<a:ea>`（主题东亚字体） | 同时写 `a:latin`/`a:ea`/`a:cs`，见 `scripts/deck.py::_set_font` |
| 默认是 4:3，版面被压窄 | `Presentation()` 默认 10×7.5 英寸 | 显式 `slide_width=Inches(13.333); slide_height=Inches(7.5)` |
| 文字溢出到页外 | python-pptx **不做排版计算**，没有自动缩排 | 用 `refs/layout-guide.md` 的字数上限控量；交付前用 `inspect_pptx.py` 查溢出与文本量 |
| 表格列宽设了没用 | 参数需要 `Emu`/`Inches` 对象，且总宽受形状宽度约束 | `tbl.columns[i].width = Emu(...)`，或只设 `add_table(..., width=...)` 让各列均分 |
| 图片被拉伸变形 | 同时传 `width` 和 `height` 会强制缩放 | 只给一个维度（另一个自动等比），或先用 PIL 读出比例 |
| 形状带默认阴影/边框，风格不统一 | 自动图形继承主题效果 | `shape.shadow.inherit = False`；`shape.line.fill.background()` 去边框 |
| 页码重复/错乱 | 版式自带编号 + 自定义页脚同时存在 | 二选一；`deck.py` 默认关闭右下角页脚，改用内容页左上角编号 |

---

## 3. 模板套用类

| 症状 | 根因 | 处理 |
|------|------|------|
| 套了模板，新页接在模板原页后面 | `Presentation(tpl)` 保留模板全部 slide | 建 deck 后调 `strip_slides()`（删除自带页，保留母版/版式/主题），见 `deck.py` |
| 想用模板的某页版式却找不到 | 版式名是中文（`标题幻灯片` / `空白` / `标题和内容`） | 按名字挑：`for l in prs.slide_layouts: if l.name=='空白'` |
| 模板配色变了，表格文字看不清 | 自定配色与模板主题冲突 | 模板模式下只用模板主题色，或把 `theme` 配色显式覆盖到每个 run |
| 删除页后残留引用 | 只 `remove(sldId)` 不删关系 | 先 `prs.part.drop_rel(rId)` 再 `sldIdLst.remove(sldId)` |
| 套模板后模板装饰全没了 | 装饰画在 slide 上、不在母版；`strip_slides()` 只能继承主题 | 用 `keep_slides([...])` 真保留封面/感谢页，再 `set_template_text` 改字 |
| 新页全被追加到末尾 | python-pptx 只能 append | 建完内容后 `move_slide(原页索引, 末位)` 调序 |
| 想改模板文字却重建了文本框 | 重建会丢字体字号 | 先 `frame_texts(slide)` 看占位符原文，再 `set_template_text` 按原文字替换 |
| 生成物莫名几十 MB | 模板**内嵌了字体**（`ppt/fonts/*.fntdata`） | `unzip -l t.pptx \| grep ppt/fonts` 查；要瘦身用 `strip_embedded_fonts()` + `unify_fonts()` |
| 打开报 "Some of the embedded fonts… cannot be installed / Font Decompression Failed" | 内嵌字体是 **Office 专有压缩格式**（首 8 字节为两个尺寸字段，非 TTF/WOFF，`fontTools` 解析不了）。字节未坏但 PowerPoint 装不上，常见于 WPS 产出的模板 | **内嵌字体装不上 = 等于没嵌**（照样回退）。对策：**默认剔内嵌字体**（`strip_embedded_fonts()` + `unify_fonts()` 改微软雅黑），只当确认对方能装时才保留。验证：`python -c "import zipfile;print([n for n in zipfile.ZipFile('a.pptx').namelist() if n.startswith('ppt/fonts')])"` → 应为空 |
| 套模板后中文变 `等线` | 主题 `<a:ea typeface=""/>` 为空，属性“继承主题”≠“用模板自身字体” | 显式指定模板已内嵌的字体名（如 `思源黑体 CN` / `优设标题黑`） |

---

## 4. 交付类

| 项 | 做法 |
|----|------|
| 字体缺失回落 | 交付用系统自带字体（微软雅黑 / 等线 / Arial），**或**保留模板内嵌字体（先用 pitfalls 里的方法验证内嵌字体真能装） |
| 体积 | 内嵌字体的成品常在 60MB 级；要交邮箱/微信先确认限额，否则剔内嵌字体重生成 |
| 与讲稿一致性 | 演示文稿 `.md` 讲稿与 `.pptx` 必须同源同版；改一处同步另一处，勿双源 |
| 页数 | 汇报/答辩：**每页 1 屏、正文 ≤6 行、每行 ≤28 字**；8~10 分钟 ≈ 10~14 页 |

---

## 5. 生成前自检清单

- [ ] 文案中无 ASCII `"` 夹在中文之间（`grep -n '[一-龥]"[一-龥]'`）
- [ ] 已设 `13.333×7.5`（16:9）
- [ ] 所有中文 run 都写了 `a:ea`
- [ ] 无空段落取 `runs[0]`
- [ ] 跑过 `python #/skills/pptx-generation/scripts/inspect_pptx.py out.pptx`，issues = 0
- [ ] 另存 PDF 目视一遍
