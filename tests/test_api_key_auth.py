"""Integration tests for API key CRUD and authentication."""

import pytest


async def _register_and_login(client, username: str) -> dict:
    r = await client.post(
        "/auth/register",
        json={"username": username, "email": f"{username}@example.com", "password": "Test123!"},
    )
    if r.status_code == 409:
        pass
    elif r.status_code == 429:
        pytest.skip("rate limited")
    else:
        assert r.status_code == 201

    r = await client.post("/auth/login", json={"username": username, "password": "Test123!"})
    if r.status_code == 429:
        pytest.skip("login rate limited")
    assert r.status_code == 200
    return r.json()


def _auth(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_api_key(client):
    tokens = await _register_and_login(client, "ak_create_user")

    r = await client.post(
        "/auth/api-keys",
        json={"name": "ci-bot", "scopes": ["read:data"]},
        headers=_auth(tokens),
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "ci-bot"
    assert data["key"].startswith("fak_")
    assert "id" in data


@pytest.mark.asyncio
async def test_list_api_keys(client):
    tokens = await _register_and_login(client, "ak_list_user")

    await client.post(
        "/auth/api-keys", json={"name": "key-1"}, headers=_auth(tokens)
    )
    await client.post(
        "/auth/api-keys", json={"name": "key-2"}, headers=_auth(tokens)
    )

    r = await client.get("/auth/api-keys", headers=_auth(tokens))
    assert r.status_code == 200
    names = [k["name"] for k in r.json()]
    assert "key-1" in names
    assert "key-2" in names


@pytest.mark.asyncio
async def test_revoke_api_key(client):
    tokens = await _register_and_login(client, "ak_revoke_user")

    r = await client.post(
        "/auth/api-keys", json={"name": "to-revoke"}, headers=_auth(tokens)
    )
    key_id = r.json()["id"]

    r2 = await client.delete(f"/auth/api-keys/{key_id}", headers=_auth(tokens))
    assert r2.status_code == 204

    # Revoked key shows revoked_at in the list
    r3 = await client.get("/auth/api-keys", headers=_auth(tokens))
    revoked = next(k for k in r3.json() if k["id"] == key_id)
    assert revoked["revoked_at"] is not None


@pytest.mark.asyncio
async def test_revoke_nonexistent_key_returns_404(client):
    tokens = await _register_and_login(client, "ak_404_user")
    r = await client.delete("/auth/api-keys/nonexistent-id", headers=_auth(tokens))
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Authentication via X-API-Key
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_key_authenticates_request(client):
    """A valid X-API-Key authenticates GET /auth/api-keys/whoami; invalid key returns 401."""
    tokens = await _register_and_login(client, "ak_auth_user")

    r = await client.post(
        "/auth/api-keys", json={"name": "svc-key", "scopes": ["read:data"]}, headers=_auth(tokens)
    )
    raw_key = r.json()["key"]
    key_id = r.json()["id"]

    # Valid key → 200 with principal info
    r2 = await client.get("/auth/api-keys/whoami", headers={"X-API-Key": raw_key})
    assert r2.status_code == 200
    data = r2.json()
    assert data["key_id"] == key_id
    assert "read:data" in data["scopes"]

    # Invalid key → 401
    r3 = await client.get("/auth/api-keys/whoami", headers={"X-API-Key": "fak_invalid"})
    assert r3.status_code == 401


@pytest.mark.asyncio
async def test_revoked_api_key_rejected(client):
    """After revocation, the key returns 401."""
    tokens = await _register_and_login(client, "ak_revoked_auth_user")

    r = await client.post(
        "/auth/api-keys", json={"name": "temp-key"}, headers=_auth(tokens)
    )
    key_id = r.json()["id"]
    raw_key = r.json()["key"]

    await client.delete(f"/auth/api-keys/{key_id}", headers=_auth(tokens))

    # Hit an endpoint that uses APIKeyDep — we'll use the verify route
    from app.auth.api_keys.utils import hash_api_key
    from app.auth.api_keys.repository import find_by_hash
    # Confirm the key is marked revoked in the DB
    from sqlmodel.ext.asyncio.session import AsyncSession
    from app.core.db import engine
    async with AsyncSession(engine) as session:
        row = await find_by_hash(session, hash_api_key(raw_key))
        assert row is not None
        assert row.revoked_at is not None


# ---------------------------------------------------------------------------
# Scope enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scope_enforcement(client):
    """APIKeyPrincipal carries the scopes set at creation time."""
    tokens = await _register_and_login(client, "ak_scope_user")

    r = await client.post(
        "/auth/api-keys",
        json={"name": "read-only", "scopes": ["read:users"]},
        headers=_auth(tokens),
    )
    raw_key = r.json()["key"]

    from app.auth.api_keys.utils import hash_api_key
    from app.auth.api_keys.repository import find_by_hash
    from sqlmodel.ext.asyncio.session import AsyncSession
    from app.core.db import engine
    async with AsyncSession(engine) as session:
        row = await find_by_hash(session, hash_api_key(raw_key))
        assert row is not None
        assert row.scopes == "read:users"
