> 本文档由 `SKILL.md` 外移而来：完整可复制模板与配置文件。规则与约束仍以 `SKILL.md` 为准。

## 9.1 pytest 配置

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from src.main import create_app
from src.config import Settings


@pytest.fixture
def settings():
    return Settings(database_url=":memory:", testing=True)


@pytest.fixture
def client(settings):
    app = create_app(settings)
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token"}
```

## 9.2 Handler 测试

```python
# tests/test_handlers/test_user.py
def test_create_user_success(client, auth_headers):
    resp = client.post(
        "/api/users",
        json={"name": "Alice", "email": "alice@example.com", "age": 30},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Alice"
    assert data["email"] == "alice@example.com"


def test_create_user_invalid_email(client, auth_headers):
    resp = client.post(
        "/api/users",
        json={"name": "Bob", "email": "not-an-email", "age": 25},
        headers=auth_headers,
    )
    assert resp.status_code == 422  # Pydantic 校验失败


def test_get_user_not_found(client):
    resp = client.get("/api/users/99999")
    assert resp.status_code == 404
```
