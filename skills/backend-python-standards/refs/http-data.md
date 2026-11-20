> 本文档由 `SKILL.md` 外移而来：完整可复制模板与配置文件。规则与约束仍以 `SKILL.md` 为准。

## 5.2 FastAPI 异常处理

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        status_map = {
            BadRequestError: 400,
            UnauthorizedError: 401,
            ForbiddenError: 403,
            NotFoundError: 404,
            ConflictError: 409,
        }
        status = status_map.get(type(exc), 500)
        return JSONResponse(
            status_code=status,
            content={"code": status, "message": str(exc)},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("未处理异常")
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": "服务器内部错误"},
        )
```

## 7.1 路由组织

```python
# router.py — 路由聚合
from fastapi import FastAPI
from src.handlers import user_handlers, health_handlers


def create_app() -> FastAPI:
    app = FastAPI(title="My API", version="0.1.0")

    # 注册异常处理
    register_exception_handlers(app)

    # 注册路由
    app.include_router(health_handlers.router, tags=["Health"])
    app.include_router(user_handlers.router, prefix="/api", tags=["Users"])

    return app
```

## 7.2 Handler 签名

```python
# handlers/user_handlers.py
from fastapi import APIRouter, Depends, Path, Query, status

router = APIRouter()


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    query: PaginationQuery = Depends(),
    service: UserService = Depends(get_user_service),
) -> list[UserResponse]:
    users, total = service.list(query)
    return users


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    req: CreateUserRequest,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    return service.create(req)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int = Path(gt=0),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    user = service.find(user_id)
    if user is None:
        raise NotFoundError("用户不存在")
    return user
```

## 7.3 依赖注入

```python
# services/deps.py
from functools import lru_cache
from src.config import Settings
from src.services.user_service import UserService


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_user_service() -> UserService:
    settings = get_settings()
    return UserService(settings.database_url)
```

## 7.4 中间件

```python
# middleware/auth.py
from fastapi import Request, HTTPException


async def auth_middleware(request: Request, call_next):
    """简易 Bearer Token 认证中间件"""
    if request.url.path in ("/health", "/api/health"):
        return await call_next(request)

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, detail="未提供认证信息")

    token = auth.removeprefix("Bearer ")
    # 验证 token ...
    return await call_next(request)
```

## 8.1 SQLite（开发模式）

```python
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class Database:
    def __init__(self, db_path: str | Path):
        self._path = str(db_path)

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def fetch_one(self, sql: str, params: tuple = ()) -> dict | None:
        with self.connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def fetch_all(self, sql: str, params: tuple = ()) -> list[dict]:
        with self.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def execute(self, sql: str, params: tuple = ()) -> int:
        with self.connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.lastrowid
```
