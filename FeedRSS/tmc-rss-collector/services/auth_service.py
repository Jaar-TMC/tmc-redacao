"""
Authentication service: JWT token management and password hashing.
Thread-safe, uses config singleton for JWT settings.
"""
import bcrypt
import jwt
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from services.config import get_config

logger = logging.getLogger(__name__)

# ========================================
# PASSWORD HASHING (bcrypt, cost 12)
# ========================================


def hash_password(password: str) -> str:
    """Hash password with bcrypt cost factor 12."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False


# ========================================
# JWT TOKEN MANAGEMENT
# ========================================


def create_access_token(user_id: str, email: str, role: str, name: str) -> str:
    """Create JWT access token.

    Payload: sub, email, role, name, jti, iat, exp
    Algorithm: HS256
    Expiry: from config jwt_access_token_minutes (default 60)
    """
    config = get_config()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "name": name,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=config.jwt_access_token_minutes),
        "type": "access"
    }
    return jwt.encode(payload, config.jwt_secret_key, algorithm="HS256")


def create_refresh_token(user_id: str, remember_me: bool = False, token_family: str = None) -> str:
    """Create JWT refresh token.

    Expiry: config jwt_refresh_token_days (7 default, 30 if remember_me)
    token_family: Links tokens in a rotation chain. Auto-generated on login,
                  preserved across rotations for reuse detection.
    """
    config = get_config()
    now = datetime.now(timezone.utc)
    days = config.jwt_refresh_token_days * 4 if remember_me else config.jwt_refresh_token_days
    payload = {
        "sub": user_id,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(days=days),
        "type": "refresh",
        "family": token_family or str(uuid.uuid4()),
    }
    return jwt.encode(payload, config.jwt_secret_key, algorithm="HS256")


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate JWT token. Returns payload dict or None."""
    config = get_config()
    try:
        payload = jwt.decode(token, config.jwt_secret_key, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        logger.debug("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid token: {e}")
        return None


def is_account_locked(locked_until: Optional[datetime]) -> bool:
    """Check if account is currently locked."""
    if not locked_until:
        return False
    now = datetime.now(timezone.utc)
    # pymssql returns tz-naive datetimes from SQL Server; treat as UTC
    if locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    return now < locked_until


LOCKOUT_THRESHOLD = 5
LOCKOUT_DURATION_MINUTES = 15
