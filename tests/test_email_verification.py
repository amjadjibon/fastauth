"""Integration tests for the email verification flow."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import settings

_PATCH_TARGET = "app.auth.router.send_verification_email"


async def _register(client, username: str) -> str:
    r = await client.post(
        "/auth/register",
        json={"username": username, "email": f"{username}@example.com", "password": "Test123!"},
    )
    if r.status_code == 429:
        pytest.skip("rate limited")
    assert r.status_code == 201
    return r.json()["user_id"]


async def _login(client, username: str):
    r = await client.post("/auth/login", json={"username": username, "password": "Test123!"})
    if r.status_code == 429:
        pytest.skip("rate limited")
    return r


# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_creates_unverified_user(client):
    with patch(_PATCH_TARGET, new_callable=AsyncMock):
        await _register(client, "ev_unverified")

    r = await _login(client, "ev_unverified")
    assert r.status_code == 200
    access = r.json()["access_token"]

    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 200
    assert me.json()["email_verified"] is False


@pytest.mark.asyncio
async def test_verify_email_marks_user_verified(client):
    tokens: list[str] = []

    async def capture(user_id, email, token):
        tokens.append(token)

    with patch(_PATCH_TARGET, side_effect=capture):
        await _register(client, "ev_verify")

    assert tokens, "send_verification_email was not called"
    token = tokens[0]

    r = await client.post("/auth/verify-email", json={"token": token})
    assert r.status_code == 200
    assert r.json()["ok"] is True

    r2 = await _login(client, "ev_verify")
    assert r2.status_code == 200
    access = r2.json()["access_token"]
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.json()["email_verified"] is True


@pytest.mark.asyncio
async def test_verify_email_token_consumed(client):
    tokens: list[str] = []

    async def capture(user_id, email, token):
        tokens.append(token)

    with patch(_PATCH_TARGET, side_effect=capture):
        await _register(client, "ev_consumed")

    token = tokens[0]
    await client.post("/auth/verify-email", json={"token": token})
    r2 = await client.post("/auth/verify-email", json={"token": token})
    assert r2.status_code == 400


@pytest.mark.asyncio
async def test_verify_email_invalid_token(client):
    r = await client.post("/auth/verify-email", json={"token": "totally-invalid-token"})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_resend_verification_unknown_email(client):
    r = await client.post("/auth/resend-verification", json={"email": "nobody@example.com"})
    assert r.status_code == 200
    assert "message" in r.json()


@pytest.mark.asyncio
async def test_login_blocked_when_unverified(client):
    original = settings.require_email_verification
    settings.require_email_verification = True
    try:
        with patch(_PATCH_TARGET, new_callable=AsyncMock):
            await _register(client, "ev_blocked")
        r = await _login(client, "ev_blocked")
        assert r.status_code == 403
        assert "not verified" in r.json()["detail"].lower()
    finally:
        settings.require_email_verification = original


@pytest.mark.asyncio
async def test_login_allowed_after_verification(client):
    tokens: list[str] = []

    async def capture(user_id, email, token):
        tokens.append(token)

    original = settings.require_email_verification
    settings.require_email_verification = True
    try:
        with patch(_PATCH_TARGET, side_effect=capture):
            await _register(client, "ev_allowed")

        assert tokens
        await client.post("/auth/verify-email", json={"token": tokens[0]})

        r = await _login(client, "ev_allowed")
        assert r.status_code == 200
        assert r.json()["access_token"] is not None
    finally:
        settings.require_email_verification = original
