> 本文档由 `SKILL.md` 外移而来：完整可复制模板与配置文件。规则与约束仍以 `SKILL.md` 为准。

## 2.1 Cargo Workspace（多 crate 项目）

```
project/
├── Cargo.toml              # workspace 根，[workspace] 声明成员
├── Cargo.lock              # 提交到 VCS
├── rust-toolchain.toml     # 固定 toolchain 版本
├── rustfmt.toml            # 格式化配置
├── clippy.toml             # Clippy 规则配置
├── .cargo/
│   └── config.toml         # 构建配置（linker、registries）
├── crates/
│   ├── server/             # HTTP 服务 crate
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── main.rs
│   │       ├── lib.rs      # 可被集成测试引用
│   │       ├── config.rs
│   │       ├── router.rs   # 路由聚合
│   │       ├── models/
│   │       ├── handlers/   # 请求处理函数
│   │       ├── services/
│   │       ├── middleware/
│   │       ├── errors/
│   │       └── response/
│   ├── core/               # 共享领域模型 crate
│   └── db/                 # 数据库访问 crate
├── migrations/             # SQL 迁移文件
└── tests/                  # 工作区级集成测试
```

## 2.3 `Cargo.toml` 规范

```toml
[package]
name = "my-server"
version = "0.1.0"
edition = "2021"
rust-version = "1.75.0"        # MSRV 声明

[dependencies]
# 按字母序排列，第三方在前、内部在后
axum = "0.7"
serde = { version = "1", features = ["derive"] }
sqlx = { version = "0.7", features = ["runtime-tokio", "sqlite", "postgres"] }
tokio = { version = "1", features = ["full"] }
tracing = "0.1"

my-core = { path = "../core" }
my-db = { path = "../db" }

[dev-dependencies]
tower = { version = "0.4", features = ["util"] }  # 测试用 ServiceExt
```

## 6.1 Tokio 配置

```rust
// main.rs
#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // 初始化 tracing
    tracing_subscriber::fmt()
        .with_env_filter(std::env::var("RUST_LOG").unwrap_or_else(|_| "info".into()))
        .init();

    // 启动
    let app = build_app().await?;
    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await?;
    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await?;
    Ok(())
}
```
