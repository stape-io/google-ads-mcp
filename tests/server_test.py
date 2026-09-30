# Copyright 2026 Google LLC.
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

"""Test cases for the server module."""

import unittest
from unittest import mock


class TestUtils(unittest.TestCase):
    """Test cases for the server module."""

    def test_server_initialization(self):
        """Tests that the MCP server instance is initialized.

        This servers as a smoke test to confirm there are no obvious issues
        with initialization, such as missing imports.
        """
        from ads_mcp import server

        self.assertIsNotNone(server.mcp, "MCP server instance not initialized")


class RunServerCredentialPolicyTest(unittest.TestCase):
    """Only the stdio branch may opt in to the ADC fallback."""

    @mock.patch("ads_mcp.server.mcp.run")
    @mock.patch("ads_mcp.server.allow_adc_fallback")
    def test_stdio_allows_adc(self, mock_allow, _run):
        from ads_mcp import server

        with mock.patch.dict("os.environ", {}, clear=True):
            server.run_server()

        mock_allow.assert_called_once()

    @mock.patch("ads_mcp.server.mcp.run")
    @mock.patch("ads_mcp.server.allow_adc_fallback")
    def test_http_does_not_allow_adc(self, mock_allow, _run):
        from ads_mcp import server

        env = {
            "GOOGLE_ADS_MCP_OAUTH_CLIENT_ID": "id",
            "GOOGLE_ADS_MCP_OAUTH_CLIENT_SECRET": "secret",
        }
        with mock.patch.dict("os.environ", env, clear=True):
            server.run_server()

        mock_allow.assert_not_called()


class DeployedAppCredentialPolicyTest(unittest.TestCase):
    def test_importing_server_app_does_not_allow_adc(self):
        """`uvicorn server:app` never goes through run_server, so it must stay
        fail-closed on the server's own identity."""
        import server  # noqa: F401

        from ads_mcp import utils

        self.assertFalse(utils._adc_fallback_allowed)


class ProtocolNegotiationTest(unittest.IsolatedAsyncioTestCase):
    """Locks in the protocol revisions this server actually serves.

    The rest of the suite calls tool functions directly and never speaks the
    protocol; tests/smoke/ speaks it but pins the 2024-11-05 handshake. These
    tests are the only thing asserting that 2026-07-28 is served at all.
    """

    async def _negotiate(self, mode):
        from ads_mcp.server import mcp
        from fastmcp import Client

        async with Client(mcp, mode=mode) as client:
            # Deliberately not client.initialize_result: the modern era has no
            # `initialize` handshake (it sends server/discover), so that
            # attribute is None under mode="auto".
            version = client.protocol_version
            tools = await client.list_tools()
            resources = await client.list_resources()
        return (
            version,
            {t.name for t in tools},
            {str(r.uri) for r in resources},
        )

    async def test_negotiates_modern_protocol(self):
        """A modern client must get 2026-07-28, not a 2025-era fallback."""
        version, tools, resources = await self._negotiate("auto")
        # Literal, not mcp.types.LATEST_PROTOCOL_VERSION: asserting against
        # the constant is tautological and would pass on any future bump.
        self.assertEqual(version, "2026-07-28")
        self.assertIn("search", tools)
        self.assertIn("resource://metrics", resources)

    async def test_legacy_clients_still_served(self):
        """Pre-2026 clients keep working, with an identical inventory."""
        legacy = await self._negotiate("legacy")
        modern = await self._negotiate("auto")
        self.assertEqual(legacy[0], "2025-11-25")
        self.assertEqual(legacy[1], modern[1])
        self.assertEqual(legacy[2], modern[2])


class HttpAppTest(unittest.TestCase):
    """The only test covering the object uvicorn actually serves."""

    def test_deployed_app_builds_with_healthz(self):
        import server

        self.assertIn("/healthz", [r.path for r in server.app.routes])
