"""User repository - CRUD and auth tracking for users."""

import logging
from typing import List, Optional, Tuple
from uuid import UUID

from models import User, UserCreate, UserUpdate, UserWithPassword
from .base import BaseRepository, _execute

logger = logging.getLogger(__name__)


def _build_update_query(table, updates, where):
    """Build a parameterized UPDATE query from safe column fragments.

    All update fragments are hardcoded column assignments (e.g. "name = %s"),
    never derived from user input. The WHERE clause is also a static string.
    This function exists to centralise dynamic SET-clause assembly for
    partial-update endpoints. pymssql parameterises all values via %s.
    """
    return "UPDATE " + table + " SET " + ", ".join(updates) + " WHERE " + where


class UserRepository(BaseRepository):
    """Repository for user management and login tracking."""

    LOCKOUT_THRESHOLD = 5
    LOCKOUT_MINUTES = 15

    def _row_to_user(self, row) -> User:
        """Convert DB row to User model."""
        return User(
            id=row[0],
            name=row[1],
            email=row[2],
            role=row[3],
            avatar=row[4],
            is_new_user=bool(row[5]),
            is_active=bool(row[6]),
            last_login=row[7],
            failed_login_attempts=row[8] or 0,
            locked_until=row[9],
            created_at=row[10],
            updated_at=row[11],
        )

    def _row_to_user_with_password(self, row) -> UserWithPassword:
        """Convert DB row to UserWithPassword model (includes password_hash)."""
        return UserWithPassword(
            id=row[0],
            name=row[1],
            email=row[2],
            password_hash=row[3],
            role=row[4],
            avatar=row[5],
            is_new_user=bool(row[6]),
            is_active=bool(row[7]),
            last_login=row[8],
            failed_login_attempts=row[9] or 0,
            locked_until=row[10],
            created_at=row[11],
            updated_at=row[12],
        )

    def get_user_by_email(self, email: str) -> Optional[UserWithPassword]:
        """Get user by email (includes password_hash for login verification)."""
        query = """
            SELECT id, name, email, password_hash, role, avatar, is_new_user,
                   is_active, last_login, failed_login_attempts, locked_until,
                   created_at, updated_at
            FROM users
            WHERE email = %s AND is_active = 1
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(email),))
            row = cursor.fetchone()
            return self._row_to_user_with_password(row) if row else None

    def get_user_by_id(self, user_id) -> Optional[User]:
        """Get user by ID (excludes password_hash)."""
        query = """
            SELECT id, name, email, role, avatar, is_new_user, is_active,
                   last_login, failed_login_attempts, locked_until,
                   created_at, updated_at
            FROM users
            WHERE id = %s AND is_active = 1
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(user_id),))
            row = cursor.fetchone()
            return self._row_to_user(row) if row else None

    def get_users(self, page: int = 1, limit: int = 20, search: Optional[str] = None, role: Optional[str] = None) -> Tuple[List[User], int]:
        """List users with pagination and optional filters."""
        limit = min(limit, 100)
        offset = (page - 1) * limit

        conditions = ["is_active = 1"]
        params = []

        if search:
            conditions.append("(name LIKE %s OR email LIKE %s)")
            search_escaped = search.replace('[', '[[]').replace('%', '[%]').replace('_', '[_]')
            search_param = "%" + search_escaped + "%"
            params.extend([search_param, search_param])

        if role:
            conditions.append("role = %s")
            params.append(role)

        where_clause = "WHERE " + " AND ".join(conditions)

        count_query = "SELECT COUNT(*) FROM users " + where_clause
        query = (
            "SELECT id, name, email, role, avatar, is_new_user, is_active,"
            " last_login, failed_login_attempts, locked_until,"
            " created_at, updated_at"
            " FROM users " + where_clause +
            " ORDER BY name ASC"
            " OFFSET %s ROWS FETCH NEXT %s ROWS ONLY"
        )

        with self.get_connection() as conn:
            cursor = conn.cursor()

            _execute(cursor, count_query, tuple(params))
            total = cursor.fetchone()[0]

            _execute(cursor, query, tuple(params) + (offset, limit))
            rows = cursor.fetchall()
            users = [self._row_to_user(row) for row in rows]

        return users, total

    def create_user(self, user_data: UserCreate, password_hash: str) -> User:
        """Create a new user. Password comes pre-hashed from auth_service."""
        query = """
            INSERT INTO users (name, email, password_hash, role)
            OUTPUT INSERTED.id, INSERTED.name, INSERTED.email, INSERTED.role,
                   INSERTED.avatar, INSERTED.is_new_user, INSERTED.is_active,
                   INSERTED.last_login, INSERTED.failed_login_attempts,
                   INSERTED.locked_until, INSERTED.created_at, INSERTED.updated_at
            VALUES (%s, %s, %s, %s)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (
                str(user_data.name),
                str(user_data.email),
                str(password_hash),
                str(user_data.role),
            ))
            row = cursor.fetchone()
            conn.commit()
            return self._row_to_user(row)

    def update_user(self, user_id, data: UserUpdate) -> Optional[User]:
        """Update user fields dynamically from non-None fields."""
        updates = []
        params = []

        if data.name is not None:
            updates.append("name = %s")
            params.append(data.name)
        if data.email is not None:
            updates.append("email = %s")
            params.append(data.email)
        if data.role is not None:
            updates.append("role = %s")
            params.append(data.role)
        if data.is_active is not None:
            updates.append("is_active = %s")
            params.append(1 if data.is_active else 0)

        if not updates:
            return self.get_user_by_id(user_id)

        updates.append("updated_at = GETUTCDATE()")
        params.append(str(user_id))

        query = _build_update_query("users", updates, "id = %s AND is_active = 1")

        with self.get_connection() as conn:
            cursor = conn.cursor()
            _execute(cursor, query, tuple(params))
            conn.commit()

        return self.get_user_by_id(user_id)

    def deactivate_user(self, user_id) -> bool:
        """Soft-deactivate a user."""
        query = """
            UPDATE users
            SET is_active = 0, updated_at = GETUTCDATE()
            WHERE id = %s
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(user_id),))
            affected = cursor.rowcount
            conn.commit()
            return affected > 0

    def reset_user_password(self, user_id, new_password_hash: str) -> bool:
        """Reset user password and mark as new user (force password change)."""
        query = """
            UPDATE users
            SET password_hash = %s, is_new_user = 1, updated_at = GETUTCDATE()
            WHERE id = %s
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(new_password_hash), str(user_id)))
            affected = cursor.rowcount
            conn.commit()
            return affected > 0

    def set_user_not_new(self, user_id) -> bool:
        """Clear is_new_user flag after user changes password."""
        query = """
            UPDATE users
            SET is_new_user = 0, updated_at = GETUTCDATE()
            WHERE id = %s
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(user_id),))
            affected = cursor.rowcount
            conn.commit()
            return affected > 0

    def record_failed_login(self, user_id) -> None:
        """Increment failed login attempts; lock account after threshold."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE users SET failed_login_attempts = failed_login_attempts + 1, updated_at = GETUTCDATE() WHERE id = %s",
                (str(user_id),)
            )

            cursor.execute(
                "SELECT failed_login_attempts FROM users WHERE id = %s",
                (str(user_id),)
            )
            row = cursor.fetchone()
            if row and row[0] >= self.LOCKOUT_THRESHOLD:
                cursor.execute(
                    "UPDATE users SET locked_until = DATEADD(minute, %s, GETUTCDATE()) WHERE id = %s",
                    (self.LOCKOUT_MINUTES, str(user_id))
                )

            conn.commit()

    def record_successful_login(self, user_id) -> None:
        """Reset failed attempts, clear lock, update last_login."""
        query = """
            UPDATE users
            SET failed_login_attempts = 0, locked_until = NULL,
                last_login = GETUTCDATE(), updated_at = GETUTCDATE()
            WHERE id = %s
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(user_id),))
            conn.commit()
