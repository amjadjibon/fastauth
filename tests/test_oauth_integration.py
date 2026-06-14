"""Integration tests for OAuth2 authorization code flow with PKCE."""

import pytest
from httpx import AsyncClient

from app.auth.oauth.domain import (
    generate_code_challenge,
    generate_code_verifier,
    verify_code_challenge,
)


def test_pkce_round_trip():
    verifier = generate_code_verifier()
    challenge = generate_code_challenge(verifier)
    assert verify_code_challenge(verifier, challenge)


def test_pkce_wrong_verifier():
    verifier = generate_code_verifier()
    challenge = generate_code_challenge(verifier)
    assert not verify_code_challenge("wrong_verifier", challenge)


@pytest.mark.asyncio
async def test_oidc_discovery(client: AsyncClient):
    r = await client.get("/.well-known/openid-configuration")
    assert r.status_code == 200
    data = r.json()
    assert "issuer" in data
    assert "authorization_endpoint" in data
    assert "token_endpoint" in data
    assert "jwks_uri" in data
    assert "openid" in data["scopes_supported"]


@pytest.mark.asyncio
async def test_jwks_endpoint(client: AsyncClient):
    r = await client.get("/.well-known/jwks.json")
    assert r.status_code == 200
    data = r.json()
    assert "keys" in data


@pytest.mark.asyncio
async def test_oauth_authorize_requires_auth(client: AsyncClient):
    r = await client.post(
        "/oauth/authorize",
        json={
            "response_type": "code",
            "client_id": "test-client",
            "redirect_uri": "http://localhost/callback",
            "scope": "openid",
        },
    )
    assert r.status_code in (401, 403)  # requires Bearer token


@pytest.mark.asyncio
async def test_oauth_token_missing_fields(client: AsyncClient):
    r = await client.post(
        "/oauth/token",
        json={
            "grant_type": "authorization_code",
        },
    )
    assert r.status_code == 400
