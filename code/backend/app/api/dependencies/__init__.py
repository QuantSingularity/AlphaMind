"""
FastAPI dependency injection utilities for AlphaMind.
"""

from typing import Any, Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from infrastructure.auth.authentication import get_auth_system

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """
    FastAPI dependency: validate Bearer token and return the authenticated user.

    Raises:
        HTTPException 401: if token is missing, invalid, or expired.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    auth = get_auth_system()
    return auth.get_current_user(credentials)


async def optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """
    FastAPI dependency: return authenticated user, or None if no token provided.
    """
    if credentials is None:
        return {}
    try:
        auth = get_auth_system()
        return auth.get_current_user(credentials)
    except HTTPException:
        return {}
