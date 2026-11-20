---
name: database-standards
description: 数据库设计规范 — 覆盖 JSONC Schema 定义、数据类型映射、$base 继承、ref 外键关系、Status 枚举、Default 值规则、迁移文件规范与数据库设计 SOP；当新建或修改数据库表、设计字段与类型、写迁移 SQL、定义状态枚举或软删除策略时自动启用。
---

# 数据库设计规范

本文件是项目数据库的**全域设计规范**，定义 Schema JSONC 格式、类型映射规则、命名约定和数据库设计工作流。所有数据库建模和DDL都必须遵循此规范。

---

## 1. 核心原则

### 1.1 设计源与真实来源（SSOT）

- **`docs/schemas/`** 下的JSONC文件是数据库模型的**单一真实来源（SSOT）**。
- 所有数据库的DDL、CRUD都严格从JSONC **自动生成**，禁止手动编写 DDL。
- 修改数据库结构必须先修改JSONC，再重新生成代码文件。

### 1.2 设计原则

1. **先 Schema 后代码** — 数据结构定义在前，Model和后端代码在后，两者保持同步。
2. **JSONC 即契约** — JSONC 定义的结构同时约束了 DDL、Model 和前端类型，三方统一。
3. **Base 继承复用** — 所有业务表必须通过 `$base` 继承审计字段，禁止在每个表中重复定义。
4. **Status 语义统一** — 所有表共用同一套 Status 值域，为 API 层提供一致的软删除/启停状态管理。
5. **字段名即列名** — JSONC 中的 property key 直接映射为 DDL 列名，命名时需考虑 SQL 兼容性。

---

## 2. JSONC Schema 格式（摘要）

> 完整格式、属性表与生成校验见 `refs/jsonc-schema-dsl.md`（R1、R6）。

采用本 DSL 时，每个 `.jsonc` 文件定义一个表，最少包含：

```jsonc
{
    "title": "product",                 // 表名，snake_case，与文件名一致
    "description": "产品表",
    "$base": ["base"],                  // 继承审计字段（见 §4）
    "properties": {
        "id":    { "type": "bigserial", "required": true, "primary": true, "description": "主键", "order": 1 },
        "name":  { "type": "character varying(100)", "required": true, "description": "产品名称", "default": "", "order": 10 }
    },
    "required": ["id", "name"]
}
```

判定要点：

- `type` 用 **PostgreSQL 类型名**，不是 DB 抽象类型（映射见 §3）
- 每表有且只有一个 `primary: true`；`order` 建议步长 10
- `title` 必须与文件名一致，否则生成时无法定位
- 生成是单向的：改 `.jsonc` → 重新生成，**不得手改生成物**

---

## 3. PostgreSQL 类型标准

JSONC Schema 中的 `type` 字段以 **PostgreSQL 类型**为标准。这是设计语言，不是实现约束：

- **PostgreSQL**：类型名直接用于 DDL，无需转换
- **SQLite**：兼容 PostgreSQL 类型名——SQLite 的类型亲和性使其接受几乎所有 PG 类型名作为列类型

| JSONC type（PG 标准） | SQLite 兼容映射 | 说明 |
|:---|:---|:---|
| `bigserial` | `INTEGER PRIMARY KEY AUTOINCREMENT` | 自增主键 |
| `serial` | `INTEGER PRIMARY KEY AUTOINCREMENT` | 自增主键 |
| `bigint` | `INTEGER` | 64 位整数 |
| `integer` / `int` | `INTEGER` | 32 位整数 |
| `smallint` | `INTEGER` | 16 位整数 |
| `boolean` / `bool` | `BOOLEAN` | SQLite 存 0/1，后端自动转换 |
| `character varying(N)` | `VARCHAR(N)` | N 为前端 maxlength 提示 |
| `character` / `char` | `TEXT` | — |
| `text` | `TEXT` | — |
| `json` / `jsonb` | `JSON` | — |
| `timestamp without time zone` | `TIMESTAMP` | 统一存 UTC ISO 8601 |
| `date` | `DATE` | — |
| `decimal` / `decimal(N,M)` | `REAL` | ⚠️ 精度可能丢失，金融场景用 `bigint` 存分 |
| `real` | `REAL` | — |
| `double precision` | `REAL` | — |

### 3.1 类型选择原则

- **主键**：统一使用 `bigserial`，不推荐 `serial`，为扩展预留空间。
- **整数**：按实际取值范围选 `smallint` / `integer` / `bigint`，避免一律用 `bigint`。
- **文本**：固定长度用 `character varying(N)`（N 取合理值），变长/长文本用 `text`。
- **金融/精确计算**：避免 `decimal` 的精度问题，改用 `bigint` 存分（整数分）。
- **时间**：统一 `timestamp without time zone`，存储 UTC ISO 8601 字符串。

---

## 4. $base 审计字段（摘要）

> 字段定义与合并规则见 `refs/jsonc-schema-dsl.md` R2。

所有业务表通过 `"$base": ["base"]` 继承 5 个审计字段，**禁止在各表中重复定义**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `create_time` / `update_time` | timestamp | 创建/更新时间 |
| `create_by` / `update_by` | bigint | 创建/更新用户 ID |
| `status` | smallint | 状态枚举（见 §7） |

系统元表可不继承；关联表视情况决定。继承字段在 DDL 中排在业务字段之后。

---

## 5. ref 外键关系（摘要）

> 语法与规则见 `refs/jsonc-schema-dsl.md` R3。

外键在字段上声明，不靠命名猜测：

```jsonc
"user_id": { "type": "bigint", "required": true, "description": "所属用户ID", "primary": false, "order": 20,
             "ref": { "entity": "user", "property": "id" } }
```

- `ref` 只用于生成外键约束与文档标注，不参与运行时逻辑
- 引用字段类型必须与目标表主键一致

---

## 6. Default 值规则（摘要）

> 完整映射表见 `refs/jsonc-schema-dsl.md` R4。

- `status` 默认 `"1"`（Active）；`create_time`/`update_time` 默认 `"CURRENT_TIMESTAMP"`
- 时间类型不加默认值；数字/布尔用具体值而非空串兜底
- `default` 是字符串，不是 JSON 字面量——`"0"` 而非 `0`

---

## 7. Status 枚举（统一规范）

> 完整值域与状态机见 `refs/jsonc-schema-dsl.md` R5。
>
> 本节是**数据层业务状态**，与 HTTP 状态码无关（HTTP 码见 `http-api-standards` §4）。禁止把 `0/1/50/100` 当错误码使用。

| 值 | 名称 | 含义 |
|:---|:---|:---|
| `0` | Init | 新建/草稿/待审核 |
| `1` | Active | 启用/正常（默认） |
| `50` | InActive | 停用/冻结 |
| `100` | Deleted | 软删除/驳回 |

**不设硬删除**；API 默认过滤 `status != 100`；软删除后不可恢复。

---

## 8. 字段命名规范

### 8.1 基本约定

| 规则 | 说明 | 示例 |
|------|------|------|
| snake_case | 全小写 + 下划线分隔 | `user_name`、`order_status` |
| 英文命名 | 使用英文简写，表意优先 | `is_deleted` ✅ `is_del` ❌ |
| 禁止保留字 | 避免 SQL/JSON 保留字 | 遇到时用双引号包裹 `"type"`，禁止自动改名 |
| ID 后缀规范 | 引用外键统一 `{entity}_id` | `user_id`、`product_id` ✅ `uid`、`pid` ❌ |
| 布尔前缀 | 布尔字段以 `is_` / `has_` / `can_` 开头 | `is_active`、`has_permission` |
| 时间后缀 | 时间字段以 `_time` 结尾 | `create_time`、`expire_time` |
| 数量后缀 | 数量字段以 `_count` / `_num` 结尾 | `view_count`、`order_num` |

### 8.2 禁止事项

| 禁止 | 说明 |
|------|------|
| 拼音命名 | 全部使用英文，禁止拼音缩写 |
| 前缀下划线 | 字段名不以 `_` 开头（那是后端语言私有成员的约定） |
| 大写字母 | 不在列名中使用大写（SQLite 大小写不敏感但应统一） |
| 中划线 | 不用 `-`，一律用 `_` |

---

## 9. 文件组织结构

### 9.1 项目中的 Schema 目录（SSOT）

```
docs/schemas/（项目的 SSOT，结构随项目演进）
├── base.jsonc             ← 审计字段模板（从本技能的 examples/ 中复制）
├── schema.jsonc           ← 元表定义模板（如项目需要）
└── {业务域}/               ← 按业务域组织
    ├── {table_a}.jsonc
    └── {table_b}.jsonc
```

### 9.2 技能内置示例

本技能自带 JSONC 建模示例，作为参考模板（位于本技能目录下 `examples/schemas/`）：

```
examples/schemas/
├── README.md              ← 使用说明
├── templates/             ← 符合规范的通用模板（新项目由此复制）
│   ├── base.jsonc         # 审计字段模板（$base 继承源）
│   └── schema.jsonc       # 元表定义模板
└── business/              ← 模式示例（每个对应 §12 / §15 的一种表模式）
    ├── category.jsonc     # 树形表：parent_id 自引用 + path/level
    ├── product.jsonc      # 标准业务表：$base + 主键 id + 外键 category_id
    ├── user.jsonc         # 标准业务表：字段命名示范
    ├── product_owner.jsonc # 关联表：双边 ref + 业务属性 → 继承 $base
    └── dict.jsonc         # 字典表：parent 字符串分组
```

> `business/` 下的 5 个示例**全部符合本规范**（`$base` 必填、主键统一 `id`、外键 `{entity}_id` 且类型与目标主键一致），彼此 `ref` 互相指向真实存在的表，可直接作为新表骨架照抄。它们刻意不含 `sys_` 前缀——示例讲的是**模式**，不是某套系统设计表。

### 9.3 文件命名

- 一个 JSONC 文件定义一个表，文件名 = 表名（`snake_case`）。
- 示例：`user_profile.jsonc` → 表名 `user_profile`。

---

## 10. DDL文件规范

### 10.1 目录与命名

```
api/sql/
└── {序号}_{描述}.sql
```

- 序号格式：`001`、`002`、`003`...（三位数，零填充）
- 描述：英文 snake_case 简要说明
- 示例：
  - `001_system_tables.sql` — 系统级表初始化
  - `002_add_product_table.sql` — 新增产品表

### 10.2 DDL文件内容

迁移 SQL 由后端 DDL 生成器自动生成，但需遵循以下约定：

- 每条 SQL 语句以 `;` 结尾。
- 包含 `CREATE TABLE IF NOT EXISTS`（幂等），而非纯 `CREATE TABLE`。
- 包含必要的索引创建语句。
- 升级迁移文件**只追加不修改**，回退迁移单独编写。

### 10.3 DDL执行原则

1. 迁移文件按序号顺序执行，不可跳过。
2. 已执行的迁移不可再修改，需要变更时应新增迁移文件。
3. 迁移通过后端迁移脚本或 CLI 命令自动执行，无需手动管理 SQL 文件。

---

## 11. 数据库设计 SOP（标准工作流）

新增一个数据库表时，按以下步骤执行：

### 阶段一：分析需求

1. **明确业务实体** — 确认要建模的业务对象及其属性
2. **确定归属** — 判断应放入 `docs/schemas/` 下哪个业务域目录（分类由项目定义）
3. **检查已有 Schema** — 翻阅 `docs/schemas/` 下同类目录，确认无重复建模

### 阶段二：编写 JSONC Schema

4. **创建 JSONC 文件** — 在对应业务目录下创建 `{table_name}.jsonc`
5. **声明基本属性** — `title`、`description`、`$base`
6. **定义主键** — `id` 字段，类型 `bigserial`
7. **定义业务字段** — 每个字段包含 `type`、`required`、`primary`、`description`、`order`
8. **声明外键** — 对引用其他表 ID 的字段添加 `ref`
9. **设置默认值** — 按 §6 规则为每个字段设置 `default`
10. **自检**：
    - [ ] 文件位置是否正确（归属目录）
    - [ ] `$base` 是否声明（业务表必须）
    - [ ] 字段名是否 snake_case
    - [ ] 类型是否从 PostgreSQL 类型映射表中选择
    - [ ] 外键字段类型与目标表主键一致
    - [ ] `description` 为空中文说明

### 阶段三：生成与验证

11. **运行 DDL 生成器** — 从 JSONC 生成迁移 SQL
12. **审查迁移 SQL** — 人工检查生成的 DDL 是否符合预期
13. **执行迁移** — 在开发环境中执行，验证表结构
14. **定义后端 Model** — 在 `api/models/` 下创建对应的 `{entity}` 模型文件（如 Pydantic BaseModel、dataclass 等）
15. **编写集成测试** — 验证新建表的 CRUD 操作

---

## 12. 常见表结构模式

| 模式 | 关键点 | 现成示例 |
|------|--------|----------|
| 标准业务表 | `$base` + 主键 `bigserial` + `name` + `description` + 状态字段 | `business/product.jsonc`、`user.jsonc` |
| 树形表 | `parent_id`（`ref` 自引用）+ `path` + `level`，三者同时维护 | `business/category.jsonc` |
| 关联/中间表 | 两侧 `{entity}_id` 均 `ref`，继承 `$base` 视是否带业务属性而定 | `business/product_owner.jsonc` |
| 字典表 | `parent` 字符串分组 + `key`/`value`，层级场景才用 `parent_id` 自引用 | `business/dict.jsonc` |

> 不再另存模板副本——`examples/schemas/` 就是唯一示例来源，改规范时只改那里。

---

## 13. 质量门槛

数据库设计交付前逐项自检：

### 13.1 定性标准

- [ ] **命名规范**：表名/字段名符合 snake_case，无拼音、无特殊字符
- [ ] **Base 继承**：业务表正确声明 `$base: ["base"]`
- [ ] **类型一致**：JSONC type 从 PostgreSQL 类型映射表中选择
- [ ] **外键匹配**：`ref` 的 entity/property 指向存在的表和字段
- [ ] **Default 合法**：默认值符合 §6 映射规则
- [ ] **Status 字段**：无需手动定义，由 $base 继承
- [ ] **Description 完整**：每个字段和表都有中文 description
- [ ] **Order 有序**：字段 order 值递增，步长合理
- [ ] **无冗余字段**：审计字段不重复定义
- [ ] **目录正确**：JSONC 文件放在正确的业务目录下

### 13.2 量化标准

| 质量维度 | 度量指标 | 合格标准 |
|---------|---------|---------|
| **命名** | 命名规范符合率 | 100% |
| **完整性** | 字段 description 覆盖率 | 100% |
| **类型** | 类型映射正确率 | 100%（生成 SQL 可执行） |
| **继承** | 业务表 $base 声明率 | 100% |
| **约束** | 外键/非空约束合理性 | 100% |

---

## 14. 禁止事项

| 禁止 | 说明 |
|------|------|
| 手动编辑迁移 SQL | 迁移文件由 DDL 生成器生成，禁止手动修改 |
| JSONC 外定义字段 | 所有数据库字段必须在 JSONC 中定义，禁止直接在后端 Model 中增加 |
| 跳过 $base | 业务表必须继承 base.jsonc 审计字段（关联表除外） |
| 自定义 status 值域 | 所有表统一使用 0/1/50/100，禁止为单表定义特殊的 status 枚举 |
| 拼音字段名 | 字段名全部英文，禁止拼音 |
| 硬删除 | 禁止物理删除数据，所有删除改为 status=100 软删除 |
| 类型不匹配 | 外键字段类型必须与目标主键一致 |
| JSONC 中引入非标准类型 | 只能使用 §3 映射表中列出的 PostgreSQL 类型名 |

---

## 15. 隐性知识与设计经验

以下经验从实际项目中提炼，补充 SKILL.md 正文难以覆盖的隐性知识。

### 15.1 树形表设计（parent_id + path + level）

简单 `parent_id` 自引用只能表达父子关系，**查询子树/全路径需要递归 CTE**，性能差。推荐补两个冗余字段：

| 字段 | 类型 | 作用 |
|------|------|------|
| `parent_id` | bigint | 父节点 ID（NULL = 根） |
| `path` | varchar | 从根到当前节点的 ID 路径，如 `/1/3/7` |
| `level` | smallint | 层级深度（根 = 0） |

**为什么加 path**：`WHERE path LIKE '/1/%'` 一次查询拿下整棵子树，无需递归。
**为什么加 level**：`WHERE level <= 2` 限制最大深度，防止前端一次性加载过深树。

```jsonc
"parent_id": { "type": "bigint", "description": "父级ID，NULL为根", "ref": { "entity": "{self}", "property": "id" }, "order": 5 },
"path": { "type": "character varying(500)", "description": "ID路径如 /1/3/7", "order": 6 },
"level": { "type": "smallint", "description": "层级深度，根=0", "order": 7 }
```

> 示例参考：`examples/schemas/business/category.jsonc`

### 15.2 地址数据分层（省/市/区三级）

中国地址的省→市→区是固定的三级层级。设计要点：

- **三层各一张表**（sys_province / sys_city / sys_district），不做单表 parent_id 树
- 市级用 `province_id` 引用省，区级用 `city_id` 引用市
- 每表设 `code` 字段存国标行政区划代码
- **只读数据**——不通过 `$base` 继承 status（无需软删除），或设为 status=1 写死

```jsonc
// 以市表 sys_city 为例
"province_id": { "type": "bigint", "ref": { "entity": "sys_province", "property": "id" }, "description": "所属省份" },
"code": { "type": "character varying(6)", "description": "行政区划代码" }
```

> 本技能不另存省市区示例文件——三表同构，上面的字段片段已覆盖全部设计点；层级树一般场景直接用 `business/category.jsonc`。

### 15.3 字典表设计（key-value + parent 分组）

系统字典的核心是 key-value 对，但同类字典需要分组管理。

| 场景 | 方案 |
|------|------|
| 简单枚举 | 硬编码在代码中 |
| 业务字典（可动态增删） | 字典表 + `parent` 字符串分组 |
| 层级字典 | 字典表 + `parent_id` 自引用 |

`parent` 用字符串而不用 FK 的原因：分组名是业务语义（如 "gender"、"order_status"），不是一个独立实体。

```jsonc
"parent": { "type": "character varying(50)", "description": "分组标识如 gender" },
"key": { "type": "character varying(50)", "description": "字典键" },
"value": { "type": "character varying(100)", "description": "字典值" },
"sort": { "type": "integer", "description": "排序号" }
```

> 示例参考：`examples/schemas/business/dict.jsonc`

### 15.4 多语言表设计（module + key + locale）

国际化文本用三元组定位：哪个模块→哪个键→哪种语言。

```jsonc
"module": { "type": "character varying(50)", "description": "模块名" },
"key": { "type": "character varying(100)", "description": "文本键" },
"locale": { "type": "character varying(10)", "description": "语言代码 zh-CN/en-US" },
"value": { "type": "text", "description": "翻译文本（支持 JSON 含变量占位）" }
```

唯一约束：`(module, key, locale)` 联合唯一。

> 本技能不另存多语言示例——它与字典表同构（三元组 + 联合唯一），差异只在校验维度和值类型，参照 `business/dict.jsonc` 改写即可。

### 15.5 通知表设计（消息与已读状态分离）

通知有两个关注点：消息内容（不随用户变）和已读状态（随用户变）。

| 表 | 职责 |
|----|------|
| notification（通知消息） | 标题、内容、类型、发送时间 |
| notification_read（已读状态） | user_id + notification_id + read_at |

**为什么分离**：一条通知发 1000 个用户，不分离则消息内容重复 1000 条。

> 本技能不另存通知示例——要点是**拆两张表**，单表写法是已知的错误示范，不宜作为模板保存。

### 15.6 审计字段的两种做法

| 做法 | 优点 | 缺点 | 推荐 |
|------|------|------|------|
| `$base: ["base"]`（按本规范） | 不重复定义，统一演进 | 需要 DDL 生成器支持 | ✅ 新项目 |
| 每个表手动写 create_time/update_time/create_by/update_by/status | 生成器无关 | 重复 5 行 × N 表，改 status 枚举要改 N 处 | ❌ 遗留做法 |

> 本技能 `business/` 示例一律使用 `$base` 写法。手动写审计字段只在改造遗留项目时才会遇到，新表不要这么做。

### 15.7 关联表何时继承 $base

| 场景 | 是否继承 | 理由 |
|------|---------|------|
| 纯多对多关联（只有两个 FK） | ❌ 不继承 | 关联关系本身无需审计 |
| 关联带有业务属性（如关联时间、角色） | ✅ 继承 | 这些属性需要审计 |

```jsonc
// 纯关联表：不继承 $base
{ "title": "user_role_rel", "properties": { "user_id": {...}, "role_id": {...} } }

// 带业务属性的关联表：继承 $base
{ "title": "user_client", "$base": ["base"], "properties": { "user_id": {...}, "client_id": {...}, "position": {...} } }
```

> 示例参考：`examples/schemas/business/product_owner.jsonc`（含 position 业务字段 → 继承审计字段）

---
