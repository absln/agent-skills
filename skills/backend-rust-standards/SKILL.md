---
name: backend-rust-standards
description: Rust 后端开发规范 — 基于 Rust 社区最佳实践（API Guidelines / RFC 430 / Clippy pedantic），覆盖项目结构、代码风格、类型系统、错误处理、异步运行时、Axum 路由、SQLx 数据访问、测试策略、安全防护与质量门槛；当编写或审查 Rust 后端代码、搭 Cargo workspace、实现 Axum 路由与 SQLx 数据访问、做 thiserror/anyhow 错误分层、补测试或安全自查时自动启用。
---

# Rust 后端开发规范

本规范定义 Rust 后端项目的**技术层面编码标准**，基于 Rust 官方 API Guidelines 和社区最佳实践，可复用于任意 Rust 服务端项目。

## 上游依赖（冲突优先级）

| 契约事实 | 唯一事实源 | 本文件角色 |
|---|---|---|
| 响应信封、错误体、状态码、分页 | `http-api-standards` §4–§6 | Axum 落地方式 |
| URL 形状、JSON 字段名、查询参数命名（`id`/`size`/`cwd`） | `http-api-standards` §2 | 消费方 |
| 数据库列名（snake_case）/ 列类型 / 枚举值域 | `database-standards`、`docs/schemas/` | 消费方；列名→JSON 字段名的 camelCase 映射见上游 §2 |
| Rust / Axum / SQLx 编码细节 | **本文件** | 事实源 |

本文件出现的错误体、分页参数是上表的落地示例，**不重新定义形状**；冲突以上游为准。

---

## 1. 技术栈

| 类别 | 推荐技术 | 版本范围 |
|------|----------|----------|
| 语言 | Rust（stable toolchain） | 1.75+（以 MSRV 为准） |
| Web 框架 | Axum | 0.7+ |
| 异步运行时 | Tokio | 1.x |
| 数据库驱动 | SQLx（编译时检查 SQL，支持 PostgreSQL + SQLite） | 0.7+ |
| 序列化 | serde + serde_json | 1.x |
| 请求校验 | validator | 0.18+ |
| 错误处理 | thiserror + anyhow | 1.x |
| 日志/追踪 | tracing + tracing-subscriber | 0.1+ |
| 密码哈希 | argon2 | 0.5+ |
| API Key 认证 | (标准库) | 无第三方依赖 |
| HTTP 客户端 | reqwest | 0.12+ |

---

## 2. 项目结构

### 2.1 Cargo Workspace（多 crate 项目）

**约束**：多 crate 用 workspace 统一版本，成员放 `crates/`；`Cargo.lock` 必须提交；`rust-toolchain.toml` 固定 toolchain，禁止依赖本机默认版本；`main.rs` 只做启动，逻辑放 `lib.rs` 以便集成测试引用。

> 完整模板（26 行）见 `refs/project.md` →「2.1 Cargo Workspace（多 crate 项目）」

### 2.2 模块声明

- 使用 `mod.rs` 或同目录同名文件均可，但项目内必须统一
- `lib.rs` 声明 crate 的公共 API，`main.rs` 仅启动
- 每个模块文件只导出一个核心类型或一组紧密关联的函数

### 2.3 `Cargo.toml` 规范

**约束**：声明 `rust-version`（MSRV）；依赖按字母序排列、第三方在前内部在后；feature 按需裁剪（如 `tokio` 不无脑 `full`，除确实需要）；内部 crate 用 `path` 依赖。

> 完整模板（19 行）见 `refs/project.md` →「2.3 `Cargo.toml` 规范」

- 精确版本用于应用程序（`=x.y.z`），兼容版本用于库（`"0.7"`）
- 功能标记（features）显式列出，避免启用不必要的默认 feature
- Dev 依赖与生产依赖明确分开

---

## 3. 代码风格

### 3.1 命名（RFC 430）

| 构造 | 规范 | 示例 |
|------|------|------|
| 模块 / 文件 | snake_case | `user_service.rs` |
| 类型（struct / enum / trait / type alias） | UpperCamelCase | `UserService`、`ConnectionPool` |
| 函数 / 方法 | snake_case | `create_user()`、`hash_password()` |
| 局部变量 | snake_case | `user_list`、`conn` |
| 常量 / 静态变量 | SCREAMING_SNAKE_CASE | `MAX_PAGE_SIZE` |
| 类型参数 | 单字母 UpperCamelCase | `T`、`E`、`R`（Reader） |
| Crate 名 | snake_case | `my_server` |
| Cargo features | snake_case（kebab-case in TOML） | `serde` |
| 构造器 | `new()` / `with_*()` | `ConnectionPool::new()` |
| 转换 | `as_*` / `to_*` / `into_*` | `as_bytes()` |

### 3.2 Derive 规范（C-COMMON-TRAITS）

公共类型必须 derive 以下适用的标准 trait：

```rust
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct User { ... }

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserDto { ... }
```

- `Debug` — 所有公共类型（C-DEBUG）
- `Clone` — 除非有明确理由不可克隆
- `PartialEq` / `Eq` — 值比较类型
- `Hash` — 需放入 HashMap / HashSet 的类型
- 错误类型 derive `std::error::Error`（通过 thiserror）

### 3.3 格式化

- `rustfmt.toml` 放在仓库根目录，CI 运行 `cargo fmt --check`
- 推荐配置：

```toml
max_width = 100
tab_spaces = 4
edition = "2021"
use_small_heuristics = "Max"
imports_granularity = "Crate"
group_imports = "StdExternalCrate"
reorder_imports = true
```

### 3.4 Clippy

- CI 运行 `cargo clippy --all-targets -- -D warnings`
- 可配置 `clippy.toml` 调整规则阈值
- 禁止在代码中使用 `#[allow(clippy::...)]` 全局压制，例外需注释原因

---

## 4. 类型系统

### 4.1 Newtype 模式

使用 newtype 包装基础类型，增加类型安全：

> 完整模板（21 行）见 `refs/code-patterns.md` →「4.1 Newtype 模式」

### 4.2 枚举优于布尔

状态、类型、分类等概念使用枚举，禁止裸 `bool`：

```rust
// ✅ 推荐
pub enum UserStatus {
    Active,
    Inactive,
    Suspended,
}

// ❌ 禁止
pub struct User {
    pub is_active: bool,
    pub is_suspended: bool,
}
```

### 4.3 请求/响应 DTO

**约束**：请求 / 响应 DTO 与领域模型分开，不把 `Deserialize` 加在实体上；入参用 `validator` 的 `#[validate(...)]` 声明长度、`email`、`range`；更新请求字段全为 `Option`，以区分「未传」与「清空」。

> 完整模板（32 行）见 `refs/code-patterns.md` →「4.3 请求/响应 DTO」

### 4.4 使用 `Option` 和 `Result` 表达可空和可失败

- 禁止用 `-1`、空字符串、null 等哨兵值表示缺失，必须用 `Option<T>`
- 可失败的函数返回 `Result<T, E>`，禁止返回裸 `bool` 或哨兵值表示成功/失败

---

## 5. 错误处理

### 5.1 thiserror 定义错误类型

**约束**：错误类型用 `thiserror` 定义单一 `AppError` 枚举，变体对应 4xx 语义并带 `#[error("...")]` 消息；不裸用 `Box<dyn Error>` 穿过业务层。

> 完整模板（34 行）见 `refs/code-patterns.md` →「5.1 thiserror 定义错误类型」

### 5.2 错误转换

```rust
impl From<sqlx::Error> for AppError {
    fn from(err: sqlx::Error) -> Self {
        match err {
            sqlx::Error::RowNotFound => Self::NotFound("记录不存在".into()),
            _ => {
                tracing::error!(?err, "数据库错误");
                Self::Internal("数据库操作失败".into())
            }
        }
    }
}
```

### 5.3 Axum IntoResponse

错误体形状的唯一事实源是 `http-api-standards` §4：`{"code": int, "message": str}`，`code` 首 3 位对齐 HTTP 状态码，需细分错因时用 5 位扩展码（`40001` 参数非法、`40901` 名称重复）。下面只给 Axum 的落地方式：

> 完整模板（14 行）见 `refs/code-patterns.md` →「5.3 Axum IntoResponse」

### 5.4 错误传播规则

- 库代码（library crate）使用 `thiserror`，应用代码（binary crate）可用 `anyhow` 做顶层胶水
- Service 层禁止 `unwrap()` / `expect()`，使用 `?` 传播
- 错误日志由最外层（handler 或中间件）统一记录，不在 Service 层重复打日志

---

## 6. 异步运行时

### 6.1 Tokio 配置

```toml
# Cargo.toml
[dependencies]
tokio = { version = "1", features = ["rt-multi-thread", "macros", "signal"] }
```

> 完整模板（16 行）见 `refs/project.md` →「6.1 Tokio 配置」

### 6.2 异步最佳实践

- 不要在异步函数中调用同步阻塞操作（如 `std::fs::read`），使用 `tokio::fs` 或 `spawn_blocking`
- CPU 密集型任务使用 `tokio::task::spawn_blocking()` 分流
- 避免 `async fn` 中持有跨越 `.await` 的 `MutexGuard`（用 `tokio::sync::Mutex` 替代）
- 长时间运行的任务应有 `CancellationToken` 支持取消

---

## 7. HTTP 层（Axum）

### 7.1 路由组织

**约束**：路由用 `Router::new()` 链式聚合，按模块拆文件再 `merge` / `nest`；状态用 `with_state` 注入，不用全局静态变量。

> 完整模板（18 行）见 `refs/http-data.md` →「7.1 路由组织」

### 7.2 Handler 签名

**约束**：handler 返回 `Result<Json<T>, AppError>`，不返回裸元组；提取器顺序固定（`State` → `Path` / `Query` → `Json`），`Json` 必须放最后；入参先 `validate()` 再进业务。

> 完整模板（23 行）见 `refs/http-data.md` →「7.2 Handler 签名」

### 7.3 中间件

**约束**：中间件用 `tower` 的 `Service` / `layer`，不手写包装；健康检查路径显式放行；认证失败返回 `AppError::Unauthorized`，由 `IntoResponse` 统一产出错误体。

> 完整模板（24 行）见 `refs/http-data.md` →「7.3 中间件」

### 7.4 AppState 模式

**约束**：共享状态放 `Arc<AppState>` 并 `#[derive(Clone)]`；service 在 `AppState::new` 里建一次，handler 内不新建；双库差异用 feature flag（`sqlite` / `postgres`）切 `DbPool` 别名，业务代码只见别名。

> 完整模板（26 行）见 `refs/http-data.md` →「7.4 AppState 模式」

---

## 8. 数据访问（SQLx）

### 8.1 双库策略

- **开发**：SQLite（零配置、文件级隔离、快速迭代）
- **测试/部署**：PostgreSQL（完整功能、生产环境对齐）

SQLx 的 `query!` / `query_as!` 宏在编译时需要确定数据库类型，因此用 **Cargo feature** 切换：

```toml
[features]
default = ["sqlite"]          # 开发默认 SQLite
sqlite = ["sqlx/sqlite"]
postgres = ["sqlx/postgres"]
```

```rust
// 连接池创建也随 feature 切换
#[cfg(feature = "sqlite")]
let pool = sqlx::SqlitePoolOptions::new()
    .max_connections(5)
    .connect(&database_url).await?;

#[cfg(feature = "postgres")]
let pool = sqlx::PgPoolOptions::new()
    .max_connections(20)
    .connect(&database_url).await?;
```

> `query!` 宏的 SQL 语法随 feature 变化——开发时写 SQLite 兼容 SQL，CI 用 PostgreSQL feature 重新编译验证。

### 8.2 编译时检查 SQL

SQLx 提供编译时 SQL 校验（`query!` / `query_as!` 宏），必须优先使用：

```rust
// ✅ 编译时检查 SQL 语法 + 结果列是否存在
let user = sqlx::query_as!(User, "SELECT id, name, email FROM users WHERE id = $1", id)
    .fetch_optional(&pool)
    .await?;

// ✅ 运行时查询（动态表名等场景才用）
let rows = sqlx::query_as::<_, User>("SELECT id, name FROM users WHERE status = $1")
    .bind("active")
    .fetch_all(&pool)
    .await?;
```

### 8.3 迁移文件

```
migrations/
├── 20240101000000_create_users.sql
├── 20240102000000_add_user_email.sql
└── ...
```

- 迁移文件名格式：`YYYYMMDDHHMMSS_description.sql`
- 每次迁移一个逻辑变更
- 迁移包含 `UP` 操作（SQLx 默认），回滚单独编写
- CI 运行 `sqlx migrate run --check` 验证迁移一致性

### 8.4 事务

```rust
pub async fn transfer(&self, from: UserId, to: UserId, amount: i64) -> Result<(), AppError> {
    let mut tx = self.pool.begin().await?;
    sqlx::query!("UPDATE accounts SET balance = balance - $1 WHERE user_id = $2", amount, from.0)
        .execute(&mut *tx).await?;
    sqlx::query!("UPDATE accounts SET balance = balance + $1 WHERE user_id = $2", amount, to.0)
        .execute(&mut *tx).await?;
    tx.commit().await?;
    Ok(())
}
```

### 8.5 连接池

**约束**：连接池参数必须显式设定 `max_connections` / `min_connections` / `acquire_timeout` / `idle_timeout`，不用默认值上生产；SQLite 开发池 `max_connections` 取小值（≤5）。

> 完整模板（14 行）见 `refs/http-data.md` →「8.5 连接池」

---

## 9. 测试

### 9.1 单元测试

**约束**：单元测试放被测文件内的 `#[cfg(test)] mod tests`，只测纯逻辑、不碰数据库；异步测试用 `#[tokio::test]`。

> 完整模板（25 行）见 `refs/testing.md` →「9.1 单元测试」

### 9.2 集成测试

**约束**：集成测试放 `tests/`，共享脚手架收敛到 `tests/common/mod.rs`（`TestApp`）；测试库每次独立建表，不依赖开发库状态。

> 完整模板（20 行）见 `refs/testing.md` →「9.2 集成测试」；共享脚手架 `TestApp`（24 行，含 `sqlx::migrate!` 与内存库）见「9.2.1 共享脚手架」

### 9.3 测试原则

- 每个 handler 至少覆盖：正常路径、参数校验失败、不存在、权限拒绝
- 集成测试使用独立测试数据库（每次测试运行迁移或回滚）
- Mock 外部 HTTP 服务（使用 `wiremock` 或 `mockito`）
- 测试命名：`test_<场景>_<预期>`（如 `test_create_user_with_invalid_email_fails`）

---

## 10. 安全

### 10.1 SQL 注入防护

- **100% 参数化查询**，使用 `$1`、`$2` 占位符
- 动态排序/字段名必须白名单校验后安全拼接：

```rust
const ALLOWED_SORT_FIELDS: &[&str] = &["id", "name", "created_at"];

fn validate_sort_field(field: &str) -> Result<&'static str, AppError> {
    ALLOWED_SORT_FIELDS.iter()
        .find(|&&f| f == field)
        .copied()
        .ok_or_else(|| AppError::bad_request("不支持的排序字段"))
}
```

### 10.2 输入校验

- 所有外部输入（请求体、Query 参数、Path 参数、Header）使用 `validator` derive 宏校验
- 自定义校验逻辑放在 `Validate` 的 `#[validate(custom = "...")]` 或 Service 层
- 路径穿越防护：拒绝包含 `..`、`\`、`/` 的文件名参数

### 10.3 密码处理

- 使用 `argon2` 哈希（Argon2id 变体），禁止 SHA256 / MD5 等通用哈希
- 密码长度要求最少 8 字符
- 禁止在日志 / 错误消息中输出密码原文
- JWT / Session Token 使用短有效期（默认 15 分钟），配合 refresh token

### 10.4 敏感信息

- 密钥、数据库 URL、API Key 从环境变量读取，禁止硬编码
- `.env` 加入 `.gitignore`
- 提供 `.env.example` 模板文件
- 生产环境使用 Secret Manager（如 HashiCorp Vault）

---

## 11. 质量门槛

| 检查项 | 命令 | 标准 |
|--------|------|------|
| 编译 | `cargo build --all-targets` | 零错误 |
| 格式化 | `cargo fmt --check` | 零差异 |
| Clippy | `cargo clippy --all-targets -- -D warnings` | 零警告 |
| 测试 | `cargo test` | 100% 通过 |
| 迁移一致性 | `sqlx migrate run --check` | 无待执行迁移 |
| 依赖审计 | `cargo audit` | 零已知漏洞 |
| 未使用依赖 | `cargo udeps` | 零未使用 |

Code Review 检查项：

| 检查项 | 要点 |
|--------|------|
| 无 `unwrap()` / `expect()` | 测试代码除外 |
| SQL 参数化 | 100% 使用 `$1` 绑定 |
| 动态 SQL 白名单 | 排序字段、表名等必须白名单 |
| 错误不吞 | 所有 `Result` 显式处理 |
| 异步不阻塞 | 无 `std::thread::sleep` 或同步 IO |


## 完整模板索引

> 以下文件是可直接复制的完整模板 / 配置文件，仅在需要照抄时查阅；约束条文都在上文。

- `refs/project.md` — 2.1 Cargo Workspace（多 crate 项目）、2.3 `Cargo.toml` 规范、6.1 Tokio 配置
- `refs/code-patterns.md` — 4.1 Newtype 模式、4.3 请求/响应 DTO、5.1 thiserror 定义错误类型、5.3 Axum IntoResponse
- `refs/http-data.md` — 7.1 路由组织、7.2 Handler 签名、7.3 中间件、7.4 AppState 模式、8.5 连接池
- `refs/testing.md` — 9.1 单元测试、9.2 集成测试、9.2.1 共享脚手架