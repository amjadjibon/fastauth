from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.deps import CurrentUser, SessionDep
from app.auth.oauth.discovery import get_oidc_discovery
from app.auth.oauth.jwks import get_jwks
from app.auth.oauth.models import AuthorizationCodeRequest, OAuthTokenResponse, TokenRequest
from app.auth.oauth.pkce import verify_code_challenge
from app.auth.services import oauth_service
from app.core.ratelimit import RateLimiter

router = APIRouter(tags=["oauth2"])


@router.get("/.well-known/openid-configuration")
async def oidc_discovery(request: Request):
    base_url = str(request.base_url).rstrip("/")
    return get_oidc_discovery(base_url)


@router.get("/.well-known/jwks.json")
async def jwks():
    return get_jwks()


@router.post(
    "/oauth/authorize",
    dependencies=[Depends(RateLimiter(times=20, seconds=60))],
)
async def authorize(
    body: AuthorizationCodeRequest,
    session: SessionDep,
    current_user: CurrentUser,
):
    if body.response_type != "code":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Only 'code' response_type is supported"
        )

    code = await oauth_service.authorize_client(
        session,
        client_id=body.client_id,
        redirect_uri=body.redirect_uri,
        user_id=current_user.id,
        scopes=body.scope,
        code_challenge=body.code_challenge,
        code_challenge_method=body.code_challenge_method,
        nonce=body.nonce,
    )
    if code is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client or redirect_uri"
        )

    return {"code": code, "state": body.state}


@router.post(
    "/oauth/token",
    response_model=OAuthTokenResponse,
    dependencies=[Depends(RateLimiter(times=20, seconds=60))],
)
async def token(
    body: TokenRequest,
    session: SessionDep,
):
    if body.grant_type != "authorization_code":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported grant_type"
        )
    if not body.code or not body.redirect_uri or not body.client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing required fields"
        )

    # If PKCE is used, verify the code challenge before exchanging
    from sqlmodel import select

    from app.auth.db_models import OAuthAuthorizationCode

    result = await session.exec(
        select(OAuthAuthorizationCode).where(OAuthAuthorizationCode.code == body.code)
    )
    pending_code = result.first()
    if pending_code and pending_code.code_challenge:
        if not body.code_verifier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="code_verifier required"
            )
        if not verify_code_challenge(
            body.code_verifier,
            pending_code.code_challenge,
            pending_code.code_challenge_method or "S256",
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code_verifier"
            )

    result = await oauth_service.exchange_code_for_token(
        session,
        code=body.code,
        client_id=body.client_id,
        redirect_uri=body.redirect_uri,
        code_verifier=body.code_verifier,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid authorization code"
        )

    return OAuthTokenResponse(**result)


@router.get("/oauth/userinfo")
async def userinfo(current_user: CurrentUser):
    return {
        "sub": current_user.id,
        "email": current_user.email,
        "preferred_username": current_user.username,
    }
