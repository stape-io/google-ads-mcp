import os
from typing import Literal

import httpx
from fastmcp.server.auth import AuthProvider, RemoteAuthProvider
from pydantic import AnyHttpUrl

from ads_mcp.auth.google_provider import GoogleProvider

from .jwt import JWTProvider
from .settings import (
    GOOGLE_ADS_MCP_REQUIRED_SCOPES,
    BasicAuthSettings,
    BearerAuthSettings,
    GoogleAdsMCPSettings,
    JwtProviderSettings,
    OAuthSettings,
    TokenVerifierSettings,
)
from .token_verifier import BearerAuth, TokenVerifier


def _get_jwt_provider() -> JWTProvider:
    from joserfc import jwk

    settings = JwtProviderSettings()  # type: ignore[call-arg]
    if not settings.private_keys or settings.algorithm is None:
        raise ValueError(
            "JWTProvider cannot be created without private keys and algorithm."
        )

    private_keys = jwk.KeySet.import_key_set({"keys": settings.private_keys})

    return JWTProvider(
        private_keys=private_keys,
        algorithm=settings.algorithm,
        claims=settings.claims,
        token_lifetime=settings.token_lifetime,
    )


def _get_bearer_auth() -> httpx.Auth:
    settings = BearerAuthSettings()
    if settings.token is not None:
        token = settings.token.get_secret_value()
        return BearerAuth(token_provider=lambda: token)
    else:
        return BearerAuth(token_provider=_get_jwt_provider())


def _get_basic_auth() -> httpx.Auth:
    settings: BasicAuthSettings = BasicAuthSettings()  # type: ignore[call-arg]
    return httpx.BasicAuth(
        username=settings.username,
        password=settings.password.get_secret_value(),
    )


def _get_token_verifier_auth(
    type: Literal["bearer", "basic", "none"],
) -> httpx.Auth | None:
    if type == "bearer":
        return _get_bearer_auth()
    elif type == "basic":
        return _get_basic_auth()
    elif type == "none":
        return None
    else:
        raise ValueError(f"Unsupported auth type: {type}")


def get_token_verifier(
    required_scopes: list[str] | None = None,
) -> TokenVerifier:
    if required_scopes is None:
        required_scopes = GOOGLE_ADS_MCP_REQUIRED_SCOPES
    settings = TokenVerifierSettings()
    return TokenVerifier(
        auth=_get_token_verifier_auth(settings.auth),
        url=settings.url,
        method=settings.method,
        required_scopes=required_scopes,
        content_type=settings.content_type,
    )


def get_google_auth_provider(base_url: str) -> GoogleProvider:
    oauth_settings = OAuthSettings()  # type: ignore[call-arg]
    if not oauth_settings.client_id or not oauth_settings.client_secret:
        raise ValueError(
            "GoogleProvider cannot be created without client ID and client secret."
        )
    return GoogleProvider(
        client_id=oauth_settings.client_id,
        client_secret=oauth_settings.client_secret.get_secret_value(),
        base_url=base_url,
        required_scopes=GOOGLE_ADS_MCP_REQUIRED_SCOPES,
    )


def get_remote_auth_provider(base_url: str, auth_server_url: AnyHttpUrl | str) -> RemoteAuthProvider:
    return RemoteAuthProvider(
        token_verifier=get_token_verifier(),
        authorization_servers=[AnyHttpUrl(auth_server_url)],
        base_url=base_url,
        scopes_supported=GOOGLE_ADS_MCP_REQUIRED_SCOPES,
    )


def get_mcp_auth_provider() -> AuthProvider | None:
    settings = GoogleAdsMCPSettings()
    if settings.auth_provider == "google":
        return get_google_auth_provider(settings.base_url)
    elif settings.auth_provider == "remote":
        if settings.auth_server_url is None:
            raise ValueError("Remote auth provider requires auth_server_url to be set.")
        return get_remote_auth_provider(settings.base_url, settings.auth_server_url)
    elif settings.auth_provider == "none":
        return None
