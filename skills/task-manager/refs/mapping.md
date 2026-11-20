# task-manager 口径表

> 本文只放**固定枚举与口径**（任务类型、状态机、映射规则、取数区间）。
> 项目清单与成员清单**不入表**，一律实时取自 `list_projects` / `list_users`；本文任何 ID 都不作为依据。

---

## 1. 项目（projects）

**不在本文维护项目清单。** 项目随时会新增/改名/挂子项目，写死快照必然过期。

- 取数：`list_projects()` —— **不传 `parent_id`**（传 `parent_id=0` 只返回顶层主项目，子项目会被过滤掉；要全量就别传）。
- 字段：`id` / `code`（内部编号）/ `name` / `parent_id` / `owner_id` / `status` / `type`。
- 匹配顺序：先按 `name` 精确匹配 → 再按 `code` 匹配 → 再按 `name` 模糊匹配 → 都不中则**问用户**，禁止猜。
- 用户口头「某主项目 + 编号」（如「X 项目 37」）时，编号通常是子项目的 `code`：先全量列出，找 `code` 命中且 `parent_id` 指向该主项目的那条。
- `status=archived` 的项目仍可挂任务，但需在 `note` 注明「已归档项目」。

> **`project_id` 必填**：任务/Issue 都必须归属项目，没有「未归属」这种状态。归属不明先问用户；实在无法归类，挂到 `name` 含「内部管理 / 日常管理」的项目（按 `name` 匹配，不写死 ID）并在 `note` 说明原因。

## 2. 成员（users）

**不在本文维护成员清单。** 取数：`list_users()` → `id` / `name` / `email` / `role`。

- 指派前先 `list_users` 查实时 ID；姓名有重名或匹配不到时问用户，禁止编造 ID。
- 显示规则：`name || email` 回退。

## 3. 任务类型（task_types）

| code | name | 父级 | 周报分类 |
|------|------|------|---------|
| software | 软件研发 | — | 软件开发 |
| software.requirement | 需求 | software | 软件开发 |
| software.analysis | 分析 | software | 软件开发 |
| software.tracking | 跟踪 | software | 软件开发 |
| software.code | 代码 | software | 软件开发 |
| software.test | 测试 | software | 软件开发 |
| design | 方案设计 | — | 方案设计 |
| ip | 知识产权 | — | 知识产权 |
| daily | 日常 | — | 其他工作 |

## 4. 任务状态机（tasks.status）

```
todo → in_progress → done
   ↘ blocked（受阻，note 写阻塞原因）→ in_progress
```

| status | 含义 |
|--------|------|
| todo | 待办 |
| in_progress | 进行中 |
| blocked | 受阻 |
| done | 已完成（done_at 自动写入/清空） |

- 优先级：`low / medium / high / urgent`（默认 medium）。

## 5. Issue 状态机（issues.status）

| status | 含义 |
|--------|------|
| draft | 草稿 |
| review | 评审 |
| confirmed | 已确认 |
| fixing | 修复中（Bug） |
| closed | 已关闭 |
| cancelled | 已取消 |

- Issue 类型：`requirement / feature / test_case / bug`。

## 6. 工作日志 → 落点映射

| 日志标签 | task_type | project_id |
|---------|-----------|------------|
| [项目] 需求/沟通/方案 | design | 对应项目 |
| [项目] 编码/开发 | software.code（或 software.*） | 对应项目 |
| [专利] | ip | 内部管理类项目 |
| [其他] 日常 | daily | 内部管理类项目 |

> 项目归属不明确：**不得留空**。先问用户；实在无法归类，挂到 `name` 含「内部管理 / 日常管理」的项目，并在 `note` 写「归属待确认：{原因}」。

## 7. 周报/季报取数口径

- 本周做了什么：`list_tasks(done_from=<周一>T00:00:00+00:00, done_to=<下周一>T00:00:00+00:00)`
- 下周计划：同区间但用 `start_from/start_to`（计划开始时间）
- 本季度：季度首日 → 下一季度首日，同上
- 区间**左闭右开**，时间格式 ISO `YYYY-MM-DDTHH:MM:SS+00:00`
