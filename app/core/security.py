"""Security and cryptography utilities."""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
import bcrypt

from app.config.settings import get_settings

settings = get_settings()
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days
RESET_TOKEN_EXPIRE_HOURS = 1


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash using bcrypt directly."""
    if len(plain_password.encode('utf-8')) > 72:
        plain_password = plain_password[:72]
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8') if isinstance(hashed_password, str) else hashed_password,
    )


def get_password_hash(password: str) -> str:
    """Hash password using bcrypt directly (truncates to 72 bytes)."""
    if len(password.encode('utf-8')) > 72:
        password = password[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def hash_password(password: str) -> str:
    """Hash password (alias for compatibility)."""
    return get_password_hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify JWT token and return payload."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify JWT token (alias for verify_token)."""
    return verify_token(token)


def create_reset_token(email: str) -> str:
    """Create password reset token (valid for 1 hour)."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(hours=RESET_TOKEN_EXPIRE_HOURS)
    to_encode = {"sub": email, "exp": expire, "type": "reset", "iat": now}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_reset_token(token: str) -> Optional[str]:
    """Verify reset token and return email."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "reset":
            return None
        return payload.get("sub")
    except JWTError:
        return None
