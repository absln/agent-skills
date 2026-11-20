# 表格抽取要点（PDF / docx / pptx / xlsx）

表格是文档解析里最容易「解析成功但内容错」的部分：行错位、合并单元格吞列、跨页表头丢失。
`parse.py` 统一用 `table_to_md()` 把二维数组转 Markdown，遇到列数不一致**按众数列数对齐并记告警**，
而不是静默截断。

---

## 1. 各格式的可达精度

| 来源 | 手段 | 能做到 | 做不到 |
|------|------|--------|--------|
| `.pdf`（有表格线） | `page.extract_tables()` | 单元格还原，多页拼接 | 合并单元格的语义（只能靠对齐推断） |
| `.pdf`（无线框） | `page.extract_table({"vertical_strategy": "text"})` | 按文字对齐猜列 | 列数猜错；数字带千分位易错位 |
| `.pdf`（扫描件） | 渲染 → OCR | 只能「看懂内容」 | 行列结构基本丢失，不要当唯一依据 |
| `.docx` | `python-docx` 的 `table.rows[].cells` | 结构完整 | 嵌套表格需递归；合并单元格会重复返回同一 cell 文本 |
| `.pptx` | `shape.has_table` | 结构完整 | 表格跨页拼接需人工判断 |
| `.xlsx` | `openpyxl`（`data_only=True`） | 完整 | 公式取缓存值；图表/透视表不解析 |

## 2. 参数级细则（PDF）

```python
# 有框线（默认）
page.extract_tables()
# 无线框：按文字位置猜竖线
page.extract_tables({"vertical_strategy": "text", "horizontal_strategy": "text"})
# 调参顺序：先放宽 snap_tolerance（默认 3），再调 join_tolerance，最后才动 strategy
page.extract_tables({"snap_tolerance": 5, "join_tolerance": 5})
```

判定是否需要调参：抽出来的行有 1/3 以上单元格为空 → 换 strategy；列数忽多忽少 → 加 `snap_tolerance`。

## 3. 跨页表格

1. 相邻页表格列数相同且页眉行相同 → 视为同一张表，去掉重复表头后拼接；
2. 列数不同 → 不合并，各自成表，并在文中标注「（续）」；
3. 无法判断时保持原样分段，宁可多给两张表，不要错拼成一张。

## 4. 输出约定

- 一律 Markdown 表格，便于下游 diff 与 LLM 引用；
- 单元格内换行压成空格，`|` 转义为 `\|`；
- 合并单元格或列数不一致 → `warnings` 里写「哪张表、什么原因」，并体现在 `confidence` 的告警惩罚里；
- 表格数计入 `metadata.tables`（xlsx 记 `sheets`）。

## 5. 反模式

| 反模式 | 后果 |
|--------|------|
| 把 OCR 出来的表格当作结构化数据 | 列错位、数字粘连，统计必然错 |
| 跨页表强行合并 | 表头串行，行数翻倍 |
| 只保留左上角值却当成合并单元格的完整信息 | 语义丢失（应在文中注明「合并单元格已展平」） |
| 表格被渲染成图片后不提取 | 下游只看到「见附图」，等于没解析 |
