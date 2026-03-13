"""
API REST para autenticacao e gerenciamento de usuarios.
"""
import azure.functions as func
import json
import logging
from math import ceil
from datetime import datetime, timedelta, timezone

from services.database import get_db
from services.async_db import run_db
from services.auth_service import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, is_account_locked,
    LOCKOUT_THRESHOLD, LOCKOUT_DURATION_MINUTES
)
from services.rate_limiter import RateLimiter
from models import UserLogin, UserCreate, UserUpdate

logger = logging.getLogger(__name__)


def _parse_cookies(cookie_header: str) -> dict:
    """Parse Cookie header into a dict."""
    cookies = {}
    if not cookie_header:
        return cookies
    for item in cookie_header.split(";"):
        item = item.strip()
        if "=" in item:
            key, value = item.split("=", 1)
            cookies[key.strip()] = value.strip()
    return cookies


async def login_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/auth/login - Authenticate user and return tokens.
    """
    try:
        # Rate limit check
        retry_after = RateLimiter.get().check("auth-login")
        if retry_after is not None:
            return func.HttpResponse(
                json.dumps({"error": "Rate limit exceeded", "retry_after_seconds": round(retry_after, 1)}),
                status_code=429,
                headers={"Retry-After": str(int(retry_after) + 1)},
                mimetype="application/json",
            )

        # Parse body
        try:
            body = req.get_json()
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid JSON body"}),
                status_code=400,
                mimetype="application/json"
            )

        email = body.get("email", "").strip().lower()
        password = body.get("password", "")
        remember_me = body.get("remember_me", False)

        if not email or not password:
            return func.HttpResponse(
                json.dumps({"error": "Email e senha sao obrigatorios"}),
                status_code=400,
                mimetype="application/json"
            )

        db = get_db()

        # Look up user by email
        user = await run_db(db.get_user_by_email, email)
        if not user:
            return func.HttpResponse(
                json.dumps({"error": "Email ou senha incorretos"}),
                status_code=401,
                mimetype="application/json"
            )

        # Check account lockout
        if is_account_locked(user.locked_until):
            return func.HttpResponse(
                json.dumps({
                    "error": "Conta bloqueada temporariamente",
                    "locked_until": user.locked_until.isoformat() if user.locked_until else None,
                }),
                status_code=423,
                mimetype="application/json"
            )

        # Verify password
        if not verify_password(password, user.password_hash):
            await run_db(db.record_failed_login, str(user.id))
            try:
                await run_db(db.log_auth_event, str(user.id), user.email, "login_failed", req.headers.get("X-Forwarded-For", "unknown"))
            except Exception as audit_err:
                logger.warning(f"Non-fatal: failed to log auth event: {audit_err}")
            return func.HttpResponse(
                json.dumps({"error": "Email ou senha incorretos"}),
                status_code=401,
                mimetype="application/json"
            )

        # Successful login
        await run_db(db.record_successful_login, str(user.id))
        try:
            await run_db(db.log_auth_event, str(user.id), user.email, "login_success", req.headers.get("X-Forwarded-For", "unknown"))
        except Exception as audit_err:
            logger.warning(f"Non-fatal: failed to log auth event: {audit_err}")

        # Create tokens
        access_token = create_access_token(
            user_id=str(user.id),
            email=user.email,
            role=user.role,
            name=user.name,
        )
        refresh_token = create_refresh_token(
            user_id=str(user.id),
            remember_me=remember_me,
        )

        # Build response
        response_body = {
            "access_token": access_token,
            "user": user.to_frontend_format(),
        }

        # Set refresh token as HttpOnly cookie
        # SameSite=None required: frontend (azurestaticapps.net) and API (azurewebsites.net)
        # are cross-site — Lax blocks cookies on cross-site POST (refresh never works).
        max_age = 30 * 24 * 3600 if remember_me else 7 * 24 * 3600
        cookie = (
            f"refresh_token={refresh_token}; "
            f"HttpOnly; SameSite=None; Secure; "
            f"Path=/api/auth; Max-Age={max_age}"
        )

        return func.HttpResponse(
            json.dumps(response_body, default=str),
            status_code=200,
            headers={"Set-Cookie": cookie},
            mimetype="application/json"
        )

    except Exception as e:
        logger.exception(f"Error in login: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )


async def refresh_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/auth/refresh - Rotate refresh token and issue new access token.

    Implements refresh token rotation with reuse detection:
    - Each refresh token can only be used once (single-use).
    - On use, old token is blacklisted and a new one is issued (same family).
    - If a blacklisted token is reused beyond the grace period, the entire
      token family is revoked (indicates token theft).
    - Grace period (30s) handles benign race conditions from concurrent tabs.
    """
    GRACE_PERIOD_SECONDS = 30
    clear_cookie = "refresh_token=; HttpOnly; SameSite=None; Secure; Path=/api/auth; Max-Age=0"

    try:
        # 1. Parse refresh token from Cookie header
        cookie_header = req.headers.get("Cookie", "")
        cookies = _parse_cookies(cookie_header)
        refresh_token_str = cookies.get("refresh_token")

        if not refresh_token_str:
            return func.HttpResponse(
                json.dumps({"error": "Refresh token not found"}),
                status_code=401,
                mimetype="application/json"
            )

        # 2. Decode and validate JWT
        payload = decode_token(refresh_token_str)
        if not payload:
            return func.HttpResponse(
                json.dumps({"error": "Invalid or expired refresh token"}),
                status_code=401,
                mimetype="application/json"
            )

        if payload.get("type") != "refresh":
            return func.HttpResponse(
                json.dumps({"error": "Invalid token type"}),
                status_code=401,
                mimetype="application/json"
            )

        # 3. Extract jti and token family
        jti = payload.get("jti")
        token_family = payload.get("family")
        user_id = payload.get("sub")

        if not jti or not token_family or not user_id:
            return func.HttpResponse(
                json.dumps({"error": "Malformed refresh token"}),
                status_code=401,
                mimetype="application/json"
            )

        db = get_db()

        # 4. REUSE DETECTION: check if this token was already used (blacklisted)
        if await run_db(db.is_token_blacklisted, jti):
            blacklist_info = await run_db(db.get_blacklisted_token_info, jti)

            if blacklist_info and blacklist_info.get("replaced_at"):
                # Token was rotated (not logout-revoked). Check grace period.
                replaced_at = blacklist_info["replaced_at"]
                if replaced_at.tzinfo is None:
                    replaced_at = replaced_at.replace(tzinfo=timezone.utc)
                elapsed = (datetime.now(timezone.utc) - replaced_at).total_seconds()

                if elapsed <= GRACE_PERIOD_SECONDS:
                    # Benign race condition (e.g. concurrent tabs).
                    # Return the token that replaced this one (already issued).
                    logger.info(f"Refresh token reuse within grace period ({elapsed:.1f}s) for user {user_id}")
                    # We cannot re-issue the same replacement token, so just
                    # issue a fresh access token. The client already has the
                    # new refresh token from the first request.
                    user = await run_db(db.get_user_by_id, user_id)
                    if not user or not user.is_active:
                        return func.HttpResponse(
                            json.dumps({"error": "User not found or inactive"}),
                            status_code=401,
                            mimetype="application/json"
                        )
                    access_token = create_access_token(
                        user_id=str(user.id),
                        email=user.email,
                        role=user.role,
                        name=user.name,
                    )
                    return func.HttpResponse(
                        json.dumps({"access_token": access_token}, default=str),
                        status_code=200,
                        mimetype="application/json"
                    )
                else:
                    # COMPROMISE DETECTED: token reused after grace period.
                    # Revoke the entire token family.
                    logger.warning(
                        f"SECURITY: Refresh token reuse detected after {elapsed:.1f}s "
                        f"for user {user_id}, family {token_family}. Revoking family."
                    )
                    await run_db(db.blacklist_token_family, token_family, user_id)
                    try:
                        await run_db(
                            db.log_auth_event, user_id, "",
                            "token_family_revoked",
                            req.headers.get("X-Forwarded-For", "unknown"),
                        )
                    except Exception:
                        pass  # Non-fatal audit log failure
                    return func.HttpResponse(
                        json.dumps({"error": "Token has been revoked"}),
                        status_code=401,
                        headers={"Set-Cookie": clear_cookie},
                        mimetype="application/json"
                    )
            else:
                # Token was revoked by logout (no replaced_at), not rotated.
                return func.HttpResponse(
                    json.dumps({"error": "Token has been revoked"}),
                    status_code=401,
                    headers={"Set-Cookie": clear_cookie},
                    mimetype="application/json"
                )

        # 5. FAMILY CHECK: entire family may have been revoked
        if await run_db(db.is_family_revoked, token_family):
            logger.warning(f"Refresh attempt on revoked family {token_family} for user {user_id}")
            return func.HttpResponse(
                json.dumps({"error": "Token has been revoked"}),
                status_code=401,
                headers={"Set-Cookie": clear_cookie},
                mimetype="application/json"
            )

        # 6. Get user and verify active
        user = await run_db(db.get_user_by_id, user_id)
        if not user or not user.is_active:
            return func.HttpResponse(
                json.dumps({"error": "User not found or inactive"}),
                status_code=401,
                mimetype="application/json"
            )

        # 7. Create new access token
        access_token = create_access_token(
            user_id=str(user.id),
            email=user.email,
            role=user.role,
            name=user.name,
        )

        # 8. Determine remember_me from old token's lifetime
        iat = payload.get("iat", 0)
        exp = payload.get("exp", 0)
        token_lifetime_days = (exp - iat) / 86400 if exp and iat else 7
        remember_me = token_lifetime_days > 14  # 28-day tokens are remember_me

        # 9. Create new refresh token (same family)
        new_refresh_token = create_refresh_token(
            user_id=str(user.id),
            remember_me=remember_me,
            token_family=token_family,
        )

        # 10. Get new token's jti
        new_payload = decode_token(new_refresh_token)
        new_jti = new_payload.get("jti") if new_payload else None

        # 11. Blacklist old token (rotation, not revocation)
        old_exp_ts = payload.get("exp")
        if old_exp_ts:
            old_expires_at = datetime.fromtimestamp(old_exp_ts, tz=timezone.utc)
        else:
            old_expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        await run_db(
            db.blacklist_token_rotated,
            jti, user_id, old_expires_at, token_family, new_jti
        )

        # 12. Set new refresh token cookie
        max_age = 30 * 24 * 3600 if remember_me else 7 * 24 * 3600
        cookie = (
            f"refresh_token={new_refresh_token}; "
            f"HttpOnly; SameSite=None; Secure; "
            f"Path=/api/auth; Max-Age={max_age}"
        )

        # 13. Return new access token with rotated refresh cookie
        return func.HttpResponse(
            json.dumps({"access_token": access_token}, default=str),
            status_code=200,
            headers={"Set-Cookie": cookie},
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in refresh: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )


async def me_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/auth/me - Return current user profile.
    Requires req.user injected by auth middleware.
    """
    try:
        db = get_db()
        user = await run_db(db.get_user_by_id, req.user["id"])

        if not user:
            return func.HttpResponse(
                json.dumps({"error": "User not found"}),
                status_code=404,
                mimetype="application/json"
            )

        return func.HttpResponse(
            json.dumps(user.to_frontend_format(), default=str),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in me: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )


async def update_me_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    PATCH /api/auth/me - Update current user profile.
    Currently supports: is_new_user toggle.
    """
    try:
        try:
            body = req.get_json()
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid JSON body"}),
                status_code=400,
                mimetype="application/json"
            )

        db = get_db()

        # Handle is_new_user toggle (onboarding complete)
        if body.get("is_new_user") is False:
            await run_db(db.set_user_not_new, req.user["id"])

        # Return updated user
        user = await run_db(db.get_user_by_id, req.user["id"])
        if not user:
            return func.HttpResponse(
                json.dumps({"error": "User not found"}),
                status_code=404,
                mimetype="application/json"
            )

        return func.HttpResponse(
            json.dumps(user.to_frontend_format(), default=str),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in update_me: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )


async def logout_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/auth/logout - Invalidate tokens and clear refresh cookie.
    """
    try:
        db = get_db()

        # Blacklist current access token
        jti = req.user.get("jti")
        if jti:
            # Extract actual expiry from the access token JWT
            auth_header = req.headers.get("Authorization", "")
            access_token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
            access_payload = decode_token(access_token) if access_token else None
            exp_ts = access_payload.get("exp") if access_payload else None
            if exp_ts:
                exp = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
            else:
                # Fallback: 1 hour from now (default access token lifetime)
                exp = datetime.now(timezone.utc) + timedelta(hours=1)
            await run_db(db.blacklist_token, jti, req.user["id"], exp)

        # Also blacklist refresh token if present
        cookie_header = req.headers.get("Cookie", "")
        cookies = _parse_cookies(cookie_header)
        refresh_token = cookies.get("refresh_token")
        if refresh_token:
            payload = decode_token(refresh_token)
            if payload and payload.get("jti"):
                exp_ts = payload.get("exp")
                if exp_ts:
                    exp = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
                else:
                    exp = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59)
                await run_db(db.blacklist_token, payload["jti"], req.user["id"], exp)

                # Revoke entire token family to invalidate any rotated tokens
                token_family = payload.get("family")
                if token_family:
                    try:
                        await run_db(db.blacklist_token_family, token_family, req.user["id"])
                    except Exception as e:
                        logger.warning(f"Failed to revoke token family on logout: {e}")

        # Log audit event
        await run_db(db.log_auth_event, req.user["id"], req.user["email"], "logout", req.headers.get("X-Forwarded-For", "unknown"))

        # Clear refresh_token cookie
        clear_cookie = "refresh_token=; HttpOnly; SameSite=None; Secure; Path=/api/auth; Max-Age=0"

        return func.HttpResponse(
            json.dumps({"message": "Logout successful"}),
            status_code=200,
            headers={"Set-Cookie": clear_cookie},
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in logout: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )


async def list_users_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/auth/users - List users with pagination (admin only).
    """
    try:
        page = int(req.params.get('page', '1'))
        limit = min(int(req.params.get('limit', '20')), 100)
        search = req.params.get('search')
        role = req.params.get('role')

        if page < 1:
            page = 1

        db = get_db()
        users, total = await run_db(db.get_users, page=page, limit=limit, search=search, role=role)

        pages = ceil(total / limit) if total > 0 else 1

        response = {
            "items": [u.to_frontend_format() for u in users],
            "total": total,
            "page": page,
            "pages": pages,
        }

        return func.HttpResponse(
            json.dumps(response, default=str),
            status_code=200,
            mimetype="application/json"
        )

    except ValueError as e:
        logger.warning(f"Invalid parameter in list_users: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Parametro invalido"}),
            status_code=400,
            mimetype="application/json"
        )
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )


async def create_user_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/auth/users - Create a new user (admin only).
    """
    try:
        try:
            body = req.get_json()
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid JSON body"}),
                status_code=400,
                mimetype="application/json"
            )

        # Validate with model
        try:
            user_data = UserCreate(
                name=body.get("name", ""),
                email=body.get("email", ""),
                password=body.get("password", ""),
                role=body.get("role", "user"),
            )
        except Exception as e:
            logger.warning(f"User create validation error: {e}")
            return func.HttpResponse(
                json.dumps({"error": "Erro de validacao nos dados do usuario"}),
                status_code=400,
                mimetype="application/json"
            )

        db = get_db()

        # Check email uniqueness
        existing = await run_db(db.get_user_by_email, user_data.email.lower())
        if existing:
            return func.HttpResponse(
                json.dumps({"error": "Email ja esta em uso"}),
                status_code=409,
                mimetype="application/json"
            )

        # Hash password and create
        password_hash = hash_password(user_data.password)
        user = await run_db(db.create_user, user_data, password_hash)

        # Log audit
        await run_db(
            db.log_auth_event,
            req.user["id"], req.user["email"], "password_change",
            req.headers.get("X-Forwarded-For", "unknown"),
            metadata={"detail": f"Created user {user.email} (role={user.role})"}
        )

        logger.info(f"User created: {user.email} by admin {req.user['email']}")

        return func.HttpResponse(
            json.dumps(user.to_frontend_format(), default=str),
            status_code=201,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )


async def update_user_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    PUT /api/auth/users/{id} - Update a user (admin only).
    """
    try:
        user_id = req.route_params.get("id")
        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "User ID is required"}),
                status_code=400,
                mimetype="application/json"
            )

        try:
            body = req.get_json()
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid JSON body"}),
                status_code=400,
                mimetype="application/json"
            )

        # Validate with model
        try:
            update_data = UserUpdate(
                name=body.get("name"),
                email=body.get("email"),
                role=body.get("role"),
                is_active=body.get("is_active"),
            )
        except Exception as e:
            logger.warning(f"User update validation error: {e}")
            return func.HttpResponse(
                json.dumps({"error": "Erro de validacao nos dados do usuario"}),
                status_code=400,
                mimetype="application/json"
            )

        db = get_db()
        user = await run_db(db.update_user, user_id, update_data)

        if not user:
            return func.HttpResponse(
                json.dumps({"error": "User not found"}),
                status_code=404,
                mimetype="application/json"
            )

        return func.HttpResponse(
            json.dumps(user.to_frontend_format(), default=str),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )


async def delete_user_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    DELETE /api/auth/users/{id} - Deactivate a user (admin only, soft delete).
    """
    try:
        user_id = req.route_params.get("id")
        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "User ID is required"}),
                status_code=400,
                mimetype="application/json"
            )

        db = get_db()
        success = await run_db(db.deactivate_user, user_id)

        if not success:
            return func.HttpResponse(
                json.dumps({"error": "User not found"}),
                status_code=404,
                mimetype="application/json"
            )

        # Log audit
        await run_db(
            db.log_auth_event,
            req.user["id"], req.user["email"], "account_locked",
            req.headers.get("X-Forwarded-For", "unknown"),
            metadata={"detail": f"Deactivated user {user_id}"}
        )

        logger.info(f"User deactivated: {user_id} by admin {req.user['email']}")

        return func.HttpResponse(
            json.dumps({"message": "User deactivated successfully"}),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error deactivating user: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )


async def reset_password_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/auth/users/{id}/reset-password - Admin reset user password.
    """
    try:
        user_id = req.route_params.get("id")
        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "User ID is required"}),
                status_code=400,
                mimetype="application/json"
            )

        try:
            body = req.get_json()
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid JSON body"}),
                status_code=400,
                mimetype="application/json"
            )

        new_password = body.get("new_password", "")
        if len(new_password) < 10:
            return func.HttpResponse(
                json.dumps({"error": "Password must be at least 10 characters"}),
                status_code=400,
                mimetype="application/json"
            )

        db = get_db()
        password_hash = hash_password(new_password)
        success = await run_db(db.reset_user_password, user_id, password_hash)

        if not success:
            return func.HttpResponse(
                json.dumps({"error": "User not found"}),
                status_code=404,
                mimetype="application/json"
            )

        # Log audit
        await run_db(
            db.log_auth_event,
            req.user["id"], req.user["email"], "password_reset",
            req.headers.get("X-Forwarded-For", "unknown"),
            metadata={"detail": f"Password reset for user {user_id}"}
        )

        logger.info(f"Password reset for user {user_id} by admin {req.user['email']}")

        return func.HttpResponse(
            json.dumps({"message": "Password reset successfully"}),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error resetting password: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )
