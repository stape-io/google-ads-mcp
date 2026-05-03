import datetime as dt
import os
from typing import Any, Literal

from pydantic import AnyHttpUrl, Field, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

GOOGLE_ADS_MCP_REQUIRED_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/adwords",
]

GOOGLE_ADS_MCP_PREFIX = "google_ads_mcp"

GOOGLE_ADS_MCP_ENV_FILE = os.environ.get(
    f"{GOOGLE_ADS_MCP_PREFIX.upper()}_ENV_FILE", ".env"
)


def create_settings_config(path: tuple[str, ...]) -> SettingsConfigDict:
    if path:
        env_path = "_".join(part.lower() for part in path)
        env_path = f"{GOOGLE_ADS_MCP_PREFIX}_{env_path}"
    else:
        env_path = GOOGLE_ADS_MCP_PREFIX
    return SettingsConfigDict(
        env_prefix=env_path + "_",
        env_file=GOOGLE_ADS_MCP_ENV_FILE,
        case_sensitive=False,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class BasicAuthSettings(BaseSettings):
    model_config = create_settings_config(("auth", "basic"))

    username: str
    password: SecretStr


class BearerAuthSettings(BaseSettings):
    model_config = create_settings_config(("auth", "bearer"))

    token: SecretStr | None = None


class JwtProviderSettings(BaseSettings):
    model_config = create_settings_config(("auth", "jwt", "provider"))

    private_keys: list[dict[str, Any]]
    algorithm: str | None = None
    token_lifetime: dt.timedelta = dt.timedelta(minutes=1)
    claims: dict[str, Any] = Field(default_factory=dict)


class AuthStorageSettings(BaseSettings):
    model_config = create_settings_config(("auth", "storage"))

    type: Literal["in-memory", "redis", "disk"] | None = None
    redis_url: RedisDsn | None = None
    encryption_key: SecretStr | None = None
    disk_directory: str | None = None


class TokenVerifierSettings(BaseSettings):
    model_config = create_settings_config(("auth", "token", "verifier"))

    url: str = "https://www.googleapis.com/oauth2/v1/tokeninfo"
    auth: Literal["bearer", "basic", "none"] = "none"
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"] = "GET"
    content_type: Literal[
        "application/json", "application/x-www-form-urlencoded"
    ] = "application/json"


class OAuthSettings(BaseSettings):
    model_config = create_settings_config(("oauth",))

    client_id: str
    client_secret: SecretStr


class GoogleAdsMCPSettings(BaseSettings):
    model_config = create_settings_config(())
    base_url: str = "http://127.0.0.1:8080"
    auth_provider: Literal["google", "remote", "none"] = "none"
    auth_server_url: AnyHttpUrl | None = None
