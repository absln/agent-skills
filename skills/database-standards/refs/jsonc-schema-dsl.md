# JSONC Schema DSL 详解

> 本文件是 `database-standards` 采用的 **JSONC → DDL 声明式 DSL** 的完整格式说明。
>
> 文中的 JSONC 片段只讲语法，**不是表结构示例**；可套用的真实表见 `examples/schemas/`（`templates/` 起步，`business/` 参考字段设计）。
>
> 这是一套**可选方案**：它以 JSONC 描述表结构，由脚本生成 DDL 与前后端模型，适用于「设计源唯一、禁止手写 DDL」的项目。若项目已使用 Alembic / Prisma / 手写 SQL 迁移，只需遵循主文件中的类型标准、命名规范与 SOP，无需引入本 DSL。
>
> 主文件保留摘要与判定要点，格式细节、语法表与生成规则在此。

---

## R1. 文件结构

每个 Schema 文件定义一个数据库表：

```jsonc
{
    "title": "table_name",          // 表名（必填，与文件名一致，snake_case）
    "description": "业务表说明",     // 表说明（必填）
    "type": "object",
    "$base": ["base"],              // 继承 base.jsonc 审计字段（业务表必填）
    "properties": {
        "id": {
            "type": "bigserial",
            "required": true,
            "primary": true,
            "description": "主键ID",
            "order": 1
        },
        "field_name": {
            "type": "<PostgreSQL 类型>",
            "required": true,           // 是否必填
            "default": "<默认值>",      // 默认值规则见 R4
            "primary": false,           // 是否主键
            "description": "字段说明",   // 中文描述（必填）
            "order": 10                 // 字段排序号（递增，步长建议 10）
        }
    },
    "required": ["id"]
}
```

### 表级属性

| 属性 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `title` | 是 | string | 表名，snake_case，与文件名一致 |
| `description` | 是 | string | 业务表的用途说明 |
| `type` | 否 | string | 固定 `"object"` |
| `$base` | 业务表必填 | string[] | 继承的 base 模板，默认为 `["base"]` |
| `hidden` | 否 | boolean | 是否为隐藏表（如元表），默认 false |

### 字段级属性

| 属性 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `type` | 是 | string | **PostgreSQL 类型名**（类型选择见主文件 §3） |
| `description` | 是 | string | 字段中文说明 |
| `required` | 是 | boolean | 字段是否必填（非空约束） |
| `primary` | 是 | boolean | 是否主键，每个表仅一个字段可设为 true |
| `default` | 否 | string | 默认值（规则见 R4） |
| `order` | 否 | number | 字段在 DDL 中的排列顺序，建议步长 10 |
| `ref` | 否 | object | 外键引用关系（语法见 R3） |

---

## R2. $base 继承机制

### 审计字段定义

`base.jsonc` 定义了所有业务表必须继承的 5 个审计字段：

| 字段 | 类型 | 说明 | order |
|------|------|------|-------|
| `create_time` | timestamp | 创建时间 | 995 |
| `update_time` | timestamp | 更新时间 | 996 |
| `create_by` | bigint | 创建用户 ID | 997 |
| `update_by` | bigint | 更新用户 ID | 998 |
| `status` | smallint | 状态枚举 | 999 |

### 使用方式

业务表 JSONC 仅需在顶层声明 `$base`，无需重复定义这 5 个字段：

```jsonc
{
    "title": "product",
    "description": "产品表",
    "$base": ["base"],
    "properties": {
        "id": { "type": "bigserial", "required": true, "primary": true, "description": "主键", "order": 1 },
        "name": { "type": "character varying(100)", "required": true, "description": "产品名称", "default": "", "primary": false, "order": 10 }
    },
    "required": ["id", "name"]
}
```

DDL 生成时，`base.jsonc` 的 5 个字段会自动合并到业务表中。

### 使用约束

- **系统元表**（如 `schema` 表自身）可以不继承 `base`。
- **关联表/中间表**视情况决定是否继承。
- 继承后，审计字段的 order 值在 DDL 中自动排到最后。

---

## R3. ref 外键关系

### 定义语法

在字段定义中添加 `ref` 对象声明表间外键：

```jsonc
"user_id": {
    "type": "bigint",
    "required": true,
    "description": "所属用户ID",
    "primary": false,
    "order": 20,
    "ref": { "entity": "user", "property": "id" }
}
```

| ref 属性 | 说明 |
|----------|------|
| `entity` | 引用的目标表名 |
| `property` | 引用的目标字段，通常为 `id` |

### 设计规则

- `ref` 仅用于 DDL 外键约束生成和代码文档标注，**不参与运行时逻辑**。
- 引用字段的类型必须与目标表主键类型一致（通常为 `bigint`）。
- `ref` 非必写，仅在确实存在外键约束时需要声明。

---

## R4. Default 值规则

JSONC 中的 `"default"` 按以下规则映射为 SQL DEFAULT 子句：

| JSONC default | 目标类型 | SQL 输出 | 说明 |
|:---|:---|:---|:---|
| `""` (空字符串) | INTEGER / REAL | `DEFAULT 0` | 数字类型默认为 0 |
| `""` (空字符串) | BOOLEAN | `DEFAULT FALSE` | 布尔类型默认为 false |
| `""` (空字符串) | TEXT / JSON | `DEFAULT ''` | 字符串类型默认为空串 |
| `""` (空字符串) | TIMESTAMP / DATE | **省略 DEFAULT** | 时间类型不设默认值 |
| `"0"` | 任意 | `DEFAULT 0` | 直接使用 |
| `"1"` | 任意 | `DEFAULT 1` | 直接使用 |
| `"false"` | BOOLEAN | `DEFAULT FALSE` | — |
| `"true"` | BOOLEAN | `DEFAULT TRUE` | — |
| `"CURRENT_TIMESTAMP"` | TIMESTAMP | `DEFAULT CURRENT_TIMESTAMP` | SQLite 原生支持 |

### 设计建议

- `status` 默认值统一为 `"1"`（Active 状态）。
- `create_time` / `update_time` 默认值统一为 `"CURRENT_TIMESTAMP"`。
- 空字符串 `""` 是通用兜底，尽量为具体类型选择更精确的默认值。
- **可空外键与 `parent_id` 切勿写 `default`。** `""` 对数字类型会生成 `DEFAULT 0`，而 `0` 不是合法外键值，插入即被外键约束拒绝；省略 `default` 才会得到 `NULL`。同理，`required: true` 的字段不要给 `default`，否则「必填」语义被默认值架空。

---

## R5. Status 枚举（统一值域）

所有业务表的 `status` 字段使用统一的值域：

| 值 | 名称 | 含义 | 使用场景 |
|:---|:---|:---|:---|
| `0` | Init | 新建/草稿/初始化/等待审核 | 资源创建后、审批流程中 |
| `1` | Active | 启用/正常使用/审核通过 | 正常运行态（默认值） |
| `50` | InActive | 停用/冻结/暂停 | 管理员停用、账户冻结 |
| `100` | Deleted | 软删除/驳回 | 软删除标记 |

### 设计规则

- 所有业务表**必须**通过 `$base` 继承 `status` 字段。
- **不设硬删除**，所有删除操作改为 `status = 100`（软删除）。
- API 查询接口默认过滤 `status != 100`，除非显式指定。
- 状态转换规则：
  - `0 → 1`：审核/激活（允许）
  - `1 → 50`：停用（允许）
  - `1 → 100`：删除（允许）
  - `0 → 100`：驳回/取消（允许）
  - `50 → 1`：重新激活（允许）
  - `100 → ?`：**禁止**从软删除恢复（如确需恢复，由管理员直接操作数据库）

---

## R6. 生成链路与校验

DSL 的产出必须是**完全确定**的，同一输入两次生成结果一致：

1. 读 `docs/schemas/**/*.jsonc`，合并 `$base`，按 `order` 排序。
2. 生成 DDL → 生成后端 Model → 生成前端类型，三方同源。
3. 校验：`title` 与文件名一致、`primary` 每表有且只有一个、`ref.entity` 指向存在的表、`required` 与 `default` 不矛盾（必填且无默认值的字段不得进 DDL 的非空列）。
4. 校验不通过则**中止生成**，不允许「生成一半再手改」——手改会在下次生成时被覆盖。
