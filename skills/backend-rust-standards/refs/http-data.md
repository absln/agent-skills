> 本文档由 `SKILL.md` 外移而来：完整可复制模板与配置文件。规则与约束仍以 `SKILL.md` 为准。

## 7.1 路由组织

```rust
// router.rs — 路由聚合
use axum::{Router, middleware};
use crate::middleware::auth;

pub fn build_router(state: AppState) -> Router {
    let public = Router::new()
        .route("/health", get(health_check));

    let protected = Router::new()
        .route("/users", get(list_users).post(create_user))
        .route("/users/{id}", get(get_user).put(update_user).delete(delete_user))
        .layer(middleware::from_fn_with_state(state.clone(), auth::require_auth));

    Router::new()
        .merge(public)
        .merge(protected)
        .with_state(state)
}
```

## 7.2 Handler 签名

```rust
use axum::{
    extract::{Path, Query, State},
    Json,
};

/// 列表查询
async fn list_users(
    State(state): State<AppState>,
    Query(params): Query<PaginationQuery>,
) -> Result<Json<PaginatedResponse<UserDto>>, AppError> {
    let (users, total) = state.user_service.list(params).await?;
    Ok(Json(PaginatedResponse::new(users, total)))
}

/// 创建
async fn create_user(
    State(state): State<AppState>,
    Json(req): Json<CreateUserRequest>,
) -> Result<(StatusCode, Json<UserDto>), AppError> {
    req.validate().map_err(|e| AppError::bad_request(e.to_string()))?;
    let user = state.user_service.create(req).await?;
    Ok((StatusCode::CREATED, Json(user)))
}
```

## 7.3 中间件

```rust
// middleware/auth.rs
use axum::{
    extract::{Request, State},
    middleware::Next,
    response::Response,
};

pub async fn require_auth(
    State(state): State<AppState>,
    mut request: Request,
    next: Next,
) -> Result<Response, AppError> {
    let header = request.headers()
        .get("Authorization")
        .and_then(|v| v.to_str().ok())
        .ok_or(AppError::Unauthorized)?;

    let token = header.strip_prefix("Bearer ")
        .ok_or(AppError::Unauthorized)?;

    let user = state.auth_service.verify_token(token).await?;
    request.extensions_mut().insert(user);
    Ok(next.run(request).await)
}
```

## 7.4 AppState 模式

```rust
use sqlx::{Pool, Database};

// 双库策略：开发 SQLite，生产 PostgreSQL
// SQLx 的 query! 宏需要编译时确定数据库类型，故用 feature flag 切换：

#[cfg(feature = "sqlite")]
pub type DbPool = sqlx::SqlitePool;
#[cfg(feature = "postgres")]
pub type DbPool = sqlx::PgPool;

#[derive(Clone)]
pub struct AppState {
    pub db: DbPool,
    pub user_service: Arc<UserService>,
    pub auth_service: Arc<AuthService>,
}

impl AppState {
    pub fn new(db: DbPool) -> Self {
        Self {
            user_service: Arc::new(UserService::new(db.clone())),
            auth_service: Arc::new(AuthService::new(db.clone())),
            db,
        }
    }
}
```

## 8.5 连接池

```rust
// PostgreSQL（生产/测试）
let pool = sqlx::PgPoolOptions::new()
    .max_connections(20)
    .min_connections(5)
    .acquire_timeout(Duration::from_secs(5))
    .idle_timeout(Duration::from_secs(300))
    .connect(&database_url)
    .await?;

// SQLite（开发，单线程即可）
let pool = sqlx::SqlitePoolOptions::new()
    .max_connections(5)
    .connect(&database_url)
    .await?;
```
