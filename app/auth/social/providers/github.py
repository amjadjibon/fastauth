import urllib.parse

import httpx

from app.auth.social.config import SocialProviderConfig
from app.auth.social.providers.base import SocialAuthProvider

_AUTH_URL = "https://github.com/login/oauth/authorize"
_TOKEN_URL = "https://github.com/login/oauth/access_token"
_USERINFO_URL = "https://api.github.com/user"
_EMAILS_URL = "https://api.github.com/user/emails"


class GitHubProvider(SocialAuthProvider):
    def __init__(self, config: SocialProviderConfig) -> None:
        super().__init__(config)

    async def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "scope": " ".join(self.config.scopes),
            "state": state,
        }
        return f"{_AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "redirect_uri": self.config.redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_user_info(self, access_token: str) -> dict:
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        async with httpx.AsyncClient() as client:
            user_resp = await client.get(_USERINFO_URL, headers=headers)
            user_resp.raise_for_status()
            user_data = user_resp.json()

            email = user_data.get("email")
            if not email:
                email_resp = await client.get(_EMAILS_URL, headers=headers)
                if email_resp.status_code == 200:
                    for e in email_resp.json():
                        if e.get("primary") and e.get("verified"):
                            email = e["email"]
                            break

            return {
                "id": str(user_data["id"]),
                "email": email,
                "username": user_data.get("login"),
                "name": user_data.get("name"),
            }
