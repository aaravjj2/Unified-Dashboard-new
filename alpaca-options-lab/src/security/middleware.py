"""
FastAPI Security Middleware

Authentication and authorization middleware for FastAPI routes.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, List, Optional
from functools import wraps

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, APIKeyHeader
from pydantic import BaseModel

from src.security import (
    AuthenticationService,
    UserRole,
    rate_limiter,
    audit_logger,
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class TokenData(BaseModel):
    """Extracted token data"""
    user_id: str
    role: str
    email: Optional[str] = None


def get_auth_service() -> AuthenticationService:
    """Get the authentication service (dependency injection)"""
    # In production, this would be configured with actual secrets
    import os
    jwt_secret = os.environ.get("JWT_SECRET", "dev-secret-change-in-production")
    return AuthenticationService(jwt_secret)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Depends(api_key_header),
    auth_service: AuthenticationService = Depends(get_auth_service),
) -> TokenData:
    """
    Dependency to extract and validate the current user from request.
    Supports both Bearer token and API key authentication.
    """
    # Try Bearer token first
    if credentials:
        valid, user, error = auth_service.verify_access(credentials.credentials)
        
        if not valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error or "Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return TokenData(
            user_id=user.id,
            role=user.role.value,
            email=user.email,
        )
        
    # Try API key
    if api_key:
        valid, key_obj, error = auth_service.api_key_manager.verify_api_key(api_key)
        
        if not valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error or "Invalid API key",
            )
            
        # Get user associated with API key
        user = auth_service.users.get(key_obj.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
            
        return TokenData(
            user_id=user.id,
            role=user.role.value,
            email=user.email,
        )
        
    # No authentication provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Depends(api_key_header),
    auth_service: AuthenticationService = Depends(get_auth_service),
) -> Optional[TokenData]:
    """
    Optional user extraction - returns None if not authenticated.
    """
    try:
        return await get_current_user(request, credentials, api_key, auth_service)
    except HTTPException:
        return None


def require_role(required_role: UserRole):
    """
    Dependency factory to require a specific role level.
    """
    async def role_checker(
        current_user: TokenData = Depends(get_current_user),
    ) -> TokenData:
        role_hierarchy = [
            UserRole.VIEWER,
            UserRole.TRADER,
            UserRole.ADMIN,
            UserRole.SUPER_ADMIN,
        ]
        
        user_role = UserRole(current_user.role)
        user_level = role_hierarchy.index(user_role)
        required_level = role_hierarchy.index(required_role)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role.value} role or higher",
            )
            
        return current_user
        
    return role_checker


def require_permissions(permissions: List[str]):
    """
    Dependency factory to require specific permissions.
    (For API key authentication)
    """
    async def permission_checker(
        request: Request,
        api_key: Optional[str] = Depends(api_key_header),
        auth_service: AuthenticationService = Depends(get_auth_service),
    ):
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required for this endpoint",
            )
            
        valid, key_obj, error = auth_service.api_key_manager.verify_api_key(api_key)
        
        if not valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error or "Invalid API key",
            )
            
        # Check permissions
        for perm in permissions:
            if perm not in key_obj.permissions and "*" not in key_obj.permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permission: {perm}",
                )
                
        return key_obj
        
    return permission_checker


class RateLimitMiddleware:
    """
    Rate limiting middleware.
    """
    
    def __init__(
        self,
        default_limit: int = 100,
        window_seconds: int = 60,
    ):
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        
    async def __call__(
        self,
        request: Request,
        call_next: Callable,
    ):
        # Get identifier (IP or user ID)
        identifier = request.client.host if request.client else "unknown"
        
        # Check for authenticated user
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            # Use user ID for rate limiting authenticated requests
            # (This is simplified - in production, decode the token)
            identifier = f"user:{auth_header[7:20]}"
            
        # Check rate limit
        allowed, remaining, reset = rate_limiter.check_rate_limit(
            identifier,
            self.default_limit,
            self.window_seconds,
        )
        
        # Add rate limit headers
        response = await call_next(request) if allowed else None
        
        if response:
            response.headers["X-RateLimit-Limit"] = str(self.default_limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset)
            return response
        else:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(self.default_limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset),
                    "Retry-After": str(reset),
                },
            )


class AuditMiddleware:
    """
    Audit logging middleware.
    """
    
    def __init__(self, log_paths: Optional[List[str]] = None):
        self.log_paths = log_paths or ["/api/"]
        
    async def __call__(
        self,
        request: Request,
        call_next: Callable,
    ):
        # Check if path should be audited
        should_audit = any(
            request.url.path.startswith(p) for p in self.log_paths
        )
        
        if not should_audit:
            return await call_next(request)
            
        start_time = datetime.now(timezone.utc)
        
        # Extract request info
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "unknown")
        
        # Extract user ID if available
        user_id = "anonymous"
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            # In production, decode the token to get user ID
            user_id = "authenticated_user"
            
        try:
            response = await call_next(request)
            
            # Log successful request
            audit_logger.log(
                user_id=user_id,
                action=request.method,
                resource=request.url.path,
                ip_address=ip_address,
                user_agent=user_agent,
                success=response.status_code < 400,
                details={
                    "status_code": response.status_code,
                    "duration_ms": (datetime.now(timezone.utc) - start_time).total_seconds() * 1000,
                },
            )
            
            return response
            
        except Exception as e:
            # Log failed request
            audit_logger.log(
                user_id=user_id,
                action=request.method,
                resource=request.url.path,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                details={
                    "error": str(e),
                    "duration_ms": (datetime.now(timezone.utc) - start_time).total_seconds() * 1000,
                },
            )
            raise


def rate_limit(limit: int = 10, window_seconds: int = 60):
    """
    Decorator for per-endpoint rate limiting.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get identifier
            identifier = f"{func.__name__}:{request.client.host if request.client else 'unknown'}"
            
            allowed, remaining, reset = rate_limiter.check_rate_limit(
                identifier,
                limit,
                window_seconds,
            )
            
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded for this endpoint",
                    headers={"Retry-After": str(reset)},
                )
                
            return await func(request, *args, **kwargs)
            
        return wrapper
    return decorator
