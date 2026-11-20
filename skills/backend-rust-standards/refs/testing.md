> 本文档由 `SKILL.md` 外移而来：完整可复制模板与配置文件。规则与约束仍以 `SKILL.md` 为准。

## 9.1 单元测试

```rust
// 与被测代码同文件
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_page_size_out_of_range() {
        assert!(PageSize::new(0).is_err());
        assert!(PageSize::new(101).is_err());
        assert!(PageSize::new(20).is_ok());
    }

    #[tokio::test]
    async fn test_create_user() {
        let pool = setup_test_db().await;
        let service = UserService::new(pool);
        let req = CreateUserRequest {
            name: "Test".into(),
            email: "test@example.com".into(),
            age: 25,
        };
        let user = service.create(req).await.unwrap();
        assert_eq!(user.name, "Test");
    }
}
```

## 9.2 集成测试

```rust
// tests/user_test.rs
mod common;
use common::TestApp;

#[tokio::test]
async fn test_create_and_get_user() {
    let app = TestApp::new().await;

    // 创建
    let resp = app.post("/users")
        .json(&json!({"name": "Alice", "email": "alice@test.com", "age": 30}))
        .send().await;
    assert_eq!(resp.status(), 201);
    let body: Value = resp.json().await;
    let id = body["data"]["id"].as_i64().unwrap();

    // 查询
    let resp = app.get(&format!("/users/{}", id)).send().await;
    assert_eq!(resp.status(), 200);
}
```

## 9.2.1 共享脚手架（tests/common/mod.rs）

```rust
// tests/common/mod.rs
use axum_test_helper::TestClient;  // 或使用 reqwest + axum::serve

pub struct TestApp {
    client: TestClient,
    db: sqlx::SqlitePool,          // 测试用 SQLite 内存库
}

impl TestApp {
    pub async fn new() -> Self {
        let db = sqlx::SqlitePoolOptions::new()
            .max_connections(1)
            .connect("sqlite::memory:").await.unwrap();
        sqlx::migrate!().run(&db).await.unwrap();
        let app = build_router(AppState::new(db.clone()));
        Self { client: TestClient::new(app), db }
    }
}

impl Drop for TestApp {
    fn drop(&mut self) {
        // 清理测试数据
    }
}
```
