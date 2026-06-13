import urllib.parse

import httpx

from app.auth.social.config import SocialProviderConfig
from app.auth.social.providers.base import SocialAuthProvider

_GITLAB_BASE = "https://gitlab.com"
_AUTH_URL = f"{_GITLAB_BASE}/oauth/authorize"
_TOKEN_URL = f"{_GITLAB_BASE}/oauth/token"
_USERINFO_URL = f"{_GITLAB_BASE}/api/v4/user"


class GitLabProvider(SocialAuthProvider):
    def __init__(self, config: SocialProviderConfig) -> None:
        super().__init__(config)

    async def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.config.scopes),
            "state": state,
        }
        return f"{_AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(_TOKEN_URL, data={
                "code": code,
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "redirect_uri": self.config.redirect_uri,
                "grant_type": "authorization_code",
            })
            resp.raise_for_status()
            return resp.json()

    async def get_user_info(self, access_token: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                _USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "id": str(data["id"]),
                "email": data.get("email"),
                "username": data.get("username"),
                "name": data.get("name"),
            }
