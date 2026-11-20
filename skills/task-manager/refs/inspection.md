# 数据门禁巡检（存量体检）

> `task-manager` §11 的完整细则。只在真的执行巡检时读；主文件 §11 保留摘要与判据。
> **只报告，不修数据。**

## 11.1 规则

| 编号 | 规则 | 判定 | 严重度 |
|---|---|---|---|
| R1 | 必填缺失 | `title` 空 / `project_id` 空 / `task_type` 空 / `status=done` 但 `done_at` 空 | 高 |
| R2 | 分类非法 | `task_type` 不在 `software* / design / ip / daily`；`status` 不在 `todo/in_progress/blocked/done` | 高 |
| R3 | 状态与时间矛盾 | `status=done` 但 `done_at` 为空；`status!=done` 但 `done_at` 有值；`start_at > plan_end_at`；`done_at < start_at` | 高 |
| R4 | 长期停滞 | `status=in_progress` 且 `updated_at` 超过 `--days`（默认 14）未更新 | 中 |
| R5 | 逾期未流转 | `plan_end_at < 今天` 且 `status` 仍为 `todo/in_progress` | 中 |
| R6 | 关联断裂 | `refs` 含不存在的 issue id；`predecessors` 含不存在的 task id；issue `parent_id` 指向 bug | 中 |
| R7 | 批量补录嫌疑 | 同一项目内 ≥3 条任务的 `done_at` 落在同一秒 | 低（提示 `done_at` 不可信） |

## 11.2 执行

```
1. list_projects() → 项目表（判 R1 项目归属、R6 项目存在性）
2. list_tasks(offset, limit=100) 循环翻页至累计 ≥ total → 全量任务
3. list_issues(offset, limit=100) 循环翻页至累计 ≥ total → 全量问题
4. 按 R1–R7 逐条判定（纯本地计算，不再调用工具）
5. 输出巡检表到对话，或按用户要求落到 巡检-{YYYYMMDD}.md
```

> 巡检是**只读**的：只调 `list_*`，不得调用任何 `create_*` / `update_*`。

## 11.3 输出格式

```
## 巡检汇总
| 规则 | 命中 | 高 | 中 | 低 |
| R1 必填缺失 | 2 | 2 | 0 | 0 |
...

## 明细
| 规则 | 对象 | id | 证据（具体字段值） | 建议 |
| R1 | task | #41 | project_id=null, title="联调" | 补 project_id |
```

**证据列必须写具体字段值**，不允许只写「字段缺失」。

## 11.4 边界

| 不做 | 原因 |
|------|------|
| 不自动修数据 | 巡检只读；修数据需用户确认后逐条调用 |
| 不自动建整改任务 | 避免每次巡检都刷出一堆任务 |
| 不判业务对错 | 只判字段与状态一致性，不评价任务内容是否合理 |
| 不做绩效打分 | 与 §9 无关 |
| 不把 R7 当错误 | 批量补录是历史事实，只提示 `done_at` 取数不可信 |

---
