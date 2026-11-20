# JSONC Schema 示例

> `database-standards` 技能的配套资产。启动新项目时把 `templates/` 复制到项目 `docs/schemas/` 作为起点。

---

## 目录结构

```
examples/schemas/
├── README.md                  ← 本文件
├── templates/                 ← 通用模板（新项目由此复制）
│   ├── base.jsonc             # 审计字段模板（$base 继承源，不要改字段）
│   └── schema.jsonc           # 元表定义模板（项目需管理元数据时用）
└── business/                  ← 模式示例（一个文件讲清一种表模式）
    ├── category.jsonc         # 树形表
    ├── product.jsonc          # 标准业务表
    ├── user.jsonc             # 标准业务表（字段命名示范）
    ├── product_owner.jsonc    # 关联表
    └── dict.jsonc             # 字典表
```

## 五种表模式对照

| 示例 | 模式 | 关键点 | 规范出处 |
|---|---|---|---|
| `category.jsonc` | 树形表 | `parent_id` 自引用 + `path` + `level` 三件套 | §15.1 |
| `product.jsonc` | 标准业务表 | `$base` + 主键 `id` + 外键 `category_id` | §12 |
| `user.jsonc` | 标准业务表 | 完整语义字段名，不用 `uid`/`cid` 缩写 | §8 |
| `product_owner.jsonc` | 关联表 | 双边 `ref`，带业务属性故继承 `$base` | §15.7 |
| `dict.jsonc` | 字典表 | `parent` 字符串分组，非外键 | §15.3 |

## 使用说明

1. **新项目启动**：复制 `templates/base.jsonc`（以及需要时的 `schema.jsonc`）到项目 `docs/schemas/`。
2. **新表建模**：按表模式挑最接近的示例照抄骨架，再替换字段。
3. **五个示例全部合规**：`$base: ["base"]` 已声明、主键统一 `id`、外键 `{entity}_id` 且类型与目标主键一致（目标 `bigserial` → 外键 `bigint`）。
4. **`ref` 互相指向真实存在的表**：`product.category_id → category`、`product_owner → product/user`，可整目录当自洽示例集验证。

## 已知边界

- **示例不含 `sys_` 前缀的表**（如省市区、多语言、通知）。它们要么与已有示例同构（多语言 ≈ 字典），要么单表写法本身就是错的（通知须拆消息表 + 已读表），在 `SKILL.md` 正文说明比存文件更清楚。
