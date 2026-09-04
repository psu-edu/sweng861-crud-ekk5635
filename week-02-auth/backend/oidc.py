"""Google's OpenID Connect provider metadata.

The authorization, token, and JWKS URLs are not hardcoded. Every OIDC provider
publishes them in a discovery document at a well-known address, and reading
them from there means this code keeps working when Google moves an endpoint —
and that the same three lines would point at a different provider by changing
one URL.

Fetched once per process: the document is effectively static, and a login
should not pay for an extra round trip every time.
"""

from dataclasses import dataclass
from functools import lru_cache

import httpx

GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"


@dataclass(frozen=True)
class ProviderMetadata:
    """The four values of the discovery document this application uses."""

    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str


@lru_cache(maxsize=1)
def get_provider_metadata() -> ProviderMetadata:
    response = httpx.get(GOOGLE_DISCOVERY_URL, timeout=10.0)
    response.raise_for_status()
    document = response.json()
    return ProviderMetadata(
        issuer=document["issuer"],
        authorization_endpoint=document["authorization_endpoint"],
        token_endpoint=document["token_endpoint"],
        jwks_uri=document["jwks_uri"],
    )
