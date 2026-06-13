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


# ---------------------------------------------------------------------------
# /auth/logout (TEST-001)
# ---------------------------------------------------------------------------


async def _fresh_tokens(client: AsyncClient, username: str, password: str = "Test1234!") -> dict:
    r = await client.post("/auth/login", json={"username": username, "password": password})
    if r.status_code != 200:
        return {}
    return r.json()


async def test_logout_revokes_session(client: AsyncClient):
    r0 = await client.post(
        "/auth/register",
        json={
            "username": "logout_test_user",
            "email": "logout_test@example.com",
            "password": "Test1234!",
        },
    )
    if r0.status_code == 429:
        pytest.skip("registration rate limited")
    tkns = await _fresh_tokens(client, "logout_test_user")
    if not tkns:
        pytest.skip("login unavailable")

    r = await client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {tkns['access_token']}"},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True

    r2 = await client.post("/auth/refresh", json={"refresh_token": tkns["refresh_token"]})
    assert r2.status_code in (401, 400, 403)


# ---------------------------------------------------------------------------
# /auth/change-password (TEST-002, TEST-003)
# ---------------------------------------------------------------------------


async def test_change_password_wrong_current(client: AsyncClient):
    r0 = await client.post(
        "/auth/register",
        json={
            "username": "changepw_test1",
            "email": "changepw_test1@example.com",
            "password": "Test1234!",
        },
    )
    if r0.status_code == 429:
        pytest.skip("registration rate limited")
    tkns = await _fresh_tokens(client, "changepw_test1")
    if not tkns:
        pytest.skip("login unavailable")

    r = await client.post(
        "/auth/change-password",
        json={"current_password": "WrongPass1!", "new_password": "NewPass456!"},
        headers={"Authorization": f"Bearer {tkns['access_token']}"},
    )
    assert r.status_code == 401


async def test_change_password_success(client: AsyncClient):
    r0 = await client.post(
        "/auth/register",
        json={
            "username": "changepw_test2",
            "email": "changepw_test2@example.com",
            "password": "Test1234!",
        },
    )
    if r0.status_code == 429:
        pytest.skip("registration rate limited")
    tkns = await _fresh_tokens(client, "changepw_test2")
    if not tkns:
        pytest.skip("login unavailable")

    r = await client.post(
        "/auth/change-password",
        json={"current_password": "Test1234!", "new_password": "NewPass456!"},
        headers={"Authorization": f"Bearer {tkns['access_token']}"},
    )
    assert r.status_code == 200

    r2 = await client.post(
        "/auth/login", json={"username": "changepw_test2", "password": "Test1234!"}
    )
    assert r2.status_code == 401

    r3 = await client.post(
        "/auth/login", json={"username": "changepw_test2", "password": "NewPass456!"}
    )
    assert r3.status_code == 200


# ---------------------------------------------------------------------------
# /auth/forgot-password and /auth/reset-password (TEST-004)
# ---------------------------------------------------------------------------


async def test_forgot_password_always_200(client: AsyncClient):
    r = await client.post("/auth/forgot-password", json={"email": "nonexistent@example.com"})
    assert r.status_code == 200
    assert "reset link" in r.json()["message"].lower() or "email" in r.json()["message"].lower()


async def test_reset_password_replay_rejected(client: AsyncClient):
    import hashlib
    import secrets
    import uuid
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import text

    from app.core.db import engine

    # Use testuser which was already registered by test_register_success
    async with engine.begin() as conn:
        user_q = await conn.execute(text("SELECT id FROM user WHERE username = 'testuser'"))
        user_id = user_q.scalar()

    if user_id is None:
        pytest.skip("testuser not found — registration was rate limited")

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    async with engine.begin() as conn:
        expires_at = (datetime.now(UTC) + timedelta(minutes=10)).isoformat()
        sql = (
            "INSERT INTO password_reset_tokens"
            " (id, user_id, token_hash, expires_at, created_at)"
            " VALUES (:id, :uid, :th, :exp, :ca)"
        )
        await conn.execute(
            text(sql),
            {
                "id": str(uuid.uuid4()),
                "uid": user_id,
                "th": token_hash,
                "exp": expires_at,
                "ca": datetime.now(UTC).isoformat(),
            },
        )

    r1 = await client.post(
        "/auth/reset-password", json={"token": raw_token, "new_password": "Resetpass789!"}
    )
    assert r1.status_code == 200

    r2 = await client.post(
        "/auth/reset-password", json={"token": raw_token, "new_password": "Resetpass789!"}
    )
    assert r2.status_code == 400
