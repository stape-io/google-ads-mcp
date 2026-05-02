from typing import Literal

import httpx

from .jwt import JWTProvider
from .settings import (
    BasicAuthSettings,
    BearerAuthSettings,
    JwtProviderSettings,
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


def _get_token_verifier_auth(type: Literal["bearer", "basic", "none"]) -> httpx.Auth | None:
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

    settings = TokenVerifierSettings()
    return TokenVerifier(
        auth=_get_token_verifier_auth(settings.auth),
        url=settings.url,
        method=settings.method,
        required_scopes=required_scopes,
        content_type=settings.content_type,
    )
