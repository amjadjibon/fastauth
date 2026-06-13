import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="session")

REGISTER_PAYLOAD = {
    "username": "testuser",
    "email": "testuser@example.com",
    "password": "Secret123",
}


# ---------------------------------------------------------------------------
# /auth/register
# ---------------------------------------------------------------------------


async def test_register_success(client: AsyncClient):
    r = await client.post("/auth/register", json=REGISTER_PAYLOAD)
    assert r.status_code == 201
    body = r.json()
    assert "user_id" in body
    assert "access_token" not in body
    assert "refresh_token" not in body


async def test_register_duplicate_username(client: AsyncClient):
    r = await client.post("/auth/register", json=REGISTER_PAYLOAD)
    assert r.status_code == 409
    assert r.json()["detail"] == "Username already taken"


async def test_register_invalid_username_too_short(client: AsyncClient):
    r = await client.post("/auth/register", json={**REGISTER_PAYLOAD, "username": "ab"})
    assert r.status_code == 422


async def test_register_invalid_username_special_chars(client: AsyncClient):
    r = await client.post("/auth/register", json={**REGISTER_PAYLOAD, "username": "bad user!"})
    assert r.status_code == 422


async def test_register_invalid_email(client: AsyncClient):
    payload = {**REGISTER_PAYLOAD, "username": "other1", "email": "not-an-email"}
    r = await client.post("/auth/register", json=payload)
    assert r.status_code == 422


async def test_register_weak_password_no_uppercase(client: AsyncClient):
    payload = {**REGISTER_PAYLOAD, "username": "other2", "password": "secret123"}
    r = await client.post("/auth/register", json=payload)
    assert r.status_code == 422


async def test_register_weak_password_no_digit(client: AsyncClient):
    payload = {**REGISTER_PAYLOAD, "username": "other3", "password": "Secretpass"}
    r = await client.post("/auth/register", json=payload)
    assert r.status_code == 422


async def test_register_password_too_short(client: AsyncClient):
    payload = {**REGISTER_PAYLOAD, "username": "other4", "password": "S1a"}
    r = await client.post("/auth/register", json=payload)
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# /auth/login
# ---------------------------------------------------------------------------


async def test_login_success(client: AsyncClient):
    r = await client.post("/auth/login", json={"username": "testuser", "password": "Secret123"})
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient):
    r = await client.post("/auth/login", json={"username": "testuser", "password": "WrongPass1"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid credentials"


async def test_login_unknown_user(client: AsyncClient):
    r = await client.post("/auth/login", json={"username": "nobody", "password": "Secret123"})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# /auth/refresh
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
async def tokens(client: AsyncClient):
    r = await client.post("/auth/login", json={"username": "testuser", "password": "Secret123"})
    return r.json()


async def test_refresh_success(client: AsyncClient, tokens: dict):
    r = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" in body


async def test_refresh_with_access_token_fails(client: AsyncClient, tokens: dict):
    r = await client.post("/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert r.status_code == 401


async def test_refresh_invalid_token(client: AsyncClient):
    r = await client.post("/auth/refresh", json={"refresh_token": "not.a.token"})
    assert r.status_code == 401


async def test_refresh_empty_token(client: AsyncClient):
    r = await client.post("/auth/refresh", json={"refresh_token": ""})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# /auth/me
# ---------------------------------------------------------------------------


async def test_me_success(client: AsyncClient, tokens: dict):
    r = await client.get("/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "testuser"
    assert body["email"] == "testuser@example.com"
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body
    assert "hashed_password" not in body


async def test_me_no_token(client: AsyncClient):
    r = await client.get("/auth/me")
    assert r.status_code == 401


async def test_me_invalid_token(client: AsyncClient):
    r = await client.get("/auth/me", headers={"Authorization": "Bearer bad.token.here"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid token"


async def test_me_with_refresh_token_fails(client: AsyncClient, tokens: dict):
    r = await client.get("/auth/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid token type"
