from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from fastauth.core.deps import (
    get_current_user,
    require_self_or_permission,
    require_user_create,
    require_user_delete,
    require_user_read,
    require_user_update,
)
from fastauth.crud.user import (
    activate_user,
    create_user,
    deactivate_user,
    delete_user,
    get_user_by_email,
    get_user_by_id,
    get_user_count,
    get_users,
    search_users,
    suspend_user,
    update_user,
    update_user_password,
)
from fastauth.db.session import get_session
from fastauth.models import (
    User,
    UserCreate,
    UserResponse,
    UserStatus,
    UserUpdate,
)

router = APIRouter()


@router.post(
    "/", response_model=UserResponse, dependencies=[Depends(require_user_create)]
)
async def create_user_endpoint(
    user_create: UserCreate,
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """Create a new user."""
    # Check if user already exists
    existing_user = await get_user_by_email(session, user_create.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    user = await create_user(session, user_create)
    return UserResponse.model_validate(user)


@router.get(
    "/", response_model=list[UserResponse], dependencies=[Depends(require_user_read)]
)
async def get_users_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: UserStatus | None = Query(None, alias="status"),
    is_active: bool | None = None,
    is_superuser: bool | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[UserResponse]:
    """Get all users with optional filtering."""
    users = await get_users(
        session,
        skip=skip,
        limit=limit,
        status=status_filter,
        is_active=is_active,
        is_superuser=is_superuser,
    )
    return [UserResponse.model_validate(user) for user in users]


@router.get(
    "/search",
    response_model=list[UserResponse],
    dependencies=[Depends(require_user_read)],
)
async def search_users_endpoint(
    q: str = Query(..., min_length=1, description="Search query"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
) -> list[UserResponse]:
    """Search users by email, first name, or last name."""
    users = await search_users(session, q, skip=skip, limit=limit)
    return [UserResponse.model_validate(user) for user in users]


@router.get("/count", dependencies=[Depends(require_user_read)])
async def get_user_count_endpoint(
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get total user count."""
    count = await get_user_count(session)
    return {"total_users": count}


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_endpoint(
    user_id: int,
    current_user: User = Depends(require_self_or_permission("user", "read")),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """Get user by ID."""
    user = await get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user_endpoint(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(require_self_or_permission("user", "update")),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """Update user."""
    # Prevent non-superusers from modifying superuser status and certain fields
    if not current_user.is_superuser:
        if user_update.is_superuser is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify superuser status",
            )
        if current_user.id == user_id:
            # Users can't change their own status or active state
            user_update.status = None
            user_update.is_active = None

    user = await update_user(session, user_id, user_update)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return UserResponse.model_validate(user)


@router.put("/{user_id}/password")
async def update_user_password_endpoint(
    user_id: int,
    new_password: str,
    current_user: User = Depends(require_self_or_permission("user", "update")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Update user password."""
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long",
        )

    success = await update_user_password(session, user_id, new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return {"message": "Password updated successfully"}


@router.post("/{user_id}/activate", dependencies=[Depends(require_user_update)])
async def activate_user_endpoint(
    user_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Activate user account."""
    success = await activate_user(session, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return {"message": "User activated successfully"}


@router.post("/{user_id}/deactivate", dependencies=[Depends(require_user_update)])
async def deactivate_user_endpoint(
    user_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Deactivate user account."""
    success = await deactivate_user(session, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return {"message": "User deactivated successfully"}


@router.post("/{user_id}/suspend", dependencies=[Depends(require_user_update)])
async def suspend_user_endpoint(
    user_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Suspend user account."""
    success = await suspend_user(session, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return {"message": "User suspended successfully"}


@router.delete("/{user_id}", dependencies=[Depends(require_user_delete)])
async def delete_user_endpoint(
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Delete user."""
    # Prevent users from deleting themselves
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    success = await delete_user(session, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return {"message": "User deleted successfully"}


@router.get("/me/profile", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Get current user's profile."""
    return UserResponse.model_validate(current_user)


@router.put("/me/profile", response_model=UserResponse)
async def update_my_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """Update current user's profile."""
    # Users can't change their own status, active state, or superuser status
    user_update.status = None
    user_update.is_active = None
    user_update.is_superuser = None
    user_update.role_ids = None

    user = await update_user(session, current_user.id, user_update)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return UserResponse.model_validate(user)


@router.put("/me/password")
async def update_my_password(
    new_password: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Update current user's password."""
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long",
        )

    success = await update_user_password(session, current_user.id, new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return {"message": "Password updated successfully"}
