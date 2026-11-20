> 本文档由 `SKILL.md` 外移而来：完整可复制模板与配置文件。规则与约束仍以 `SKILL.md` 为准。

## 2.1 推荐布局

```
project/
├── pyproject.toml               # 项目元数据 + 依赖 + 工具配置
├── requirements.txt             # 精确 pin 的生产依赖
├── requirements-dev.txt         # 开发依赖（lint / test）
├── .python-version              # pyenv / mise 使用的 Python 版本
├── .env.example                 # 配置模板
├── .env                         # 实际配置（gitignore）
├── src/                         # 应用源码（src 布局避免意外导入）
│   ├── __init__.py
│   ├── main.py                  # 应用入口
│   ├── config.py                # 配置加载
│   ├── router.py                # 路由聚合
│   ├── models/                  # Pydantic 数据模型
│   │   ├── __init__.py
│   │   └── user.py
│   ├── services/                # 业务逻辑
│   │   ├── __init__.py
│   │   └── user_service.py
│   ├── handlers/                # HTTP 处理函数
│   │   ├── __init__.py
│   │   └── user_handlers.py
│   ├── middleware/               # 中间件
│   │   ├── __init__.py
│   │   └── auth.py
│   ├── errors/                  # 异常定义
│   │   ├── __init__.py
│   │   └── exceptions.py
│   └── utils/                   # 工具函数
│       └── __init__.py
├── tests/                       # 测试目录
│   ├── __init__.py
│   ├── conftest.py              # 共享 fixtures
│   ├── test_handlers/
│   └── test_services/
└── migrations/                  # 数据库迁移（如使用 Alembic）
```

## 2.2 pyproject.toml 规范

```toml
[project]
name = "my-server"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110,<1",
    "uvicorn[standard]>=0.30,<1",
    "pydantic>=2,<3",
    "pydantic-settings>=2,<3",
    "httpx>=0.27,<1",
]

[project.optional-dependencies]
dev = [
    "black>=24",
    "ruff>=0.5",
    "mypy>=1.10",
    "pytest>=8",
    "pytest-cov>=5",
    "httpx>=0.27",
]

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "SIM"]

[tool.mypy]
strict = true
python_version = "3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"
```
