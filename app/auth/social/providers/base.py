from abc import ABC, abstractmethod

from app.auth.social.config import SocialProviderConfig


class SocialAuthProvider(ABC):
    def __init__(self, config: SocialProviderConfig) -> None:
        self.config = config

    @abstractmethod
    async def get_authorization_url(self, state: str) -> str:
        """Return the URL to redirect the user to for authorization."""

    @abstractmethod
    async def exchange_code_for_tokens(self, code: str) -> dict:
        """Exchange authorization code for provider tokens. Returns raw token response."""

    @abstractmethod
    async def get_user_info(self, access_token: str) -> dict:
        """Fetch user profile from provider. Returns dict with at least: id, email, username."""
