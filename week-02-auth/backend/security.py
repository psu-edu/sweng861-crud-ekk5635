"""The reusable authentication gate for protected endpoints.

Written as a FastAPI dependency rather than ASGI middleware. Middleware runs on
every request, so protecting one route with it means the middleware itself
deciding which paths are exempt - a list that quietly rots as routes are added,
and whose default is "open". A dependency is declared on the routes that need
it, so a protected route cannot forget to be protected, and it hands the
handler a typed user instead of an untyped value on the request object.
"""

from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import get_settings
from tokens import ALGORITHM, ISSUER


@dataclass(frozen=True)
class AuthenticatedUser:
    """Who the caller is, according to their own token.

    Deliberately thin: the local user id and the email claim, which is all any
    Week 2 handler needs. Loading the database row here would mean a query on
    every request to fetch fields nothing reads.
    """

    id: int
    email: str | None


# auto_error=False so a missing header reaches this code and produces the
# error body the assignment specifies, instead of FastAPI's default shape.
_bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    """One 401 for every reason.

    Missing header, malformed token, bad signature, expired, wrong issuer - the
    caller is told the same thing each time. Explaining which check failed
    tells an attacker whether a token was genuine but stale, or forged.
    """
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": "Unauthorized", "message": "Valid access token is required"},
        # RFC 6750: a 401 from a bearer-protected resource says how to authenticate.
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthenticatedUser:
    """Verify the bearer token and return the caller's identity.

    The signature check is what makes the claims trustworthy: the payload of a
    JWT is base64, not ciphertext, so a caller can edit "sub" to any user id
    they like. Only the HMAC over the payload, which they cannot recompute
    without the signing key, decides whether those claims are ours.

    The issuer is pinned and the standard claims are required, so a token
    signed elsewhere, or one missing an expiry, is not accepted by default.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()

    try:
        claims = jwt.decode(
            credentials.credentials,
            get_settings().session_jwt_secret,
            algorithms=[ALGORITHM],
            issuer=ISSUER,
            options={"require": ["exp", "iat", "iss", "sub"]},
        )
    except jwt.PyJWTError:
        raise _unauthorized() from None

    return AuthenticatedUser(id=int(claims["sub"]), email=claims.get("email"))
