from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from fastauth.core.deps import get_current_user
from fastauth.core.security import (
    create_access_token,
    create_refresh_token,
    create_token_data,
    verify_token,
)
from fastauth.crud.rbac import get_user_permissions, get_user_roles
from fastauth.crud.user import authenticate_user, create_user, get_user_by_email
from fastauth.db.session import get_session
from fastauth.models import (
    Token,
    TokenRefresh,
    User,
    UserCreate,
    UserLogin,
    UserResponse,
)

router = APIRouter()


async def create_user_tokens(session: AsyncSession, user: User) -> Token:
    """Create access and refresh tokens with user roles and permissions."""
    # Get user roles and permissions
    user_roles = await get_user_roles(session, user.id)
    user_permissions = await get_user_permissions(session, user.id)

    # Format data for token
    token_data = create_token_data(user.id, user.email, user.is_superuser)
    role_names = [role.name for role in user_roles]
    permission_data = [
        {"resource": perm.resource, "action": perm.action} for perm in user_permissions
    ]

    # Create tokens
    access_token = create_access_token(
        data=token_data, roles=role_names, permissions=permission_data
    )
    refresh_token = create_refresh_token(data=token_data)

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/register", response_model=UserResponse)
async def register(
    user_create: UserCreate,
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """Register a new user."""
    # Check if user already exists
    existing_user = await get_user_by_email(session, user_create.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Create user
    user = await create_user(session, user_create)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=Token)
async def login(
    user_login: UserLogin,
    session: AsyncSession = Depends(get_session),
) -> Token:
    """Authenticate user and return tokens with roles and permissions."""
    user = await authenticate_user(session, user_login.email, user_login.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return await create_user_tokens(session, user)


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_refresh: TokenRefresh,
    session: AsyncSession = Depends(get_session),
) -> Token:
    """Refresh access token using refresh token with updated roles and permissions."""
    payload = verify_token(token_refresh.refresh_token, "refresh")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get current user data
    from ..crud.user import get_user_by_id

    user = await get_user_by_id(session, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create new tokens with fresh user data
    return await create_user_tokens(session, user)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user=Depends(get_current_user),
) -> UserResponse:
    """Get current user information."""
    return UserResponse.model_validate(current_user.user)
