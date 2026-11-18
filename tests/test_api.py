
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db


# Тестовая база данных SQLite в оперативной памяти
@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    Base.metadata.create_all(bind=engine)

    # Подменяем подключение к основной БД тестовым
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


PASSWORD = "StrongPass1!"


def register(client, login):
    return client.post(
        "/api/register",
        json={"login": login, "password": PASSWORD},
    )


def login_headers(client, login):
    response = client.post(
        "/api/login",
        json={"login": login, "password": PASSWORD},
    )

    assert response.status_code == 200

    token = response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


# 1. Успешная регистрация
def test_register_success(client):
    response = register(client, "testuser")

    assert response.status_code == 201
    assert response.json()["login"] == "testuser"
    assert "password_hash" not in response.json()


# 2. Регистрация с уже существующим логином
def test_register_duplicate_login(client):
    register(client, "testuser")

    response = register(client, "testuser")

    assert response.status_code == 409


# 3. Регистрация со слабым паролем
def test_register_weak_password(client):
    response = client.post(
        "/api/register",
        json={"login": "testuser", "password": "weak"},
    )

    assert response.status_code == 422


# 4. Пользователь с правом чтения может прочитать ресурс
def test_resource_read_allowed(client):
    register(client, "owner")
    register(client, "reader")

    owner_headers = login_headers(client, "owner")
    reader_headers = login_headers(client, "reader")

    resource = client.post(
        "/api/resources",
        json={"name": "Документ", "content": "Тестовое содержимое"},
        headers=owner_headers,
    )

    resource_id = resource.json()["id"]

    client.post(
        f"/api/resources/{resource_id}/permissions",
        json={
            "user_login": "reader",
            "can_read": True,
            "can_update": False,
            "can_delete": False,
        },
        headers=owner_headers,
    )

    response = client.get(
        f"/api/resources/{resource_id}",
        headers=reader_headers,
    )

    assert response.status_code == 200
    assert response.json()["content"] == "Тестовое содержимое"


# 5. Пользователь без прав не может изменить или удалить ресурс
def test_resource_access_denied(client):
    register(client, "owner")
    register(client, "outsider")

    owner_headers = login_headers(client, "owner")
    outsider_headers = login_headers(client, "outsider")

    resource = client.post(
        "/api/resources",
        json={"name": "Документ", "content": "Тестовое содержимое"},
        headers=owner_headers,
    )

    resource_id = resource.json()["id"]

    update_response = client.put(
        f"/api/resources/{resource_id}",
        json={"name": "Изменённый документ", "content": "Новое содержимое"},
        headers=outsider_headers,
    )

    delete_response = client.delete(
        f"/api/resources/{resource_id}",
        headers=outsider_headers,
    )

    assert update_response.status_code == 403
    assert delete_response.status_code == 403
