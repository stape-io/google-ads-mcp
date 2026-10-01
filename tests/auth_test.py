# Copyright 2026 Stape
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

"""Test cases for the auth providers.

The production deployment runs GOOGLE_ADS_MCP_AUTH_PROVIDER=google, so
GoogleProvider/OAuthProxy is the live auth path. The upgrade risk there is
kwarg drift rather than logic: get_google_auth_provider passes 8 keyword
arguments straight through to the SDK provider, and a rename in a future
FastMCP major would fail at boot -- after the image ships. So these tests go
*through* the factories rather than around them.
"""

import os
import unittest
from unittest import mock

from ads_mcp import auth
from ads_mcp.auth.google_provider import GoogleProvider
from ads_mcp.auth.settings import GOOGLE_ADS_MCP_REQUIRED_SCOPES
from fastmcp.server.auth.providers.google import (
    GoogleProvider as _SDKGoogleProvider,
)

# Every value is set explicitly so that a developer's gitignored .env cannot
# change the outcome: in pydantic-settings, environment variables take
# precedence over the dotenv file. The keys are syntactically valid but inert.
_FERNET_KEY = "YWRzLW1jcC10ZXN0LWtleS1ub3QtYS1zZWNyZXQhISE="
AUTH_ENV = {
    "GOOGLE_ADS_MCP_OAUTH_CLIENT_ID": "test.apps.googleusercontent.com",
    "GOOGLE_ADS_MCP_OAUTH_CLIENT_SECRET": "GOCSPX-test-secret",
    "GOOGLE_ADS_MCP_OAUTH_REQUIRE_AUTHORIZATION_CONSENT": "external",
    "GOOGLE_ADS_MCP_OAUTH_JWT_SIGNING_KEY": _FERNET_KEY,
    "GOOGLE_ADS_MCP_AUTH_STORAGE_TYPE": "in-memory",
    "GOOGLE_ADS_MCP_AUTH_STORAGE_ENCRYPTION_KEY": _FERNET_KEY,
}

BASE_URL = "https://mcp.example.test"


class _AuthEnvTestCase(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.dict(os.environ, AUTH_ENV)
        patcher.start()
        self.addCleanup(patcher.stop)


class AuthProviderFactoryTest(_AuthEnvTestCase):
    """Guards the kwargs the factories hand to the SDK providers."""

    def test_google_provider_builds(self):
        provider = auth.get_google_auth_provider(BASE_URL)

        self.assertIsInstance(provider, GoogleProvider)
        self.assertEqual(
            provider.required_scopes, GOOGLE_ADS_MCP_REQUIRED_SCOPES
        )

    def test_remote_provider_builds(self):
        provider = auth.get_remote_auth_provider(
            BASE_URL, "https://accounts.google.com"
        )

        self.assertEqual(
            provider.token_verifier.required_scopes,
            GOOGLE_ADS_MCP_REQUIRED_SCOPES,
        )

    def test_remote_provider_requires_auth_server_url(self):
        with self.assertRaises(ValueError):
            auth.get_remote_auth_provider(BASE_URL, None)


class ExtractUpstreamClaimsTest(
    _AuthEnvTestCase, unittest.IsolatedAsyncioTestCase
):
    """Covers the local override of a *private* SDK hook.

    Patching _extract_upstream_claims on the parent doubles as a tripwire: if a
    future FastMCP renames or removes it, mock.patch.object raises
    AttributeError and this fails loudly, instead of the subclass silently
    becoming dead code that never runs.
    """

    def setUp(self):
        super().setUp()
        self.provider = auth.get_google_auth_provider(BASE_URL)

    @mock.patch("ads_mcp.auth.google_provider.get_google_user_info")
    @mock.patch.object(
        _SDKGoogleProvider,
        "_extract_upstream_claims",
        new_callable=mock.AsyncMock,
    )
    async def test_merges_user_profile_claims(self, mock_super, mock_userinfo):
        mock_super.return_value = {"sub": "123"}
        mock_userinfo.return_value = {
            "email": "someone@example.test",
            "name": "Some One",
            "unexpected": "dropped",
        }

        claims = await self.provider._extract_upstream_claims(
            {
                "access_token": "tok",
                "scope": "https://www.googleapis.com/auth/userinfo.email",
            }
        )

        self.assertEqual(
            claims,
            {
                "sub": "123",
                "email": "someone@example.test",
                "name": "Some One",
            },
        )

    @mock.patch("ads_mcp.auth.google_provider.get_google_user_info")
    @mock.patch.object(
        _SDKGoogleProvider,
        "_extract_upstream_claims",
        new_callable=mock.AsyncMock,
    )
    async def test_no_profile_scope_skips_userinfo(
        self, mock_super, mock_userinfo
    ):
        mock_super.return_value = {"sub": "123"}

        claims = await self.provider._extract_upstream_claims(
            {
                "access_token": "tok",
                "scope": "https://www.googleapis.com/auth/adwords",
            }
        )

        self.assertEqual(claims, {"sub": "123"})
        mock_userinfo.assert_not_called()


if __name__ == "__main__":
    unittest.main()
