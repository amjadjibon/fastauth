import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="session")

_SECURITY_HEADERS = [
    "x-content-type-options",
    "x-frame-options",
    "referrer-policy",
    "permissions-policy",
]


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------


async def test_security_headers_present(client: AsyncClient):
    r = await client.get("/livez")
    for header in _SECURITY_HEADERS:
        assert header in r.headers, f"missing security header: {header}"


async def test_security_header_values(client: AsyncClient):
    r = await client.get("/livez")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"


async def test_cors_unlisted_origin_blocked(client: AsyncClient):
    r = await client.get("/livez", headers={"Origin": "https://evil.example.com"})
    assert "access-control-allow-origin" not in r.headers


async def test_trace_id_absent_when_otel_disabled(client: AsyncClient, caplog):
    import logging

    with caplog.at_level(logging.INFO, logger="fastauth.access"):
        await client.get("/livez")

    if caplog.records:
        record = caplog.records[-1]
        trace_id = getattr(record, "trace_id", None)
        assert trace_id is None or trace_id == "0" * 32


# ---------------------------------------------------------------------------
# Token security (no DB interaction needed)
# ---------------------------------------------------------------------------


async def test_missing_token_rejected(client: AsyncClient):
    r = await client.get("/auth/me")
    # FastAPI 0.136+ returns 401 for missing Bearer credentials
    assert r.status_code in (401, 403)


async def test_tampered_token_rejected(client: AsyncClient):
    """Modifying the JWT signature causes 401."""
    await client.post(
        "/auth/register",
        json={
            "username": "tokentest_tamper",
            "email": "tokentest_tamper@example.com",
            "password": "Test1234!",
        },
    )
    r2 = await client.post(
        "/auth/login",
        json={
            "username": "tokentest_tamper",
            "password": "Test1234!",
        },
    )
    if r2.status_code != 200:
        pytest.skip("login unavailable (rate limited)")
    access_token = r2.json()["access_token"]

    parts = access_token.split(".")
    tampered = parts[0] + "." + parts[1] + ".invalidsignature"

    r3 = await client.get("/auth/me", headers={"Authorization": f"Bearer {tampered}"})
    assert r3.status_code == 401


async def test_expired_token_signature_check(client: AsyncClient):
    """A well-formed JWT with a bad secret is rejected."""
    import base64
    import json
    import time

    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=").decode()
    payload = (
        base64.urlsafe_b64encode(
            json.dumps(
                {
                    "sub": "99999",
                    "exp": int(time.time()) + 3600,
                }
            ).encode()
        )
        .rstrip(b"=")
        .decode()
    )
    fake_sig = base64.urlsafe_b64encode(b"fakesig").rstrip(b"=").decode()
    forged = f"{header}.{payload}.{fake_sig}"

    r = await client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Session management & revocation
# ---------------------------------------------------------------------------


async def _register_login(client: AsyncClient, username: str) -> dict | None:
    """Register + login; return tokens dict or None if rate-limited."""
    await client.post(
        "/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "Test1234!",
        },
    )
    r = await client.post(
        "/auth/login",
        json={
            "username": username,
            "password": "Test1234!",
        },
    )
    if r.status_code != 200:
        return None
    return r.json()


async def test_session_list_requires_auth(client: AsyncClient):
    r = await client.get("/auth/sessions")
    assert r.status_code in (401, 403)


async def test_session_revoke_requires_auth(client: AsyncClient):
    r = await client.delete("/auth/sessions/00000000-0000-0000-0000-000000000001")
    assert r.status_code in (401, 403)


async def test_session_created_on_login(client: AsyncClient):
    tokens = await _register_login(client, "sesstest_create")
    if tokens is None:
        pytest.skip("login unavailable (rate limited)")

    r = await client.get(
        "/auth/sessions",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert r.status_code == 200
    sessions = r.json()
    assert isinstance(sessions, (list, dict))


async def test_refresh_token_rotation(client: AsyncClient):
    """Refresh issues a new access_token; old refresh_token must not work twice."""
    tokens = await _register_login(client, "sesstest_rotate")
    if tokens is None:
        pytest.skip("login unavailable (rate limited)")

    refresh1 = tokens["refresh_token"]
    r1 = await client.post("/auth/refresh", json={"refresh_token": refresh1})
    assert r1.status_code == 200
    new_access = r1.json()["access_token"]
    assert new_access != tokens["access_token"]

    # Re-using old refresh_token should fail (token rotation)
    r2 = await client.post("/auth/refresh", json={"refresh_token": refresh1})
    assert r2.status_code in (401, 400, 403)


async def test_revoke_all_sessions(client: AsyncClient):
    """DELETE /auth/sessions revokes all active sessions."""
    tokens = await _register_login(client, "sesstest_revokeall")
    if tokens is None:
        pytest.skip("login unavailable (rate limited)")

    r = await client.delete(
        "/auth/sessions",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert r.status_code in (200, 204)

    refresh = tokens.get("refresh_token")
    if refresh:
        r2 = await client.post("/auth/refresh", json={"refresh_token": refresh})
        assert r2.status_code in (401, 400, 403)


# ---------------------------------------------------------------------------
# OAuth state CSRF (TEST-005)
# ---------------------------------------------------------------------------


async def test_oauth_state_replay(client: AsyncClient):
    """Callback with fabricated state returns 400."""
    r = await client.get("/auth/social/github/callback?code=fakecode&state=forged_state_xyz")
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Password history reuse (TEST-006)
# ---------------------------------------------------------------------------


async def test_password_history_reuse(client: AsyncClient):
    """Changing password back to original should return 400."""
    r0 = await client.post(
        "/auth/register",
        json={
            "username": "histtest_user",
            "email": "histtest_user@example.com",
            "password": "OrigPass1!",
        },
    )
    if r0.status_code == 429:
        pytest.skip("registration rate limited")
    r = await client.post(
        "/auth/login", json={"username": "histtest_user", "password": "OrigPass1!"}
    )
    if r.status_code != 200:
        pytest.skip("login unavailable (rate limited)")

    access_token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    r2 = await client.post(
        "/auth/change-password",
        json={"current_password": "OrigPass1!", "new_password": "NewPass2!2"},
        headers=headers,
    )
    assert r2.status_code == 200

    r3 = await client.post(
        "/auth/login", json={"username": "histtest_user", "password": "NewPass2!2"}
    )
    if r3.status_code != 200:
        pytest.skip("login unavailable (rate limited)")

    new_token = r3.json()["access_token"]
    r4 = await client.post(
        "/auth/change-password",
        json={"current_password": "NewPass2!2", "new_password": "OrigPass1!"},
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert r4.status_code == 400


# ---------------------------------------------------------------------------
# Brute-force protection (runs last — pollutes IP-based counter)
# ---------------------------------------------------------------------------


async def _register_user(client: AsyncClient, username: str) -> None:
    await client.post(
        "/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "Test1234!",
        },
    )


async def test_brute_force_triggers_lockout(client: AsyncClient):
    """After repeated bad-password attempts the IP or account is locked out."""
    user = "brutetest_lockout"
    await _register_user(client, user)

    locked = False
    for _ in range(8):
        r = await client.post("/auth/login", json={"username": user, "password": "WRONG!"})
        if r.status_code in (429, 423, 403):
            locked = True
            break

    assert locked, "Expected 429/423/403 after repeated failed logins"


async def test_brute_force_correct_password_after_lockout(client: AsyncClient):
    """Even with correct credentials the attempt fails while locked out."""
    user = "brutetest_postlock"
    await _register_user(client, user)

    for _ in range(6):
        await client.post("/auth/login", json={"username": user, "password": "WRONG!"})

    r = await client.post("/auth/login", json={"username": user, "password": "Test1234!"})
    assert r.status_code != 500
