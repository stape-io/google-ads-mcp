#!/usr/bin/env python

# Copyright 2026 Google LLC.
# Modified by Stape, 2026
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Common utilities used by the MCP server."""

import functools
import importlib.resources
import logging
import os
import time
from collections.abc import Set
from contextvars import ContextVar
from typing import Any

import google.auth
import google.auth.transport.requests
import httpx
import proto
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.util import get_nested_attr

from ads_mcp.mcp_header_interceptor import MCPHeaderInterceptor

# filename for generated field information used by search
_GAQL_FILENAME = "gaql_resources.txt"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# OAuth scope for the Google Ads API. Google Ads does not publish a separate
# read-only scope; access is restricted to read methods by the tools this
# server exposes (see ads_mcp/tools/).
_ADS_SCOPE = "https://www.googleapis.com/auth/adwords"

# Context variable that overrides GOOGLE_ADS_LOGIN_CUSTOMER_ID for the current
# async context (e.g. per-request in a FastMCP server).
_login_customer_id_var: ContextVar[str | None] = ContextVar(
    "login_customer_id", default=None
)


def set_login_customer_id(customer_id: str | None) -> None:
    """Set the login customer ID for the current context."""
    _login_customer_id_var.set(customer_id)


# How long the multi-MB Google docs resources are served from memory. Bounded
# because several of them track moving targets (`latest`, release notes).
RESOURCE_TTL_SECONDS = 6 * 60 * 60


def ttl_cache(seconds: float):
    """Caches a zero-argument function's result for `seconds`.

    Unlike functools.lru_cache, the value expires, so a long-running server
    picks up changes Google publishes. Keeps `cache_clear` for tests.
    """

    def decorator(fn):
        cached: tuple[float, Any] | None = None

        @functools.wraps(fn)
        def wrapper():
            nonlocal cached
            now = time.monotonic()
            if cached is None or now - cached[0] >= seconds:
                cached = (now, fn())
            return cached[1]

        def cache_clear() -> None:
            nonlocal cached
            cached = None

        wrapper.cache_clear = cache_clear
        return wrapper

    return decorator


# ADC is this server's own identity, so it is only allowed when the process is
# explicitly running over stdio (see run_server). Defaulting to False keeps
# every HTTP entrypoint (run_server's HTTP branch and `server:app`) fail-closed,
# including when a request loses its caller context.
_adc_fallback_allowed = False


def allow_adc_fallback() -> None:
    """Permit Application Default Credentials when no caller token exists.

    Call only from a stdio entrypoint, where the local user is the caller.
    """
    global _adc_fallback_allowed
    _adc_fallback_allowed = True


def _create_credentials() -> google.auth.credentials.Credentials:
    """Returns Application Default Credentials with the Google Ads scope, or the FastMCP token if found."""
    from fastmcp.server.dependencies import get_access_token
    from google.oauth2.credentials import Credentials

    token_obj = get_access_token()
    if token_obj and token_obj.token:
        # Create credentials using the access token provided by FastMCP
        return Credentials(token=token_obj.token)

    # No caller token. ADC is the intended path for stdio/local use only; over
    # HTTP every request belongs to a user, so falling back would silently run
    # their query as this server's own identity instead of failing loudly.
    if not _adc_fallback_allowed:
        raise ValueError(
            "No caller credentials available on an HTTP server; "
            "refusing to fall back to this server's own identity."
        )

    credentials, _ = google.auth.default(scopes=[_ADS_SCOPE])
    return credentials


def _get_developer_token() -> str:
    """Returns the developer token from the environment variable GOOGLE_ADS_DEVELOPER_TOKEN."""
    dev_token = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN")
    if dev_token is None:
        raise ValueError(
            "GOOGLE_ADS_DEVELOPER_TOKEN environment variable not set."
        )
    return dev_token


def _get_login_customer_id() -> str | None:
    """Returns login customer id from the context variable or, as a fallback,
    from the GOOGLE_ADS_LOGIN_CUSTOMER_ID environment variable."""
    ctx_value = _login_customer_id_var.get()
    if ctx_value is not None:
        return ctx_value
    return os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID")


def _get_googleads_client() -> GoogleAdsClient:
    args: dict[str, Any] = {
        "credentials": _create_credentials(),
        "developer_token": _get_developer_token(),
        "use_proto_plus": True,
    }

    # If the login-customer-id is not set, avoid setting None.
    login_customer_id = _get_login_customer_id()

    if login_customer_id:
        args["login_customer_id"] = login_customer_id

    client = GoogleAdsClient(**args)

    return client


def get_googleads_service(serviceName: str) -> Any:
    return _get_googleads_client().get_service(
        serviceName, interceptors=[MCPHeaderInterceptor()]
    )


def get_googleads_type(typeName: str):
    return _get_googleads_client().get_type(typeName)


def get_googleads_client():
    return _get_googleads_client()


def format_output_value(value: Any) -> Any:
    if isinstance(value, proto.Enum):
        return value.name
    elif isinstance(value, proto.Message):
        return proto.Message.to_dict(value)
    elif hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
        return [format_output_value(v) for v in value]
    else:
        return value


def format_output_row(row: proto.Message, attributes):
    return {
        attr: format_output_value(get_nested_attr(row, attr))
        for attr in attributes
    }


def get_gaql_resources_filepath():
    package_root = importlib.resources.files("ads_mcp")
    file_path = package_root.joinpath(_GAQL_FILENAME)
    return file_path


def _describe_url(url: httpx.URL) -> str:
    """Scheme and host only, for error messages: the path or query of a
    download URL may carry signed tokens."""
    return f"{url.scheme or '(no scheme)'}://{url.host or '(no host)'}"


def _parse_authenticated_download_url(
    url: str, allowed_hosts: Set[str]
) -> httpx.URL:
    """Parses `url` and rejects it unless it is https on one of `allowed_hosts`.

    Hosts match exactly (no subdomains), and URLs with an explicit non-default
    port or userinfo are rejected. Returns the parsed URL so the caller
    requests exactly what was checked.
    """
    # Checked at runtime too: a bare str would turn the membership test below
    # into a substring test.
    if not isinstance(allowed_hosts, (set, frozenset)):
        raise TypeError(
            "allowed_hosts must be a set or frozenset of host names"
        )
    try:
        parsed = httpx.URL(url)
        # Reading .host can raise too (e.g. idna.IDNAError, a ValueError).
        host = parsed.host
    except (httpx.InvalidURL, ValueError) as ex:
        raise ValueError(f"Invalid URL: {ex}") from ex
    if (
        parsed.scheme != "https"
        or host not in allowed_hosts
        # httpx normalizes the scheme's default port (:443) to None.
        or parsed.port is not None
        or parsed.userinfo
    ):
        allowed = " or ".join(f"https://{h}/" for h in sorted(allowed_hosts))
        raise ValueError(
            "Refusing to send Google Ads credentials to "
            f"{_describe_url(parsed)}: only URLs on {allowed} are allowed."
        )
    return parsed


def download_authenticated_url(url: str, *, allowed_hosts: Set[str]) -> bytes:
    """Downloads a URL that requires the same Ads OAuth credentials as gRPC calls.

    The caller names the hosts the credentials may be sent to; any other URL
    is rejected before credentials are fetched. See
    `_parse_authenticated_download_url`.
    """
    parsed_url = _parse_authenticated_download_url(url, allowed_hosts)
    credentials = _create_credentials()
    if not credentials.valid:
        credentials.refresh(google.auth.transport.requests.Request())
    # Invoice PDFs are multi-MB; httpx's 5s default is not enough.
    # follow_redirects is deliberately left off: httpx strips the
    # Authorization header on cross-origin redirects, so following one
    # would silently drop the credential and fail as a 401 instead of a
    # legible 3xx.
    response = httpx.get(
        parsed_url,
        headers={"Authorization": f"Bearer {credentials.token}"},
        timeout=30.0,
    )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as ex:
        # httpx's own message includes the full URL.
        raise httpx.HTTPStatusError(
            f"HTTP {response.status_code} {response.reason_phrase} from "
            f"{_describe_url(parsed_url)}",
            request=ex.request,
            response=ex.response,
        ) from None
    return response.content
