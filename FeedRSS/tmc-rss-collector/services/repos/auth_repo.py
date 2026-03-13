"""Auth repository - token blacklist and auth audit log operations."""

import json
import logging
from typing import Optional

from .base import BaseRepository

logger = logging.getLogger(__name__)


class AuthRepository(BaseRepository):
    """Repository for authentication-related database operations."""

    def blacklist_token(self, jti: str, user_id, expires_at) -> None:
        """Add a JWT token ID to the blacklist."""
        query = """
            INSERT INTO token_blacklist (token_jti, user_id, expires_at)
            VALUES (%s, %s, %s)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(jti), str(user_id), expires_at))
            conn.commit()

    def is_token_blacklisted(self, jti: str) -> bool:
        """Check if a JWT token ID is blacklisted."""
        query = "SELECT 1 FROM token_blacklist WHERE token_jti = %s"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(jti),))
            return cursor.fetchone() is not None

    def cleanup_expired_blacklist(self) -> int:
        """Remove expired tokens from blacklist. Returns count deleted."""
        query = "DELETE FROM token_blacklist WHERE expires_at < GETUTCDATE()"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            deleted = cursor.rowcount
            conn.commit()
            return deleted

    def log_auth_event(self, user_id, email: str, action: str,
                       ip_address: Optional[str] = None,
                       user_agent: Optional[str] = None,
                       metadata: Optional[dict] = None) -> None:
        """Insert an auth audit log entry."""
        query = """
            INSERT INTO auth_audit_log
            (user_id, email, action, ip_address, user_agent, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (
                str(user_id) if user_id else None,
                str(email),
                str(action),
                str(ip_address) if ip_address else None,
                str(user_agent) if user_agent else None,
                metadata_json,
            ))
            conn.commit()
