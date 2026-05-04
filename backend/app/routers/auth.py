from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_active_user
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserResponse
from app.security.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from app.config import settings

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user = await authenticate_user(db, body.email, body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Update last_login_at
    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout")
async def logout() -> dict:
    """
    Stateless JWT logout — the client must discard the token.
    For token invalidation a denylist (Redis) can be layered in later.
    """
    return {"detail": "Logged out successfully"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(body: RefreshRequest) -> TokenResponse:
    payload = verify_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    sub = payload["sub"]
    access_token = create_access_token({"sub": sub})
    new_refresh = create_refresh_token({"sub": sub})
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user=Depends(get_current_active_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
