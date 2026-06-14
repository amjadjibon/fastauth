from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import repositories as repo
from app.auth.models import UserSocialAccount
from app.auth.models import User


async def get_oauth_url(provider: str, state: str, redirect_uri: str) -> str:
    """Return the authorization URL for the given social provider."""
    # Implemented per-provider in social/providers/*.py
    # This stub exists to wire the service contract.
    raise NotImplementedError(f"Provider '{provider}' not configured.")


async def exchange_code_for_user_info(provider: str, code: str, redirect_uri: str) -> dict | None:
    """Exchange authorization code for provider user info."""
    raise NotImplementedError(f"Provider '{provider}' not configured.")


async def link_social_account(
    session: AsyncSession,
    user_id: str,
    provider: str,
    provider_user_id: str,
    provider_email: str | None = None,
    provider_username: str | None = None,
    access_token_encrypted: str | None = None,
    refresh_token_encrypted: str | None = None,
) -> UserSocialAccount:
    existing = await _find_social_account(session, provider, provider_user_id)
    if existing:
        existing.user_id = user_id
        existing.provider_email = provider_email
        existing.provider_username = provider_username
        existing.access_token_encrypted = access_token_encrypted
        existing.refresh_token_encrypted = refresh_token_encrypted
        existing.updated_at = datetime.now(UTC)
        session.add(existing)
        await session.commit()
        await session.refresh(existing)
        return existing

    account = UserSocialAccount(
        user_id=user_id,
        provider=provider,
        provider_user_id=provider_user_id,
        provider_email=provider_email,
        provider_username=provider_username,
        access_token_encrypted=access_token_encrypted,
        refresh_token_encrypted=refresh_token_encrypted,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return account


async def handle_social_login(
    session: AsyncSession,
    provider: str,
    provider_user_id: str,
    email: str | None,
    username: str | None,
) -> User | None:
    """Find or auto-create a user based on social account."""
    existing = await _find_social_account(session, provider, provider_user_id)
    if existing:
        return await repo.user.find_by_id(session, existing.user_id)

    if email:
        user = await repo.user.find_by_email(session, email)
        if user:
            return user

    return None


async def auto_create_user_on_social_login(
    session: AsyncSession,
    provider: str,
    provider_user_id: str,
    email: str,
    username: str,
    email_verified: bool = True,
) -> User:
    import secrets as _secrets

    random_password = _secrets.token_hex(32)
    # Social-login users are created with email_verified=True by default because
    # the OAuth provider has already vouched for the address.
    # User and social account are committed atomically — a crash between the two
    # inserts would otherwise leave an orphaned user row with no login path.
    user = await repo.user.create_no_commit(session, username=username, email=email, password=random_password, email_verified=email_verified)
    account = UserSocialAccount(
        user_id=user.id,
        provider=provider,
        provider_user_id=provider_user_id,
        provider_email=email,
        provider_username=username,
    )
    session.add(account)
    await session.commit()
    await session.refresh(user)
    return user


async def _find_social_account(
    session: AsyncSession, provider: str, provider_user_id: str
) -> UserSocialAccount | None:
    result = await session.execute(
        select(UserSocialAccount).where(
            UserSocialAccount.provider == provider,
            UserSocialAccount.provider_user_id == provider_user_id,
        )
    )
    return result.scalar_one_or_none()
