---
name: weekly-report
description: 周报 Excel 的版式规范与通用 xlsx 模板套用（列宽、字体、合并锚点、尾注、邮件正文版式；以及从任意带样式的模板复制生成新 xlsx 的完整流程）；当需要查周报 xlsx 的单元格坐标/样式细节、套用历史周报做样板、或基于现有 Excel 模板生成新文件并保留样式的，自动启用。取数、生成、校验流程一律走 task-manager §6，本技能只负责「这份表长什么样」。
---

# weekly-report（周报版式 + 通用 xlsx 模板套用）

> **本技能不负责取数与生成流程。** 周报的取数、行组装、校验由 `task-manager` §6 负责；**产出路径与文件命名归本技能 §1**（全库只此一处定义，其他地方引用不重抄）。
> 本技能回答两件事：
> 1. **周报这份 xlsx 长什么样**——坐标、列宽、字体、合并规则、邮件正文版式（§1–§2、§4）。
> 2. **从任意带样式的模板生成本文件**——复制继承 → 清区 → 写数 → 先设样式后合并 → 保存（§3，通用，非周报专属）。
> 姓名、项目清单、签名、称呼等一律**不在此维护**，运行时从 `list_users` / `list_projects` / 用户输入取。

---

## 1. 命名与路径

```
周报/{年}/研发周报-{结束日期}-{姓名}.xlsx    # 结束日期 = 本周五，YYYYMMDD
周报/{年}/研发周报-{结束日期}-{姓名}.md      # 邮件正文
```

- `{姓名}` 取 `list_users` 返回的 `name`，不写死。
- 结束日期格式 `YYYYMMDD`，对应区间为「本周一 ~ 本周五」。

---

## 2. 周报 Excel 版式（固定坐标）

### 2.1 区域与样式

| 区域 | 坐标 | 内容 | 样式 |
|---|---|---|---|
| 标题 | `C2:E2`（合并） | `研发周报` | 宋体 18 加粗，居中，行高 22.5 |
| 姓名标签 | `A4` | `姓名` | 宋体 11，thin 边框，居中 |
| 姓名值 | `B4:C4`（合并） | 当前用户姓名 | 同上 |
| 日期标签 | `D4` | `起始日期` | 同上 |
| 日期值 | `E4:G4`（合并） | 如 `3.30-4.3` | 同上 |
| 表头 | `A6:G6` | 序号 / 任务分类 / 项目名称 / 工作内容 / 交付物 / 下周工作计划 / 说明 | 宋体 11，thin 边框，居中 |
| 数据区 | `A7` 起 | 逐行任务 | 宋体 11，thin 边框；D/E/F/G 左对齐 + 自动换行 |
| 尾注 | `A{n}:G{n}`（合并，`n = 最后数据行 + 2`） | `研发周报及交付物将作为季度绩效考评以及年度绩效考评的依据！！！` | 宋体 11，无边框，居中 |

### 2.2 列宽（必须照抄）

```python
{'B': 9.4, 'C': 27.73, 'D': 40.88, 'E': 23.87, 'F': 47.0, 'G': 84.75}
```

### 2.3 合并规则

| 列 | 规则 |
|---|---|
| B 任务分类 | 同分类连续行合并 |
| C 项目名称 | 同项目连续行合并 |
| E 交付物 | 不合并，逐行填 |
| G 说明 | 不合并，逐行填 |

### 2.4 排序

先按 B 分类固定顺序（方案设计 → 软件开发 → 知识产权 → 其他工作），再按 C 项目名。

---

## 3. 从模板生成 xlsx（通用流程）

> 本节是**唯一事实源**：周报、以及任何"基于现有模板生成新 xlsx"的场景都走这里，不再另立技能。

### 3.1 三条原则（顺序关键）

1. **样式从模板 `shutil.copy` 来**——不新建 `Workbook`。新建必然丢样式。
2. **先取消合并 → 写值 → 设样式 → 最后重新合并**。合并后 `MergedCell` 属性只读，顺序反了必报错。
3. **合并按内容锚点自动分段**——不硬编码行号，行数变了才不炸。

> 原则 1 与步骤 5（手动设边框/对齐）不矛盾：**继承**指列宽、行高、字体族与字号、数字格式；**数据区**的边框与对齐仍需重设，因为模板里的空行往往没带完整边框。判断标准——模板改一次就跟着变的，继承；随数据行数变而扩张的，重设。

### 3.2 参数（换成实际值即可照抄）

```python
SRC = "<模板或最近一份历史成品>"      # 带完整样式的 xlsx
DST = "<新文件路径>"
sheet_name = "<以样板为准>"
data_start, data_end = 7, 30          # 数据区首末行（模板里现有的空行区间）
max_col = 7                           # 数据区总列数
center_cols = {1, 2, 3}               # 数据区中需居中的列号；其余左对齐 + 自动换行
tasks = [["1", "方案设计", "项目A", "xxx", "设计文档", "yyy", ""],
         ["2", "软件开发", "项目A", "zzz", "代码", "www", ""]]   # 每个子列表 = 一行，长度 ≤ max_col
```

**周报场景取值**：`SRC` = 最近一份历史周报（`周报/{年}/` 下日期最晚者）、`data_start = 7`（表头在 6）、`max_col = 7`、`center_cols = {1, 2, 3}`（A 序号 / B 分类 / C 项目名居中，D–G 左对齐换行）。

### 3.3 步骤

```python
import shutil, openpyxl
from openpyxl.styles import Side, Border, Alignment

# 1. 复制模板——保留全部样式
shutil.copy(SRC, DST)

# 2. 加载并改固定单元格（周报：更新 E4 日期区间、B4:C4 姓名）
wb = openpyxl.load_workbook(DST)
ws = wb[sheet_name]
ws['E4'] = '<新日期区间>'

# 3. 清理数据区：先记下合并区域，再 unmerge，再清值
merges = [(str(m), m.min_row, m.max_row, m.min_col, m.max_col)
          for m in ws.merged_cells.ranges if m.min_row >= data_start]
for m_str, _, _, _, _ in merges:
    ws.unmerge_cells(m_str)
for rr in range(data_start, data_end + 1):
    for cc in range(1, max_col + 1):
        ws.cell(rr, cc).value = None

# 4. 写入新数据，并把 data_end 收敛到实际最后一行
r = data_start
for row_data in tasks:
    for idx, val in enumerate(row_data, start=1):
        if val is not None and val != '':
            ws.cell(r, idx, val)
    r += 1
data_end = r - 1        # 后面 5/6/7 一律用它，避免把尾部空行也合并进去

# 5. 统一样式（边框 + 对齐）——必须在步骤 6 之前！
thin = Side(style='thin')
full_border = Border(left=thin, right=thin, top=thin, bottom=thin)
center = Alignment(horizontal='center', vertical='center', wrap_text=True)
left_wrap = Alignment(horizontal='left', vertical='center', wrap_text=True)
for rr in range(data_start, data_end + 1):
    for cc in range(1, max_col + 1):
        cell = ws.cell(rr, cc)
        cell.border = full_border
        cell.alignment = center if cc in center_cols else left_wrap

# 6. 按内容锚点重新合并
def merge_by_anchors(ws, col, data_start, data_end):
    """按列内容锚点合并：空值视为延续上一行值"""
    spans = []
    start = data_start
    last_val = ws.cell(data_start, col).value
    for rr in range(data_start + 1, data_end + 1):
        v = ws.cell(rr, col).value
        actual = v if v else last_val
        if actual != last_val:
            if rr - 1 > start:
                spans.append((start, rr - 1))
            start = rr
            last_val = actual
    if data_end > start:
        spans.append((start, data_end))
    for rs, re in spans:
        ws.merge_cells(start_row=rs, start_column=col, end_row=re, end_column=col)
    return spans

merge_by_anchors(ws, 2, data_start, data_end)   # B 任务分类
merge_by_anchors(ws, 3, data_start, data_end)   # C 项目名称

# 7. 周报专属：写尾注（行号动态）并合并 A:G
last = data_start - 1
for rr in range(data_start, data_end + 1):
    if ws.cell(rr, 1).value not in (None, ''):
        last = rr
note_row = last + 2                              # 最后数据行 + 2
ws.cell(note_row, 1, '研发周报及交付物将作为季度绩效考评以及年度绩效考评的依据！！！')
ws.merge_cells(start_row=note_row, start_column=1, end_row=note_row, end_column=7)

# 8. 保存
wb.save(DST)
```

> 步骤 7 的尾注是周报专属。通用场景无需，跳过即可。

### 3.4 常见错误

| 现象 | 原因 | 处理 |
|---|---|---|
| `AttributeError: 'MergedCell' object attribute 'value' is read-only` | 合并后才写值 / 动属性 | 先 `unmerge_cells` → 写值 → 设样式 → 再合并 |
| 合并后边框丢失 | 先合并、后设边框（合并区只剩左上角可写） | 步骤 5 必须在步骤 6 **之前** |
| 合并后对齐失效 | 同上 | 同上，边框与对齐一次批量设完 |
| 合并区域与内容不对齐 | 硬编码行号 / 空值未按延续处理 | 用 `merge_by_anchors`，检查空值延续逻辑 |
| 列宽、行高变回默认 | 新建 `Workbook` 而非复制样板 | 必须 `shutil.copy` |
| 只有第一个 sheet 正确 | 只处理了 `wb[sheet_name]` | 需要时遍历 `wb.worksheets` |
| 尾注位置错 | 硬编码行号 | 改为「最后数据行 + 2」动态计算 |
| 数据行数变了以后全乱 | 用 `insert_rows` / `delete_rows` 改模板结构 | 从空白模板区间写入，不动模板骨架 |

### 3.5 禁用操作

| 禁止 | 原因 |
|---|---|
| 手动创建 `Border` / `Alignment` 后逐个单元格散着设 | 应由模板继承或按 §3.3 步骤 5 批量设 |
| 合并后修改 `MergedCell` 属性 | openpyxl 只读 |
| 硬编码合并行号 | 数据行数一变就错，用 `merge_by_anchors` |
| 手动指定列宽 | 模板自带，覆盖即偏离模板 |
| 对数据区 `insert_rows` / `delete_rows` | 破坏模板结构，改为从空白模板区间写入 |

---

## 4. 邮件正文版式

```markdown
# 研发周报（{周一:%Y.%m.%d} - {周五:%Y.%m.%d}）

{称呼}，您好：

本周主要工作按项目汇总如下：

## {项目名}
- {工作内容要点 1}
- {工作内容要点 2}

下周计划：
- {下周任务 1}

详细见附件，有任何问题随时联系。

{当前用户姓名}
{职务}
{公司名}
```

- `{称呼}`、`{职务}`、`{公司名}` 由用户提供或从历史邮件正文沿用，**不在技能里写死**。
- 项目分组顺序取 `list_projects` 返回顺序（主项目在前、子项目随后），未归类项放最后。
- 每项目 1–3 条要点，不堆砌。

---

## 5. 边界

| 事项 | 归属 |
|---|---|
| 取数（本周完成 / 下周计划）、行组装、分类映射 | `task-manager` §6 |
| 生成后 10 条自检、行号↔task id 对照表 | `task-manager` §6.7 |
| 周报 Excel 版式坐标、列宽、字体、合并、邮件版式 | **本技能 §1–§2、§4** |
| 通用 xlsx 模板套用（复制继承 → 先样式后合并 → 保存） | **本技能 §3** |
| 其它格式的模板套用 | `pptx-generation`（pptx）/ `docx-generation`（docx） |
