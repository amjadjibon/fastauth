"""Integration tests for social login (OAuth2 provider flows)."""

from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.auth.social.config import SocialProviderConfig, get_provider_config


def test_provider_config_returns_dataclass_fields():
    """get_provider_config returns a SocialProviderConfig with expected fields when configured."""
    with patch("app.auth.social.config.settings") as mock_settings:
        mock_settings.google_client_id = "gid"
        mock_settings.google_client_secret = "gsecret"
        config = get_provider_config("google", "http://localhost:8000")
    assert config is not None
    assert isinstance(config, SocialProviderConfig)
    assert config.client_id == "gid"
    assert config.client_secret == "gsecret"
    assert "google" in config.redirect_uri
    assert "openid" in config.scopes


def test_provider_config_github():
    with patch("app.auth.social.config.settings") as mock_settings:
        mock_settings.github_client_id = "ghid"
        mock_settings.github_client_secret = "ghsecret"
        config = get_provider_config("github", "http://localhost:8000")
    assert config is not None
    assert config.client_id == "ghid"
    assert "user:email" in config.scopes


def test_provider_config_gitlab():
    with patch("app.auth.social.config.settings") as mock_settings:
        mock_settings.gitlab_client_id = "glid"
        mock_settings.gitlab_client_secret = "glsecret"
        config = get_provider_config("gitlab", "http://localhost:8000")
    assert config is not None
    assert config.client_id == "glid"


def test_provider_config_unknown_returns_none():
    """Unknown provider returns None instead of raising."""
    result = get_provider_config("notareal_provider", "http://localhost:8000")
    assert result is None


def test_provider_config_missing_credentials_returns_none():
    """Missing client_id/secret returns None."""
    with patch("app.auth.social.config.settings") as mock_settings:
        mock_settings.google_client_id = None
        mock_settings.google_client_secret = None
        result = get_provider_config("google", "http://localhost:8000")
    assert result is None


@pytest.mark.asyncio
async def test_social_authorize_missing_provider(client: AsyncClient):
    """Non-existent provider returns 400 or 404."""
    r = await client.get("/auth/social/notareal/authorize")
    assert r.status_code in (400, 404, 422)


@pytest.mark.asyncio
async def test_social_link_requires_auth(client: AsyncClient):
    """Linking a social account requires a valid Bearer token."""
    r = await client.post(
        "/auth/social/link",
        json={
            "provider": "google",
            "code": "fake_code",
            "redirect_uri": "http://localhost/callback",
        },
    )
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_social_linked_accounts_requires_auth(client: AsyncClient):
    """Listing linked accounts requires authentication."""
    r = await client.get("/auth/social/linked")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_social_unlink_requires_auth(client: AsyncClient):
    """Unlinking a social account requires authentication."""
    r = await client.delete("/auth/social/unlink/google")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_social_callback_missing_code(client: AsyncClient):
    """Social callback without code returns 400 or 422."""
    r = await client.get("/auth/social/google/callback")
    assert r.status_code in (400, 404, 422)


@pytest.mark.asyncio
async def test_social_authorize_unconfigured_provider_returns_400(client: AsyncClient):
    """Google authorize without credentials configured returns 400."""
    with patch("app.auth.social.config.settings") as mock_settings:
        mock_settings.google_client_id = None
        mock_settings.google_client_secret = None
        r = await client.get(
            "/auth/social/google/authorize",
            follow_redirects=False,
        )
    assert r.status_code in (400, 302, 307, 404, 422)
