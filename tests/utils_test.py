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

"""Test cases for the utils module."""

import unittest
from unittest.mock import MagicMock, patch

from ads_mcp import utils
from google.ads.googleads.v25.common.types.metrics import Metrics
from google.ads.googleads.v25.enums.types.campaign_status import (
    CampaignStatusEnum,
)


class TestUtils(unittest.TestCase):
    """Test cases for the utils module."""

    def test_format_output_value(self):
        """Tests that output values are formatted correctly."""

        self.assertEqual(
            utils.format_output_value(
                CampaignStatusEnum.CampaignStatus.ENABLED
            ),
            "ENABLED",
        )

    def test_format_output_value_primitive(self):
        """Tests that primitive values are returned as is."""
        self.assertEqual(utils.format_output_value(123), 123)
        self.assertEqual(utils.format_output_value("abc"), "abc")

    def test_format_output_value_message(self):
        """Tests that proto messages are converted to dict."""
        metrics = Metrics(clicks=10, impressions=100)
        formatted = utils.format_output_value(metrics)
        self.assertIsInstance(formatted, dict)
        self.assertEqual(formatted.get("clicks"), "10")
        self.assertEqual(formatted.get("impressions"), "100")

    def test_format_output_value_repeated_primitive(self):
        """Tests that repeated primitive values are formatted."""
        self.assertEqual(
            utils.format_output_value([1, 2, 3]),
            [1, 2, 3],
        )

    def test_format_output_value_repeated_message(self):
        """Tests that repeated proto messages are formatted."""
        metrics1 = Metrics(clicks=10)
        metrics2 = Metrics(clicks=20)
        formatted = utils.format_output_value([metrics1, metrics2])
        self.assertIsInstance(formatted, list)
        self.assertEqual(len(formatted), 2)
        self.assertEqual(formatted[0].get("clicks"), "10")
        self.assertEqual(formatted[1].get("clicks"), "20")

    @patch("ads_mcp.utils.httpx.get")
    @patch("ads_mcp.utils._create_credentials")
    def test_download_authenticated_url(
        self, mock_create_credentials, mock_httpx_get
    ):
        """Tests that download_authenticated_url sends a bearer token and
        returns the response content."""
        mock_credentials = MagicMock()
        mock_credentials.valid = True
        mock_credentials.token = "fake-token"
        mock_create_credentials.return_value = mock_credentials

        mock_response = MagicMock()
        mock_response.content = b"file content"
        mock_httpx_get.return_value = mock_response

        result = utils.download_authenticated_url("https://example.com/f")

        mock_httpx_get.assert_called_once_with(
            "https://example.com/f",
            headers={"Authorization": "Bearer fake-token"},
            timeout=30.0,
        )
        mock_response.raise_for_status.assert_called_once()
        self.assertEqual(result, b"file content")

    @patch("ads_mcp.utils.httpx.get")
    @patch("ads_mcp.utils._create_credentials")
    def test_download_authenticated_url_refreshes_invalid_credentials(
        self, mock_create_credentials, mock_httpx_get
    ):
        """Tests that credentials are refreshed if not already valid (e.g.
        Application Default Credentials, which start without a token)."""
        mock_credentials = MagicMock()
        mock_credentials.valid = False
        mock_credentials.token = "refreshed-token"
        mock_create_credentials.return_value = mock_credentials

        mock_response = MagicMock()
        mock_response.content = b"file content"
        mock_httpx_get.return_value = mock_response

        utils.download_authenticated_url("https://example.com/f")

        mock_credentials.refresh.assert_called_once()


class TestCreateCredentials(unittest.TestCase):
    """Test cases for the caller-token / ADC fallback in _create_credentials."""

    def setUp(self):
        patcher = patch.object(utils, "_adc_fallback_allowed", False)
        patcher.start()
        self.addCleanup(patcher.stop)

    @patch("google.auth.default")
    @patch("fastmcp.server.dependencies.get_access_token")
    def test_no_caller_token_on_http_raises(
        self, mock_get_access_token, mock_default
    ):
        """HTTP entrypoints never opt in to ADC, so a request that lost its
        caller context fails closed instead of using the server's identity."""
        mock_get_access_token.return_value = None

        with self.assertRaises(ValueError):
            utils._create_credentials()

        mock_default.assert_not_called()

    @patch.dict(
        "os.environ",
        {
            "GOOGLE_ADS_MCP_AUTH_PROVIDER": "remote",
            "GOOGLE_ADS_MCP_AUTH_SERVER_URL": "https://auth.example.com",
        },
    )
    @patch("google.auth.default")
    @patch("fastmcp.server.dependencies.get_access_token")
    def test_no_caller_token_on_stdio_uses_adc(
        self, mock_get_access_token, mock_default
    ):
        """stdio opts in via allow_adc_fallback, even when an auth provider is
        configured in .env (the example.env setup)."""
        mock_get_access_token.return_value = None
        mock_default.return_value = (MagicMock(), None)

        utils.allow_adc_fallback()
        utils._create_credentials()

        mock_default.assert_called_once()
