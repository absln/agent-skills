---
name: backend-python-standards
description: Python 后端开发规范 — 基于 Python 社区最佳实践（PEP 8 / PEP 257 / PEP 484 / PEP 604），覆盖项目结构、代码风格、类型系统、异常处理、异步编程、FastAPI 路由、数据访问、测试策略、安全防护与质量门槛；当编写或审查 Python 后端代码、搭 FastAPI 项目结构、实现路由与数据访问层、处理异常与异步、补测试或做安全自查时自动启用。
---

# Python 后端开发规范

本规范定义 Python 后端项目的**技术层面编码标准**，基于 PEP 系列标准和 Python 社区最佳实践，可复用于任意 Python 服务端项目。

## 上游依赖（冲突优先级）

| 契约事实 | 唯一事实源 | 本文件角色 |
|---|---|---|
| 响应信封、错误体、状态码、分页 | `http-api-standards` §4–§6 | FastAPI 落地方式 |
| URL 形状、JSON 字段名、查询参数命名（`id`/`size`/`cwd`） | `http-api-standards` §2 | 消费方 |
| 数据库列名（snake_case）/ 列类型 / 枚举值域 | `database-standards`、`docs/schemas/` | 消费方；列名→JSON 字段名的 camelCase 映射见上游 §2 |
| Python / FastAPI 编码细节 | **本文件** | 事实源 |

本文件出现的错误体、分页参数是上表的落地示例，**不重新定义形状**；冲突以上游为准。

---

## 1. 技术栈

| 类别 | 推荐技术 | 版本 |
|------|----------|------|
| 语言 | Python | 3.11+ |
| Web 框架 | FastAPI（支持 async/await） | 0.110+ |
| ASGI 服务器 | Uvicorn | 0.30+ |
| 数据校验 | Pydantic v2 | 2.0+ |
| 配置管理 | Pydantic Settings + python-dotenv | 2.0+ |
| HTTP 客户端 | httpx（异步）/ requests（同步） | 0.27+ |
| 测试 | pytest + httpx | 7.0+ |
| 格式化 | black | 24.x |
| Lint | ruff（替代 flake8 + isort） | 0.5+ |
| 类型检查 | mypy（strict 模式） | 1.10+ |
| 日志 | structlog（结构化日志）或标准库 logging | — |

---

## 2. 项目结构

### 2.1 推荐布局

**约束**：用 src 布局（应用代码只在 `src/` 下，避免根目录同名模块被意外导入）；按 `models` / `services` / `handlers` / `middleware` / `errors` 分层，`handlers` 只做参数校验与响应组装，业务逻辑一律落在 `services`。

> 完整模板（35 行）见 `refs/project.md` →「2.1 推荐布局」

### 2.2 pyproject.toml 规范

**约束**：依赖写 `>=x,<y` 双端约束，不用 `*`、不裸版本号；black / ruff / mypy / pytest 的配置全部集中在本文件，不再建 `.flake8`、`setup.cfg`；`mypy strict = true` 不得放宽。

> 完整模板（40 行）见 `refs/project.md` →「2.2 pyproject.toml 规范」

### 2.3 虚拟环境

- 项目使用 `.venv/` 目录存放虚拟环境，加入 `.gitignore`
- Python 版本通过 `.python-version` 固定（配合 pyenv 或 mise）
- `requirements.txt` 使用 `pip freeze` 或 `pip-compile` 生成，pin 精确版本

---

## 3. 代码风格

### 3.1 命名（PEP 8）

| 构造 | 规范 | 示例 |
|------|------|------|
| 模块 / 文件 | snake_case | `user_service.py`、`auth.py` |
| 类 | PascalCase | `UserService`、`AppException` |
| 函数 / 方法 | snake_case | `create_user()`、`hash_password()` |
| 变量 | snake_case | `user_list`、`connection_pool` |
| 常量 | UPPER_SNAKE_CASE | `MAX_PAGE_SIZE`、`DEFAULT_TIMEOUT` |
| 私有成员 | `_` 前缀 | `_validate_input()`、`_cache` |
| 类型变量 | PascalCase | `T`、`TResponse` |
| 包名 | 简短小写，无下划线 | `mypackage` |

### 3.2 格式化

- 使用 **black** 自动格式化，零配置分歧
- 使用 **ruff** 替代 flake8 / isort / pyupgrade
- import 顺序：标准库 → 第三方 → 本地模块（每组间空一行，组内按字母序）

```python
# ✅ 正确
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.config import settings
from src.errors.exceptions import NotFoundError
```

### 3.3 Docstring（PEP 257）

使用 Google 或 NumPy 风格的 docstring：

> 完整模板（15 行）见 `refs/code-patterns.md` →「3.3 Docstring（PEP 257）」

---

## 4. 类型系统

### 4.1 类型注解（PEP 484 / PEP 604）

- 所有公共函数必须有完整的参数和返回值类型注解
- 使用 Python 3.10+ 的 `| None` 语法，禁止 `Optional[X]`：

```python
# ✅ 推荐
def find_user(user_id: int) -> User | None:
    ...

# ❌ 禁止
from typing import Optional
def find_user(user_id: int) -> Optional[User]:
    ...
```

- 集合类型使用内置泛型（Python 3.9+）：

```python
def list_users(page: int) -> list[User]: ...
def stats() -> dict[str, int]: ...
def batch_create(users: list[CreateUserRequest]) -> tuple[int, list[User]]: ...
```

### 4.2 Pydantic v2 模型

**约束**：请求模型与响应模型分开定义，不复用同一个类；用 `model_config = dict(...)`（v2 写法），不写 `class Config`；外部输入字段必须带 `Field` 约束（长度 / 范围），跨字段规则用 `@field_validator`；更新请求全部可选（`| None`），以区分「未传」与「置空」。

> 完整模板（41 行）见 `refs/code-patterns.md` →「4.2 Pydantic v2 模型」

### 4.3 枚举优于字符串

```python
from enum import StrEnum

class UserStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

# 在 Pydantic 中使用
class User(BaseModel):
    status: UserStatus = UserStatus.ACTIVE
```

### 4.4 NewType 用于语义区分

```python
from typing import NewType

UserId = NewType("UserId", int)
AccountId = NewType("AccountId", int)

# 类型检查时不可互换
def transfer(from_id: UserId, to_id: UserId, amount: int) -> None:
    ...
```

---

## 5. 异常处理

### 5.1 异常层次

**约束**：业务异常必须继承 `AppException` 基类，只表达 4xx 语义（400 / 401 / 403 / 404 / 409）；业务代码禁止 `raise Exception`，也不要直接抛 `HTTPException`（会绕过统一错误信封）。

> 完整模板（17 行）见 `refs/code-patterns.md` →「5.1 异常层次」

### 5.2 FastAPI 异常处理

错误体形状的唯一事实源是 `http-api-standards` §4：`{"code": int, "message": str}`，`code` 首 3 位对齐 HTTP 状态码，需细分错因时用 5 位扩展码（`40001` 参数非法、`40901` 名称重复）。下面只给 FastAPI 的落地方式：

> 完整模板（26 行）见 `refs/http-data.md` →「5.2 FastAPI 异常处理」

### 5.3 异常处理规则

- Service 层抛出 `AppException` 子类，不捕获它
- 外部依赖异常（数据库、网络）在 Service 层捕获并转换：

```python
def create_user(self, req: CreateUserRequest) -> User:
    try:
        row = self.db.execute("INSERT INTO users ...", ...)
    except Exception as e:  # sqlite3.IntegrityError / asyncpg.UniqueViolationError 等
        raise ConflictError("用户名或邮箱已存在") from e
    except sqlite3.Error as e:
        logger.exception("数据库错误")
        raise AppException("数据库操作失败") from e
```

- handler 层不做 try/except，依赖全局 exception_handler
- 禁止 `except Exception: pass`（裸吞异常），必须记录日志或重新抛出

### 5.4 上下文管理器

资源管理使用 context manager 而非手动 try/finally：

> 完整模板（14 行）见 `refs/code-patterns.md` →「5.4 上下文管理器」

---

## 6. 异步编程

### 6.1 FastAPI async handler

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/users/{user_id}")
async def get_user(user_id: int) -> UserResponse:
    # FastAPI 在线程池中运行，async 是推荐的默认风格
    user = await user_service.find(user_id)
    if user is None:
        raise NotFoundError("用户不存在")
    return user
```

### 6.2 异步最佳实践

- FastAPI handler 默认使用 `async def`
- 数据库操作如果使用同步驱动（如 sqlite3），用 `asyncio.to_thread` 避免阻塞事件循环：

```python
import asyncio

@router.get("/users")
async def list_users(query: PaginationQuery = Depends()) -> list[UserResponse]:
    return await asyncio.to_thread(user_service.list, query)
```

- 并发外部请求使用 `httpx.AsyncClient` + `asyncio.gather`：

```python
async with httpx.AsyncClient() as client:
    tasks = [client.get(url) for url in urls]
    responses = await asyncio.gather(*tasks)
```

- 禁止在 async 函数中调用 `time.sleep()`，使用 `await asyncio.sleep()`
- 禁止在 async 函数中调用同步 `requests.get()`，使用 `httpx.AsyncClient`

---

## 7. HTTP 层（FastAPI）

### 7.1 路由组织

**约束**：用 `create_app()` 工厂函数组装，不写模块级全局 `app`（否则测试无法注入）；异常处理器必须在注册路由**之前**注册，否则先注册的路由出错时不走统一信封。

> 完整模板（16 行）见 `refs/http-data.md` →「7.1 路由组织」

### 7.2 Handler 签名

**约束**：handler 一律 `async def` 并显式声明 `response_model`，不返回裸 dict；路径 / 查询参数用 `Path(gt=0)`、`Query` 声明校验；handler 内只做「取依赖 → 调 service → 返回」，不写 SQL、不做业务判断。

> 完整模板（32 行）见 `refs/http-data.md` →「7.2 Handler 签名」

### 7.3 依赖注入

**约束**：配置与 service 全部经 `Depends` 注入，不在 handler 里 `new`；`get_settings` 用 `lru_cache` 保证单例，避免每请求重建。

> 完整模板（14 行）见 `refs/http-data.md` →「7.3 依赖注入」

### 7.4 中间件

**约束**：健康检查路径在鉴权中间件里显式放行；认证失败统一抛 401，由统一异常处理器产出错误体，中间件不自行拼 JSON。

> 完整模板（16 行）见 `refs/http-data.md` →「7.4 中间件」

---

## 8. 数据访问

### 8.0 双库策略

- **开发**：SQLite（零配置、文件级隔离，`sqlite3` 标准库即可）
- **测试/部署**：PostgreSQL（完整功能、生产环境对齐）

数据访问层通过抽象基类切换后端，业务代码不感知底层驱动。以下 §8.1 为 SQLite 开发模式，PostgreSQL 实现同理（替换连接驱动即可）。

### 8.1 SQLite（开发模式）

**约束**：SQLite 连接必须开 `PRAGMA journal_mode=WAL` 与 `PRAGMA foreign_keys=ON`——SQLite 默认不校验外键，不开等于约束失效；仅用于开发模式，SQL 保持可移植以兼容生产库。

> 完整模板（38 行）见 `refs/http-data.md` →「8.1 SQLite（开发模式）」

### 8.2 迁移策略

```
migrations/
├── 001_create_users.sql
├── 002_add_email_unique.sql
└── 003_create_sessions.sql
```

- 序号三位数，描述英文 snake_case
- 所有迁移幂等（`CREATE TABLE IF NOT EXISTS` / `ALTER TABLE ... IF NOT EXISTS`）
- 应用启动时自动按序执行

### 8.3 SQL 最佳实践

- 始终使用参数化查询（`?` 占位符），禁止字符串拼接
- 查询结果立即序列化为 `dict`，不把 cursor 传出函数作用域
- 长查询拆分多行，关键字大写：

```python
rows = self.fetch_all(
    """SELECT u.id, u.name, u.email, u.created_at
         FROM users u
        WHERE u.status = ?
        ORDER BY u.created_at DESC
        LIMIT ? OFFSET ?""",
    (status, limit, offset),
)
```

- 使用 `PRAGMA journal_mode=WAL`（SQLite 并发读写）
- 使用 `PRAGMA foreign_keys=ON`（强制外键约束）

---

## 9. 测试

### 9.1 pytest 配置

**约束**：`conftest.py` 只放 fixture（client / settings / auth_headers），不放用例；测试数据自建自清，不依赖开发库里已有的数据。

> 完整模板（21 行）见 `refs/testing.md` →「9.1 pytest 配置」

### 9.2 Handler 测试

**约束**：handler 测试用 `TestClient` 走完整 HTTP 栈，断言状态码 + 响应体字段；必须覆盖成功、参数校验失败（422）、资源不存在（404）三类路径。

> 完整模板（25 行）见 `refs/testing.md` →「9.2 Handler 测试」

### 9.3 Service 单元测试

```python
# tests/test_services/test_user_service.py
def test_create_user_duplicate_email(service, test_db):
    service.create(CreateUserRequest(name="A", email="a@test.com", age=20))
    with pytest.raises(ConflictError, match="邮箱已存在"):
        service.create(CreateUserRequest(name="B", email="a@test.com", age=20))
```

### 9.4 测试原则

- 每个 handler 覆盖：正常路径、校验失败、不存在、未授权
- 使用内存 SQLite（`:memory:`）或临时文件作为测试数据库
- 外部 HTTP 调用使用 `responses` 库或 `pytest-httpx` mock
- 测试命名：`test_<被测函数>_<场景>_<预期结果>`

---

## 10. 安全

### 10.1 SQL 注入防护

- **100% 参数化查询**，使用 `?` 占位符

```python
# ✅ 正确
conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))

# ❌ 禁止
conn.execute(f"SELECT * FROM users WHERE id = {user_id}")
```

- 动态排序 / 分组字段必须白名单：

```python
ALLOWED_SORT_FIELDS = frozenset({"id", "name", "created_at", "email"})

def list_users(sort_by: str = "id") -> list[User]:
    if sort_by not in ALLOWED_SORT_FIELDS:
        raise BadRequestError(f"不支持的排序字段: {sort_by}")
    # sort_by 已验证安全，可拼接
    return db.fetch_all(f"SELECT * FROM users ORDER BY {sort_by}")
```

### 10.2 输入校验

- 所有外部输入使用 Pydantic 模型校验
- 文件上传校验 MIME 类型和大小：

```python
ALLOWED_MIME_TYPES = frozenset({
    "image/jpeg", "image/png", "image/gif",
    "application/pdf", "text/plain", "text/csv",
})

def validate_upload(filename: str, content_type: str, size: int, max_size: int) -> None:
    if size > max_size:
        raise BadRequestError("文件大小超限")
    if ".." in filename or "/" in filename or "\\" in filename:
        raise BadRequestError("文件名包含非法字符")
    if content_type not in ALLOWED_MIME_TYPES:
        raise BadRequestError("不支持的文件类型")
```

### 10.3 敏感信息

- 所有密钥 / Token / 连接串通过环境变量或 `.env` 读取：

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model_config = dict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "sqlite:///app.db"          # 开发；部署时设为 postgresql://...
    secret_key: str          # 必填，无默认值 = 启动即报错
    api_key_hash: str
```

- `.env` 加入 `.gitignore`，提供 `.env.example` 模板
- 禁止在日志中打印密码、Token、完整 SQL 参数

---

## 11. 质量门槛

### 11.1 自动化检查

| 检查项 | 命令 | 标准 |
|--------|------|------|
| 格式化 | `black --check src/ tests/` | 零差异 |
| Lint | `ruff check src/ tests/` | 零错误 |
| 类型检查 | `mypy src/` | 零错误 |
| 测试 | `pytest tests/ -v` | 100% 通过 |
| 覆盖率 | `pytest --cov=src --cov-report=term` | ≥ 80% 行覆盖 |

### 11.2 Code Review 检查

| 检查项 | 要点 |
|--------|------|
| 类型注解 | 所有公共函数有完整注解，无裸 `Any` |
| SQL 参数化 | 100% 使用 `?` 占位符 |
| 动态 SQL | 排序/分组字段白名单校验 |
| 异常不吞 | 无 `except: pass`，所有 IO 有 try/except |
| 无硬编码 | 配置从 Settings / 环境变量读取 |
| 函数长度 | 单函数 ≤ 50 行 |


## 完整模板索引

> 以下文件是可直接复制的完整模板 / 配置文件，仅在需要照抄时查阅；约束条文都在上文。

- `refs/project.md` — 2.1 推荐布局、2.2 pyproject.toml 规范
- `refs/code-patterns.md` — 3.3 Docstring（PEP 257）、4.2 Pydantic v2 模型、5.1 异常层次、5.4 上下文管理器
- `refs/http-data.md` — 5.2 FastAPI 异常处理、7.1 路由组织、7.2 Handler 签名、7.3 依赖注入、7.4 中间件、8.1 SQLite（开发模式）
- `refs/testing.md` — 9.1 pytest 配置、9.2 Handler 测试