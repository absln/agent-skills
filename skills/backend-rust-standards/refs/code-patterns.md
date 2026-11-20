> 本文档由 `SKILL.md` 外移而来：完整可复制模板与配置文件。规则与约束仍以 `SKILL.md` 为准。

## 4.1 Newtype 模式

```rust
/// 用户 ID — 杜绝与其它 i64 混淆
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(transparent)]
pub struct UserId(pub i64);

/// 分页大小 — 保证合法性
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct PageSize(u32);

impl PageSize {
    pub const MIN: u32 = 1;
    pub const MAX: u32 = 100;
    pub const DEFAULT: u32 = 20;

    pub fn new(n: u32) -> Result<Self, AppError> {
        if !(Self::MIN..=Self::MAX).contains(&n) {
            return Err(AppError::bad_request("分页大小超出范围"));
        }
        Ok(Self(n))
    }
}
```

## 4.3 请求/响应 DTO

```rust
use serde::{Deserialize, Serialize};
use validator::Validate;

/// 创建用户请求
#[derive(Debug, Deserialize, Validate)]
pub struct CreateUserRequest {
    #[validate(length(min = 1, max = 50))]
    pub name: String,

    #[validate(email)]
    pub email: String,

    #[validate(range(min = 1))]
    pub age: u8,
}

/// 更新请求 — 全部 Optional，允许部分更新
#[derive(Debug, Deserialize, Validate)]
pub struct UpdateUserRequest {
    #[validate(length(min = 1, max = 50))]
    pub name: Option<String>,

    #[validate(email)]
    pub email: Option<String>,
}

/// 分页查询参数
#[derive(Debug, Deserialize)]
pub struct PaginationQuery {
    pub page: Option<u32>,
    pub page_size: Option<u32>,
}
```

## 5.1 thiserror 定义错误类型

```rust
use thiserror::Error;

#[derive(Debug, Error)]
pub enum AppError {
    #[error("请求参数错误: {0}")]
    BadRequest(String),

    #[error("未认证")]
    Unauthorized,

    #[error("无权限: {0}")]
    Forbidden(String),

    #[error("资源不存在: {0}")]
    NotFound(String),

    #[error("资源冲突: {0}")]
    Conflict(String),

    #[error("内部错误: {0}")]
    Internal(String),
}

impl AppError {
    pub fn bad_request(msg: impl Into<String>) -> Self {
        Self::BadRequest(msg.into())
    }
    pub fn not_found(msg: impl Into<String>) -> Self {
        Self::NotFound(msg.into())
    }
    pub fn internal(msg: impl Into<String>) -> Self {
        Self::Internal(msg.into())
    }
}
```

## 5.3 Axum IntoResponse

```rust
impl axum::response::IntoResponse for AppError {
    fn into_response(self) -> axum::response::Response {
        let (status, message) = match &self {
            Self::BadRequest(msg) => (StatusCode::BAD_REQUEST, msg.clone()),
            Self::Unauthorized => (StatusCode::UNAUTHORIZED, "未认证".into()),
            Self::Forbidden(msg) => (StatusCode::FORBIDDEN, msg.clone()),
            Self::NotFound(msg) => (StatusCode::NOT_FOUND, msg.clone()),
            Self::Conflict(msg) => (StatusCode::CONFLICT, msg.clone()),
            Self::Internal(msg) => (StatusCode::INTERNAL_SERVER_ERROR, msg.clone()),
        };
        let body = Json(json!({ "code": status.as_u16(), "message": message }));
        (status, body).into_response()
    }
}
```
