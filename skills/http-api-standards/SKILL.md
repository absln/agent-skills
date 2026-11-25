---
name: http-api-standards
description: HTTP 接口开发规范 — 对齐 OpenAPI 3.1 与 RFC 9110，覆盖 URL/字段/参数命名、HTTP 方法语义、错误处理与状态码、响应信封、分页、OpenAPI 元数据；当新增或整改 HTTP 接口、设计 REST API、审查接口契约一致性时自动启用。
---

# http-api-standards

> HTTP 接口开发规范。标准可查的部分对齐 RFC 9110 / OpenAPI 3.1；错误体、信封、分页等形状为本项目约定，跨端以本文件为唯一事实源。

---

## 1. 核心原则

1. **契约优先**：以行业标准为准绳，实现不得偏离项目需求；改动先改文档再改代码。
2. **一个语义一个名字**：简短但不歧义。
3. **错误可被 HTTP 层识别**：禁止 `200` 携带失败信息；响应信封不含 `success` 字段，成败由状态码表达，错误体唯一形状 `{code:int, message}`（§4）。
4. **宁缺毋假**：未实现的字段/端点要么删除、要么 `501`，不放占位假数据（`null`/`[]`/空串恒值）。
5. **JSON 一律 camelCase**：用各栈的显式别名机制声明，不依赖序列化器默认猜测——C# `[JsonPropertyName]`、Python Pydantic `alias_generator=to_camel`、Rust `#[serde(rename_all = "camelCase")]`。

---

## 2. 命名规范

| 对象 | 规则 | 示例 |
|------|------|------|
| 集合路径 | 复数名词 | `/api/sessions` |
| 单资源 | 集合 + `/{id}` | `/api/sessions/{id}` |
| 子资源 | `/{id}/{sub}` | `/api/sessions/{id}/state` |
| 动作型接口 | 动词只放命令体，不放 URL | `POST /api/agent/{id}` body `{type:"remove"}` |
| 字段名 | camelCase | `messageCount`, `leafId` |
| 查询参数 | 小写驼峰；统一语义统一命名 | 起点=`id`、页大小=`size`、项目目录=`cwd` |

> 参数中英文说明统一经 OpenAPI 参数 `description` 补齐，不散落在端点实现里。

> **两层字段名的分界**（跨端最容易错的一处）：本节的 camelCase 只约束 **HTTP 上的 JSON 字段名**；数据库列名由 `database-standards` §8 定为 snake_case。两者映射固定为「列名 snake_case → JSON 字段名 camelCase」（`create_time` → `createTime`、`user_id` → `userId`），列名不得原样出现在响应体里，JSON 字段名也不得反推去改列名。

---

## 3. HTTP 方法语义

| 方法 | 语义 | 本项目实例 |
|------|------|-----------|
| GET | 只读、幂等、无副作用 | `/api/{model}/view`、`/api/models` |
| POST | 创建资源 / 提交命令 | `/api/{model}/{id}`、`/api/models/search` |
| PUT | 全量替换 | `/api/{model}/update` |
| PATCH | 部分更新 | `/api/{model}/status`（启停）、`/api/{model}/name`（改名） |
| DELETE | 删除 | `/api/{model}/{id}` |

---

## 4. 错误处理

错误响应体（全项目唯一形状，前后端按此对齐）：

```json
{ "code": 40001, "message": "磁盘名称不能为空" }
```

- `code` 是**整数**，首 3 位与 HTTP 状态码一致：无需细分时直接等于状态码（`400`/`404`/`500`）；需要程序区分错因时用 5 位扩展码（`40001` 参数非法、`40901` 名称重复）。
- `message` 面向终端用户，中文、可直接展示；禁止含堆栈、SQL、内部路径、异常类名。
- 错误体**只含** `code` + `message` 两个必需字段；成功响应里不出现这两个键。
- 形状参考 AIP-193 的 `code`/`message`，字段名为本项目约定（`code` 为整数而非字符串枚举）。

状态码语义（RFC 9110）：

| 状态码 | 语义 |
|---|---|
| 400 | 参数缺失/非法 |
| 401 | 未认证 |
| 403 | 已认证但无权限 / 越界 |
| 404 | 资源不存在 |
| 409 | 冲突（如上传覆盖） |
| 422 | 语义错误（可选，缺省归 400） |
| 429 | 限流 |
| 500 | 服务内部错误 |
| **501** | **未实现**（替代「200 空成功」的 stub） |

**禁止**：
- `200` + `{success:false}` 或 `200` + `{code,message}` 承载错误（HTTP 层无法识别，缓存/重试/监控全错）。
- 顶层 `{ "error": "..." }` 旧格式（与 `code`/`message` 并存会让前端分叉判断）。
- 未实现端点返回 `200` + 空数据（stub 一律 `501` 或下线）。

---

## 5. 响应信封

每端点返回**一个顶层资源键**，绝不混平铺、包裹与裸数组：

```json
{ "sessions": [...], "nextCursor": "opaque|null", "hasMore": true }   // 列表
{ "session": {...} }                                                 // 单资源
{ "envs": {...} }                                                    // 字典/附属数据
```

- 键名与路径段同名：列表用复数键，单资源用单数键。
- 命令型接口（`POST /api/{model}/{id}`）**同样只返回受影响的资源键**，不再套第二层 `{success, data}`：

```json
{ "agent": {...} }    // 有返回对象 → 资源键
{ "removed": true }   // 无返回对象 → 具体语义键，不用 success
```

- 值类型必须与键语义一致：对象键恒为对象或 `null`，列表键恒为数组。禁止同一键时而字符串时而对象。

---

## 6. 分页（cursor）

列表/条目接口统一 cursor 分页：

```json
{ "sessions": [...], "nextCursor": "opaque-string|null", "hasMore": true }
```

- 列表键与路径段同名（§5），不用泛化的 `items`/`data`/`list`。
- cursor 不透明，客户端不得解析或推算；`hasMore` 由服务端给，前端不靠 `nextCursor != null` 猜。
- 现状 `/sessions/context|entries` 的 `oldestId`+`atRoot` 是 cursor 实例；新接口直接套 `nextCursor`/`hasMore`，旧字段逐步收敛。

---

## 7. OpenAPI 元数据（每端点必填）

| 项 | 要求 |
|----|------|
| `operationId` | 稳定标识（供前端代码生成/引用） |
| `tags` | 业务域分组：会话/对话/模型配置/技能/认证/工作目录/系统 |
| `summary` + `description` | 中文；含请求体与响应说明 |
|  `description` |  逐个补齐（不靠实现层注释代偿） |
| `schema` | 请求体/响应需有 `description`，关键字段补 `example` |
| 废弃接口 | `deprecated: true`（不再用删除线文本） |

---

## 8. 质量门槛（新增/整改接口自检）

- [ ] 字段全 camelCase，用各栈显式别名机制声明（C# `[JsonPropertyName]` / Pydantic `alias_generator` / serde `rename_all`）
- [ ] 无别名参数；参数语义与命名符合 §2
- [ ] 错误用 `{code:int, message}` + 语义状态码（§4），无 `200` 假失败、无 `error` 字符串旧格式
- [ ] 未实现字段/端点已删除或 `501`（无占位假数据）
- [ ] 响应信封符合 §5；顶层是单个资源键（列表键与路径段同名），无 `{success, data}` 二次包裹，键值类型一致
- [ ] 列表/条目有分页（§6）
- [ ] `summary`/`description`/参数说明齐全，`operationId` 稳定
- [ ] 契约已同步到项目的接口规范文档（路径以项目 `README.md` 为准）

---

## 9. 禁止事项

| 禁止 | 说明 |
|------|------|
| 别名参数 | `force`/`leaf`/`leafId`/`objectId`/`length` 等，一个语义只一个名字 |
| 200 携带失败 | `200 {success:false}` 或 `200 {code,message}` |
| 空成功 stub | 未实现却返回 `200` + 空数据，应 `501` |
| PascalCase 字段 | 遗漏显式别名声明，让序列化器按原名输出 |
| 信封二重包裹 | 资源键外再套 `{success, data}`；键值时而字符串时而对象 |
| 错误体分叉 | 同时出现 `error` 与 `code`/`message`，或 `code` 时而整数时而字符串 |
| 占位假数据 | `null`/`[]`/空串恒值字段（要么真实现、要么删字段） |
| 缺 operationId/描述 | 裸接口无元数据，无法被文档/代码生成消费 |

---

## 参考标准

- Microsoft REST API Guidelines — 复数集合命名、`operationId` 约定
- RFC 9110 — HTTP 语义（方法、状态码）
- Google AIP — AIP-121（资源命名）、AIP-158（分页）、AIP-193（错误码形状）
- OpenAPI 3.1 + JSON Schema（描述/校验）
