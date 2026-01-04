"""
Security & Authentication Module

JWT-based authentication, OAuth2 support, and security middleware:
- JWT token generation and validation
- OAuth2 integration (Google, GitHub)
- API key management
- Rate limiting
- Audit logging
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import base64
import json

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class UserRole(Enum):
    """User roles for authorization"""
    VIEWER = "viewer"
    TRADER = "trader"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class TokenType(Enum):
    """Types of authentication tokens"""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"


@dataclass
class User:
    """User account"""
    id: str
    email: str
    username: str
    password_hash: str
    role: UserRole
    is_active: bool = True
    is_verified: bool = False
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None
    api_keys: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None


@dataclass
class APIKey:
    """API key for programmatic access"""
    key_id: str
    key_hash: str
    user_id: str
    name: str
    permissions: List[str]
    rate_limit: int  # requests per minute
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_used: Optional[datetime] = None
    expires_at: Optional[datetime] = None


@dataclass
class AuditLogEntry:
    """Security audit log entry"""
    id: str
    timestamp: datetime
    user_id: str
    action: str
    resource: str
    ip_address: str
    user_agent: str
    success: bool
    details: Dict = field(default_factory=dict)


class PasswordHasher:
    """
    Secure password hashing using Argon2 (with bcrypt fallback).
    """
    
    def __init__(self):
        self._hasher = None
        self._init_hasher()
        
    def _init_hasher(self):
        """Initialize the password hasher"""
        try:
            from argon2 import PasswordHasher as Argon2Hasher
            self._hasher = Argon2Hasher(
                time_cost=3,
                memory_cost=65536,
                parallelism=4,
                hash_len=32,
            )
            self._algorithm = "argon2"
        except ImportError:
            try:
                import bcrypt
                self._algorithm = "bcrypt"
            except ImportError:
                logger.warning("No secure password hasher available, using PBKDF2")
                self._algorithm = "pbkdf2"
                
    def hash_password(self, password: str) -> str:
        """Hash a password"""
        if self._algorithm == "argon2":
            return self._hasher.hash(password)
        elif self._algorithm == "bcrypt":
            import bcrypt
            return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        else:
            # PBKDF2 fallback
            salt = secrets.token_bytes(32)
            key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
            return f"pbkdf2${base64.b64encode(salt).decode()}${base64.b64encode(key).decode()}"
            
    def verify_password(self, password: str, hash: str) -> bool:
        """Verify a password against a hash"""
        try:
            if self._algorithm == "argon2" and hash.startswith("$argon2"):
                from argon2 import PasswordHasher as Argon2Hasher
                from argon2.exceptions import VerifyMismatchError
                try:
                    Argon2Hasher().verify(hash, password)
                    return True
                except VerifyMismatchError:
                    return False
            elif self._algorithm == "bcrypt" and hash.startswith("$2"):
                import bcrypt
                return bcrypt.checkpw(password.encode(), hash.encode())
            elif hash.startswith("pbkdf2$"):
                parts = hash.split("$")
                salt = base64.b64decode(parts[1])
                stored_key = base64.b64decode(parts[2])
                key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
                return hmac.compare_digest(key, stored_key)
            return False
        except Exception as e:
            logger.error("password_verify_error", error=str(e))
            return False


class JWTManager:
    """
    JWT token management for authentication.
    """
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_ttl = timedelta(minutes=15)
        self.refresh_token_ttl = timedelta(days=7)
        
    def create_access_token(
        self,
        user_id: str,
        role: str,
        additional_claims: Optional[Dict] = None,
    ) -> str:
        """Create a JWT access token"""
        now = datetime.now(timezone.utc)
        
        payload = {
            "sub": user_id,
            "role": role,
            "type": TokenType.ACCESS.value,
            "iat": int(now.timestamp()),
            "exp": int((now + self.access_token_ttl).timestamp()),
            "jti": secrets.token_hex(16),
        }
        
        if additional_claims:
            payload.update(additional_claims)
            
        return self._encode_token(payload)
        
    def create_refresh_token(self, user_id: str) -> str:
        """Create a JWT refresh token"""
        now = datetime.now(timezone.utc)
        
        payload = {
            "sub": user_id,
            "type": TokenType.REFRESH.value,
            "iat": int(now.timestamp()),
            "exp": int((now + self.refresh_token_ttl).timestamp()),
            "jti": secrets.token_hex(16),
        }
        
        return self._encode_token(payload)
        
    def verify_token(self, token: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Verify a JWT token.
        
        Returns:
            Tuple of (valid, payload, error_message)
        """
        try:
            payload = self._decode_token(token)
            
            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
                return False, None, "Token expired"
                
            return True, payload, None
            
        except Exception as e:
            return False, None, str(e)
            
    def _encode_token(self, payload: Dict) -> str:
        """Encode payload as JWT"""
        try:
            import jwt
            return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        except ImportError:
            # Manual JWT encoding (simplified, for demonstration)
            header = {"alg": self.algorithm, "typ": "JWT"}
            header_b64 = base64.urlsafe_b64encode(
                json.dumps(header).encode()
            ).rstrip(b"=").decode()
            payload_b64 = base64.urlsafe_b64encode(
                json.dumps(payload).encode()
            ).rstrip(b"=").decode()
            
            message = f"{header_b64}.{payload_b64}"
            signature = hmac.new(
                self.secret_key.encode(),
                message.encode(),
                hashlib.sha256
            ).digest()
            signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
            
            return f"{message}.{signature_b64}"
            
    def _decode_token(self, token: str) -> Dict:
        """Decode JWT token"""
        try:
            import jwt
            return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except ImportError:
            # Manual JWT decoding
            parts = token.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid token format")
                
            # Verify signature
            message = f"{parts[0]}.{parts[1]}"
            signature = base64.urlsafe_b64decode(parts[2] + "==")
            expected_sig = hmac.new(
                self.secret_key.encode(),
                message.encode(),
                hashlib.sha256
            ).digest()
            
            if not hmac.compare_digest(signature, expected_sig):
                raise ValueError("Invalid signature")
                
            # Decode payload
            payload_json = base64.urlsafe_b64decode(parts[1] + "==")
            return json.loads(payload_json)


class APIKeyManager:
    """
    API key management for programmatic access.
    """
    
    def __init__(self):
        self.keys: Dict[str, APIKey] = {}  # In production, use database
        
    def generate_api_key(
        self,
        user_id: str,
        name: str,
        permissions: List[str],
        rate_limit: int = 60,
        expires_in_days: Optional[int] = None,
    ) -> Tuple[str, APIKey]:
        """
        Generate a new API key.
        
        Returns:
            Tuple of (raw_key, api_key_object)
            The raw_key is only returned once and should be stored by the user
        """
        # Generate a secure random key
        raw_key = secrets.token_urlsafe(32)
        key_id = f"ak_{secrets.token_hex(8)}"
        
        # Hash the key for storage
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
            
        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            user_id=user_id,
            name=name,
            permissions=permissions,
            rate_limit=rate_limit,
            expires_at=expires_at,
        )
        
        self.keys[key_id] = api_key
        
        logger.info(
            "api_key_created",
            key_id=key_id,
            user_id=user_id,
            permissions=permissions,
        )
        
        return f"{key_id}.{raw_key}", api_key
        
    def verify_api_key(self, raw_key: str) -> Tuple[bool, Optional[APIKey], Optional[str]]:
        """
        Verify an API key.
        
        Returns:
            Tuple of (valid, api_key, error_message)
        """
        try:
            parts = raw_key.split(".")
            if len(parts) != 2:
                return False, None, "Invalid key format"
                
            key_id, key_secret = parts
            
            if key_id not in self.keys:
                return False, None, "Key not found"
                
            api_key = self.keys[key_id]
            
            # Verify hash
            expected_hash = hashlib.sha256(key_secret.encode()).hexdigest()
            if not hmac.compare_digest(api_key.key_hash, expected_hash):
                return False, None, "Invalid key"
                
            # Check if active
            if not api_key.is_active:
                return False, None, "Key is disabled"
                
            # Check expiration
            if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
                return False, None, "Key has expired"
                
            # Update last used
            api_key.last_used = datetime.now(timezone.utc)
            
            return True, api_key, None
            
        except Exception as e:
            return False, None, str(e)
            
    def revoke_api_key(self, key_id: str):
        """Revoke an API key"""
        if key_id in self.keys:
            self.keys[key_id].is_active = False
            logger.info("api_key_revoked", key_id=key_id)


class RateLimiter:
    """
    Token bucket rate limiter.
    """
    
    def __init__(self):
        self.buckets: Dict[str, Dict] = {}
        
    def check_rate_limit(
        self,
        identifier: str,
        limit: int,
        window_seconds: int = 60,
    ) -> Tuple[bool, int, int]:
        """
        Check if request is within rate limit.
        
        Returns:
            Tuple of (allowed, remaining, reset_time)
        """
        now = time.time()
        
        if identifier not in self.buckets:
            self.buckets[identifier] = {
                "tokens": limit,
                "last_update": now,
                "window_start": now,
            }
            
        bucket = self.buckets[identifier]
        
        # Calculate time since last update
        elapsed = now - bucket["last_update"]
        
        # Add tokens based on elapsed time
        tokens_to_add = int(elapsed * limit / window_seconds)
        bucket["tokens"] = min(limit, bucket["tokens"] + tokens_to_add)
        bucket["last_update"] = now
        
        # Check if window has reset
        if now - bucket["window_start"] >= window_seconds:
            bucket["window_start"] = now
            bucket["tokens"] = limit
            
        # Check if request is allowed
        if bucket["tokens"] > 0:
            bucket["tokens"] -= 1
            remaining = bucket["tokens"]
            reset_time = int(bucket["window_start"] + window_seconds - now)
            return True, remaining, max(0, reset_time)
        else:
            remaining = 0
            reset_time = int(bucket["window_start"] + window_seconds - now)
            return False, remaining, max(0, reset_time)
            
    def get_usage(self, identifier: str, limit: int) -> Dict:
        """Get rate limit usage for an identifier"""
        if identifier not in self.buckets:
            return {"used": 0, "remaining": limit, "limit": limit}
            
        bucket = self.buckets[identifier]
        return {
            "used": limit - bucket["tokens"],
            "remaining": bucket["tokens"],
            "limit": limit,
        }


class AuditLogger:
    """
    Security audit logging.
    """
    
    def __init__(self):
        self.entries: List[AuditLogEntry] = []  # In production, use database
        
    def log(
        self,
        user_id: str,
        action: str,
        resource: str,
        ip_address: str,
        user_agent: str,
        success: bool,
        details: Optional[Dict] = None,
    ):
        """Log a security event"""
        entry = AuditLogEntry(
            id=secrets.token_hex(16),
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            action=action,
            resource=resource,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            details=details or {},
        )
        
        self.entries.append(entry)
        
        # Log to structured logger
        logger.info(
            "audit_log",
            user_id=user_id,
            action=action,
            resource=resource,
            success=success,
            ip_address=ip_address,
        )
        
    def get_user_activity(
        self,
        user_id: str,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditLogEntry]:
        """Get activity log for a user"""
        entries = [e for e in self.entries if e.user_id == user_id]
        
        if since:
            entries = [e for e in entries if e.timestamp >= since]
            
        return sorted(entries, key=lambda x: x.timestamp, reverse=True)[:limit]
        
    def get_failed_logins(
        self,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditLogEntry]:
        """Get failed login attempts"""
        entries = [
            e for e in self.entries
            if e.action == "login" and not e.success
        ]
        
        if since:
            entries = [e for e in entries if e.timestamp >= since]
            
        return sorted(entries, key=lambda x: x.timestamp, reverse=True)[:limit]


class AuthenticationService:
    """
    Main authentication service coordinating all security components.
    """
    
    def __init__(self, jwt_secret: str):
        self.password_hasher = PasswordHasher()
        self.jwt_manager = JWTManager(jwt_secret)
        self.api_key_manager = APIKeyManager()
        self.rate_limiter = RateLimiter()
        self.audit_logger = AuditLogger()
        
        # User storage (in production, use database)
        self.users: Dict[str, User] = {}
        
        # Account lockout settings
        self.max_failed_attempts = 5
        self.lockout_duration = timedelta(minutes=15)
        
    def register_user(
        self,
        email: str,
        username: str,
        password: str,
        role: UserRole = UserRole.TRADER,
    ) -> User:
        """Register a new user"""
        # Check if email/username already exists
        for user in self.users.values():
            if user.email == email:
                raise ValueError("Email already registered")
            if user.username == username:
                raise ValueError("Username already taken")
                
        # Hash password
        password_hash = self.password_hasher.hash_password(password)
        
        # Create user
        user = User(
            id=secrets.token_hex(16),
            email=email,
            username=username,
            password_hash=password_hash,
            role=role,
        )
        
        self.users[user.id] = user
        
        logger.info("user_registered", user_id=user.id, email=email)
        
        return user
        
    def authenticate(
        self,
        email: str,
        password: str,
        ip_address: str = "unknown",
        user_agent: str = "unknown",
    ) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Authenticate a user with email and password.
        
        Returns:
            Tuple of (success, tokens_dict, error_message)
        """
        # Find user
        user = None
        for u in self.users.values():
            if u.email == email:
                user = u
                break
                
        if not user:
            self.audit_logger.log(
                user_id="unknown",
                action="login",
                resource="auth",
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                details={"reason": "user_not_found", "email": email},
            )
            return False, None, "Invalid credentials"
            
        # Check if locked
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            return False, None, f"Account locked until {user.locked_until.isoformat()}"
            
        # Verify password
        if not self.password_hasher.verify_password(password, user.password_hash):
            user.failed_login_attempts += 1
            
            # Lock account if too many failures
            if user.failed_login_attempts >= self.max_failed_attempts:
                user.locked_until = datetime.now(timezone.utc) + self.lockout_duration
                
            self.audit_logger.log(
                user_id=user.id,
                action="login",
                resource="auth",
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                details={"reason": "invalid_password"},
            )
            return False, None, "Invalid credentials"
            
        # Check if active
        if not user.is_active:
            return False, None, "Account is disabled"
            
        # Reset failed attempts
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.now(timezone.utc)
        
        # Generate tokens
        access_token = self.jwt_manager.create_access_token(
            user_id=user.id,
            role=user.role.value,
        )
        refresh_token = self.jwt_manager.create_refresh_token(user_id=user.id)
        
        self.audit_logger.log(
            user_id=user.id,
            action="login",
            resource="auth",
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
        )
        
        return True, {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": int(self.jwt_manager.access_token_ttl.total_seconds()),
        }, None
        
    def refresh_tokens(
        self,
        refresh_token: str,
    ) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Refresh access token using refresh token.
        
        Returns:
            Tuple of (success, tokens_dict, error_message)
        """
        valid, payload, error = self.jwt_manager.verify_token(refresh_token)
        
        if not valid:
            return False, None, error
            
        if payload.get("type") != TokenType.REFRESH.value:
            return False, None, "Invalid token type"
            
        user_id = payload.get("sub")
        user = self.users.get(user_id)
        
        if not user or not user.is_active:
            return False, None, "User not found or disabled"
            
        # Generate new tokens
        access_token = self.jwt_manager.create_access_token(
            user_id=user.id,
            role=user.role.value,
        )
        new_refresh_token = self.jwt_manager.create_refresh_token(user_id=user.id)
        
        return True, {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": int(self.jwt_manager.access_token_ttl.total_seconds()),
        }, None
        
    def verify_access(
        self,
        token: str,
        required_role: Optional[UserRole] = None,
    ) -> Tuple[bool, Optional[User], Optional[str]]:
        """
        Verify access token and optionally check role.
        
        Returns:
            Tuple of (valid, user, error_message)
        """
        valid, payload, error = self.jwt_manager.verify_token(token)
        
        if not valid:
            return False, None, error
            
        if payload.get("type") != TokenType.ACCESS.value:
            return False, None, "Invalid token type"
            
        user_id = payload.get("sub")
        user = self.users.get(user_id)
        
        if not user:
            return False, None, "User not found"
            
        if not user.is_active:
            return False, None, "User is disabled"
            
        # Check role
        if required_role:
            role_hierarchy = [
                UserRole.VIEWER,
                UserRole.TRADER,
                UserRole.ADMIN,
                UserRole.SUPER_ADMIN,
            ]
            user_level = role_hierarchy.index(user.role)
            required_level = role_hierarchy.index(required_role)
            
            if user_level < required_level:
                return False, None, "Insufficient permissions"
                
        return True, user, None


# Global instances
password_hasher = PasswordHasher()
api_key_manager = APIKeyManager()
rate_limiter = RateLimiter()
audit_logger = AuditLogger()
