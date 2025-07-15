from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from fastauth.core.deps import get_current_user
from fastauth.core.security import create_access_token, create_refresh_token, verify_token
from fastauth.crud.user import authenticate_user, create_user, get_user_by_email
from fastauth.db.session import get_session
from fastauth.models.user import Token, TokenRefresh, User, UserCreate, UserLogin, UserResponse

router = APIRouter()


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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user = await create_user(session, user_create)
    return UserResponse.from_orm(user)


@router.post("/login", response_model=Token)
async def login(
    user_login: UserLogin,
    session: AsyncSession = Depends(get_session),
) -> Token:
    """Authenticate user and return tokens."""
    user = await authenticate_user(session, user_login.email, user_login.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_refresh: TokenRefresh,
    session: AsyncSession = Depends(get_session),
) -> Token:
    """Refresh access token using refresh token."""
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
    
    # Create new tokens
    access_token = create_access_token(data={"sub": user_id})
    refresh_token = create_refresh_token(data={"sub": user_id})
    
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Get current user information."""
    return UserResponse.from_orm(current_user)