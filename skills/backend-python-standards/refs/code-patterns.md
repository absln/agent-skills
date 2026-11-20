> 本文档由 `SKILL.md` 外移而来：完整可复制模板与配置文件。规则与约束仍以 `SKILL.md` 为准。

## 3.3 Docstring（PEP 257）

```python
def create_user(name: str, email: str, age: int | None = None) -> User:
    """创建新用户。

    Args:
        name: 用户名，不可为空。
        email: 邮箱地址，需要格式校验。
        age: 年龄，可选。

    Returns:
        新创建的用户对象。

    Raises:
        DuplicateError: 邮箱已存在。
        ValidationError: 输入校验失败。
    """
```

## 4.2 Pydantic v2 模型

```python
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, field_validator


class User(BaseModel):
    """用户实体"""
    model_config = dict(from_attributes=True)  # 支持从 ORM / dict 构建

    id: int
    name: str
    email: str
    age: int | None = None
    is_active: bool = True
    created_at: datetime


class CreateUserRequest(BaseModel):
    """创建用户请求"""
    name: str = Field(min_length=1, max_length=50)
    email: EmailStr
    age: int = Field(gt=0, lt=150)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("名称不能为空")
        return v.strip()


class UpdateUserRequest(BaseModel):
    """更新用户请求 — 所有字段可选，仅更新传入的字段"""
    name: str | None = Field(None, min_length=1, max_length=50)
    email: EmailStr | None = None
    age: int | None = Field(None, gt=0, lt=150)


class PaginationQuery(BaseModel):
    """分页查询参数"""
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
```

## 5.1 异常层次

```python
class AppException(Exception):
    """应用基础异常"""

class BadRequestError(AppException):
    """400 — 请求参数错误"""

class UnauthorizedError(AppException):
    """401 — 未认证"""

class ForbiddenError(AppException):
    """403 — 无权限"""

class NotFoundError(AppException):
    """404 — 资源不存在"""

class ConflictError(AppException):
    """409 — 资源冲突"""
```

## 5.4 上下文管理器

```python
from contextlib import contextmanager

@contextmanager
def db_connection(path: str):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```
