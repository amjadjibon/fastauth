import secrets

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.auth.deps import CurrentUser, SessionDep
from app.auth.services import social_service
from app.auth.services.session_service import create_session
from app.auth.social.config import get_provider_config
from app.auth.social.providers.github import GitHubProvider
from app.auth.social.providers.gitlab import GitLabProvider
from app.auth.social.providers.google import GoogleProvider

_PROVIDERS = {
    "google": GoogleProvider,
    "github": GitHubProvider,
    "gitlab": GitLabProvider,
}

router = APIRouter(prefix="/auth/social", tags=["social"])


def _get_provider(provider: str, base_url: str):
    config = get_provider_config(provider, base_url)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider '{provider}' not configured",
        )
    cls = _PROVIDERS.get(provider)
    if cls is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown provider '{provider}'")
    return cls(config)


@router.get("/{provider}/authorize")
async def social_authorize(provider: str, request: Request):
    base_url = str(request.base_url).rstrip("/")
    p = _get_provider(provider, base_url)
    state = secrets.token_urlsafe(16)
    url = await p.get_authorization_url(state)
    return RedirectResponse(url)


@router.get("/{provider}/callback")
async def social_callback(provider: str, code: str, request: Request, session: SessionDep):
    base_url = str(request.base_url).rstrip("/")
    p = _get_provider(provider, base_url)

    try:
        tokens = await p.exchange_code_for_tokens(code)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to exchange code") from exc

    access_token = tokens.get("access_token")
    if not access_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No access token from provider")

    try:
        user_info = await p.get_user_info(access_token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to fetch user info") from exc

    provider_user_id = user_info.get("id")
    email = user_info.get("email")
    username = user_info.get("username") or (email or "").split("@")[0]

    if not provider_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provider did not return user ID")

    user = await social_service.handle_social_login(session, provider, provider_user_id, email, username)
    if user is None:
        if not email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provider did not return email")
        user = await social_service.auto_create_user_on_social_login(
            session, provider, provider_user_id, email, username
        )

    await social_service.link_social_account(
        session, user.id, provider, provider_user_id,
        provider_email=email, provider_username=username,
    )

    atk, rtk, _ = await create_session(session, user_id=user.id, ip_address=request.client.host if request.client else None)
    return {"access_token": atk, "refresh_token": rtk, "token_type": "bearer"}


@router.post("/link")
async def link_account(provider: str, code: str, request: Request, current_user: CurrentUser, session: SessionDep):
    base_url = str(request.base_url).rstrip("/")
    p = _get_provider(provider, base_url)
    tokens = await p.exchange_code_for_tokens(code)
    access_token = tokens.get("access_token")
    if not access_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No access token")
    user_info = await p.get_user_info(access_token)
    await social_service.link_social_account(
        session,
        current_user.id,
        provider,
        user_info["id"],
        provider_email=user_info.get("email"),
        provider_username=user_info.get("username"),
    )
    return {"message": f"{provider} account linked"}


@router.get("/linked")
async def list_linked_accounts(current_user: CurrentUser, session: SessionDep):
    from sqlmodel import select
    from app.auth.db_models import UserSocialAccount
    result = await session.exec(
        select(UserSocialAccount).where(UserSocialAccount.user_id == current_user.id)
    )
    return [{"provider": a.provider, "provider_username": a.provider_username} for a in result.all()]


@router.delete("/unlink/{provider}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_account(provider: str, current_user: CurrentUser, session: SessionDep):
    from sqlmodel import select
    from app.auth.db_models import UserSocialAccount
    result = await session.exec(
        select(UserSocialAccount).where(
            UserSocialAccount.user_id == current_user.id,
            UserSocialAccount.provider == provider,
        )
    )
    account = result.first()
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Social account not linked")
    await session.delete(account)
    await session.commit()
