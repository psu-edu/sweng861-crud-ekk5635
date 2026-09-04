"""FastAPI application for Week 2 — authentication and protected APIs.

Week 1 shipped an unauthenticated Hello/Health service. This service is where
the Google OIDC login flow, the local user store, and the `requireAuth`
middleware are built; `/api/hello` becomes a protected endpoint here.
"""

import base64
import hashlib
import secrets
from contextlib import asynccontextmanager
from urllib.parse import urlencode

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from config import get_settings
from db import create_tables
from oidc import get_provider_metadata

# Short-lived cookies that carry the login attempt from the redirect to the
# callback. All three are per-attempt random values; none is a secret the user
# needs, so all three are HttpOnly.
STATE_COOKIE = "oauth_state"      # CSRF: ties the callback to this browser
NONCE_COOKIE = "oauth_nonce"      # replay: ties the id_token to this attempt
VERIFIER_COOKIE = "oauth_verifier"  # PKCE: proves who redeems the code started it

# The user has ten minutes to finish consenting at Google.
STATE_TTL_SECONDS = 600

# openid gets an id_token at all; email and profile are what this app stores.
# Nothing more is requested - an authorization the app does not need is an
# authorization it cannot misuse.
SCOPES = "openid email profile"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure the users table exists before the first request is served.

    Run on startup rather than at import time so that importing this module —
    which the tests do — neither needs a database nor creates one.
    """
    create_tables()
    yield


app = FastAPI(
    title="SWENG 861 Week 2 — Auth API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. Deliberately unauthenticated: a monitor has no login."""
    return {"status": "ok"}


@app.get("/auth/login")
def login() -> RedirectResponse:
    """Leg 1 of the three-legged flow: send the user to Google to authenticate.

    The state parameter is the CSRF defense. It is a random value that goes out
    in the redirect and is simultaneously stored in a cookie on this site. When
    Google sends the user back, /auth/callback only accepts the request if the
    state in the query string matches the one in the cookie. An attacker can
    make a victim's browser hit the callback URL with an authorization code of
    the attacker's own - which would log the victim into the attacker's
    account - but the attacker cannot write a cookie on this origin, so the
    forged request has nothing to match and is rejected.

    Two further values ride along. The nonce is echoed by Google inside the
    id_token, so the callback can tell this attempt's token from an older one
    replayed at it. PKCE sends only the SHA-256 of a random verifier now and
    the verifier itself at redemption, so an authorization code that leaks out
    of the browser cannot be spent by whoever picked it up.

    All three cookies are HttpOnly (script cannot read them), SameSite=Lax
    (sent on the top-level redirect back from Google, but not on cross-site
    subrequests), scoped to /auth (never attached to API calls), and Secure
    whenever the redirect URI is https - http is only ever used for localhost.
    """
    settings = get_settings()
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)

    # S256 challenge: base64url of the SHA-256 digest, no padding, per RFC 7636.
    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
        .decode()
        .rstrip("=")
    )

    query = urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": SCOPES,
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )
    authorization_url = f"{get_provider_metadata().authorization_endpoint}?{query}"

    response = RedirectResponse(authorization_url, status_code=302)
    for name, value in (
        (STATE_COOKIE, state),
        (NONCE_COOKIE, nonce),
        (VERIFIER_COOKIE, code_verifier),
    ):
        response.set_cookie(
            name,
            value,
            max_age=STATE_TTL_SECONDS,
            httponly=True,
            samesite="lax",
            secure=settings.google_redirect_uri.startswith("https://"),
            path="/auth",
        )
    return response
