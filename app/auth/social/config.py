from dataclasses import dataclass

from app.core.config import settings


@dataclass
class SocialProviderConfig:
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: list[str]


def get_provider_config(provider: str, base_url: str) -> SocialProviderConfig | None:
    redirect_uri = f"{base_url}/auth/social/{provider}/callback"
    if provider == "google":
        client_id = getattr(settings, "google_client_id", None)
        client_secret = getattr(settings, "google_client_secret", None)
        if not client_id or not client_secret:
            return None
        return SocialProviderConfig(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scopes=["openid", "email", "profile"],
        )
    if provider == "github":
        client_id = getattr(settings, "github_client_id", None)
        client_secret = getattr(settings, "github_client_secret", None)
        if not client_id or not client_secret:
            return None
        return SocialProviderConfig(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scopes=["read:user", "user:email"],
        )
    if provider == "gitlab":
        client_id = getattr(settings, "gitlab_client_id", None)
        client_secret = getattr(settings, "gitlab_client_secret", None)
        if not client_id or not client_secret:
            return None
        return SocialProviderConfig(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scopes=["read_user", "email"],
        )
    return None
