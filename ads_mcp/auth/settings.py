
import datetime as dt
import os
from typing import Any, Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

GOOGLE_ADS_MCP_PREFIX = "google_ads_mcp"
GOOGLE_ADS_MCP_AUTH_PREFIX = "google_ads_mcp_auth"

GOOGLE_ADS_MCP_ENV_FILE = os.environ.get(f"{GOOGLE_ADS_MCP_PREFIX.upper()}_ENV_FILE", ".env")

def create_settings_config(path: tuple[str, ...]) -> SettingsConfigDict:
    if path:
        env_path = "_".join(part.lower() for part in path)
        env_path = f"{GOOGLE_ADS_MCP_AUTH_PREFIX}_{env_path}"
    else:
        env_path = GOOGLE_ADS_MCP_AUTH_PREFIX
    return SettingsConfigDict(
        env_prefix=env_path + "_",
        env_file=GOOGLE_ADS_MCP_ENV_FILE,
        case_sensitive=False,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class BasicAuthSettings(BaseSettings):
    model_config = create_settings_config(("basic", "auth"))

    username: str
    password: SecretStr


class BearerAuthSettings(BaseSettings):
    model_config = create_settings_config(("bearer", "auth"))

    token: SecretStr | None = None


class JwtProviderSettings(BaseSettings):
    model_config = create_settings_config(("jwt", "provider"))

    private_keys: list[dict[str, Any]]
    algorithm: str | None = None
    token_lifetime: dt.timedelta = dt.timedelta(minutes=1)
    claims: dict[str, Any] = Field(default_factory=dict)


class TokenVerifierSettings(BaseSettings):
    model_config = create_settings_config(("token", "verifier"))

    url: str = "https://www.googleapis.com/oauth2/v1/tokeninfo"
    auth: Literal["bearer", "basic", "none"] = "none"
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"] = "GET"
    content_type: Literal[
        "application/json", "application/x-www-form-urlencoded"
    ] = "application/json"
