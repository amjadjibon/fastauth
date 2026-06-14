from fastapi import APIRouter, HTTPException, Query, status

from app.admin.dashboard import get_dashboard_metrics
from app.admin.models import (
    DashboardMetrics,
    OAuthClientCreateRequest,
    OAuthClientResponse,
    PaginatedUsersResponse,
    UpdateUserRequest,
    UserListResponse,
)
from app.admin.services.user_management import (
    force_password_reset,
    get_user_detail,
    list_users,
    lock_user,
    unlock_user,
)
from app.auth import repositories as repo
from app.auth.deps import SessionDep
from app.auth.models import User
from app.auth.rbac.dependencies import RequireRoles

router = APIRouter(prefix="/admin", tags=["admin"])

_RequireAdmin = RequireRoles(["admin"])


@router.get("/dashboard", response_model=DashboardMetrics, dependencies=[_RequireAdmin])
async def dashboard(session: SessionDep):
    return await get_dashboard_metrics(session)


@router.get("/users", response_model=PaginatedUsersResponse, dependencies=[_RequireAdmin])
async def list_all_users(
    session: SessionDep,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, le=200),
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
):
    users, total = await list_users(session, page=page, limit=limit, search=search, status=status)
    return PaginatedUsersResponse(
        users=[
            UserListResponse(id=u.id, username=u.username, email=u.email, created_at=u.created_at)
            for u in users
        ],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/users/{user_id}", dependencies=[_RequireAdmin])
async def get_user(user_id: str, session: SessionDep):
    detail = await get_user_detail(session, user_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return detail


@router.patch("/users/{user_id}", dependencies=[_RequireAdmin])
async def update_user(user_id: str, body: UpdateUserRequest, session: SessionDep):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if body.email is not None:
        user.email = body.email
    if body.username is not None:
        user.username = body.username
    await repo.user.update(session, user)
    return {"message": "User updated"}


@router.delete(
    "/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[_RequireAdmin]
)
async def delete_user(user_id: str, session: SessionDep):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await repo.user.delete(session, user)


@router.post("/users/{user_id}/lock", dependencies=[_RequireAdmin])
async def lock_user_account(user_id: str):
    await lock_user(user_id)
    return {"message": "User locked"}


@router.post("/users/{user_id}/unlock", dependencies=[_RequireAdmin])
async def unlock_user_account(user_id: str):
    await unlock_user(user_id)
    return {"message": "User unlocked"}


@router.post("/users/{user_id}/force-password-reset", dependencies=[_RequireAdmin])
async def admin_force_password_reset(user_id: str, session: SessionDep):
    ok = await force_password_reset(session, user_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"message": "Password reset initiated"}


@router.post("/users/bulk-lock", dependencies=[_RequireAdmin])
async def bulk_lock_users(user_ids: list[str]):
    for uid in user_ids:
        await lock_user(uid)
    return {"message": f"{len(user_ids)} users locked"}


@router.post(
    "/users/bulk-delete", status_code=status.HTTP_204_NO_CONTENT, dependencies=[_RequireAdmin]
)
async def bulk_delete_users(user_ids: list[str], session: SessionDep):
    for uid in user_ids:
        user = await session.get(User, uid)
        if user:
            await repo.user.delete(session, user)


# ---------------------------------------------------------------------------
# OAuth client management
# ---------------------------------------------------------------------------


@router.post("/oauth/clients", dependencies=[_RequireAdmin])
async def create_oauth_client(body: OAuthClientCreateRequest, session: SessionDep):
    import secrets

    from app.auth.models import OAuthClient
    from app.core.security import hash_password as _hash

    client_id = secrets.token_hex(16)
    raw_secret = secrets.token_hex(32)
    secret_hash = _hash(raw_secret)

    client = OAuthClient(
        id=client_id,
        name=body.name,
        client_secret_hash=secret_hash,
        redirect_uris=" ".join(body.redirect_uris),
        scopes=" ".join(body.scopes),
        is_confidential=body.is_confidential,
        is_active=True,
    )
    session.add(client)
    await session.commit()
    return {"client_id": client_id, "client_secret": raw_secret}


@router.get(
    "/oauth/clients", response_model=list[OAuthClientResponse], dependencies=[_RequireAdmin]
)
async def list_oauth_clients(session: SessionDep):
    from sqlalchemy import select

    from app.auth.models import OAuthClient

    result = await session.execute(select(OAuthClient))
    return list(result.scalars().all())


@router.get(
    "/oauth/clients/{client_id}", response_model=OAuthClientResponse, dependencies=[_RequireAdmin]
)
async def get_oauth_client(client_id: str, session: SessionDep):
    from app.auth.models import OAuthClient

    client = await session.get(OAuthClient, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


@router.delete(
    "/oauth/clients/{client_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_RequireAdmin],
)
async def revoke_oauth_client(client_id: str, session: SessionDep):
    from app.auth.models import OAuthClient

    client = await session.get(OAuthClient, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    client.is_active = False
    session.add(client)
    await session.commit()
