"""
FastAPI dependencies for authentication and common patterns.
"""

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthenticationError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.repository import UserRepository


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extract and validate the current user from the Authorization header.

    Expected format: "Bearer <token>"
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Missing or invalid authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    user_id = decode_access_token(token)
    if not user_id:
        raise AuthenticationError("Invalid or expired token")

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise AuthenticationError("User not found or deactivated")

    return user
