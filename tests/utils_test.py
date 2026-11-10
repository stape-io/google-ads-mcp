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

import httpx
from ads_mcp import utils
from google.ads.googleads.v25.common.types.metrics import Metrics
from google.ads.googleads.v25.enums.types.campaign_status import (
    CampaignStatusEnum,
)

# download_authenticated_url is generic: the caller passes the allowed hosts,
# so these tests use their own rather than the invoice tool's.
_ALLOWED_HOSTS = frozenset({"files.example.com", "docs.example.org"})
_FILE_URL = "https://files.example.com/f.pdf"


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
        """Tests that download_authenticated_url requests the parsed URL with
        a bearer token and returns the response content."""
        mock_credentials = MagicMock()
        mock_credentials.valid = True
        mock_credentials.token = "fake-token"
        mock_create_credentials.return_value = mock_credentials

        mock_response = MagicMock()
        mock_response.content = b"file content"
        mock_httpx_get.return_value = mock_response

        result = utils.download_authenticated_url(
            _FILE_URL, allowed_hosts=_ALLOWED_HOSTS
        )

        mock_httpx_get.assert_called_once_with(
            httpx.URL(_FILE_URL),
            headers={"Authorization": "Bearer fake-token"},
            timeout=30.0,
        )
        # httpx.URL compares equal to a str, so the assertion above would
        # also pass if the raw string were requested instead.
        self.assertIsInstance(mock_httpx_get.call_args.args[0], httpx.URL)
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

        utils.download_authenticated_url(
            _FILE_URL, allowed_hosts=_ALLOWED_HOSTS
        )

        mock_credentials.refresh.assert_called_once()

    @patch("ads_mcp.utils.httpx.get")
    @patch("ads_mcp.utils._create_credentials")
    def test_download_authenticated_url_rejects_other_urls(
        self, mock_create_credentials, mock_httpx_get
    ):
        """URLs outside the allowed hosts get no request and no credentials
        are even fetched. The error names the rejected host."""
        for url, target in [
            ("https://other.example.com/f.pdf", "https://other.example.com"),
            ("http://files.example.com/f.pdf", "http://files.example.com"),
            (
                "https://files.example.com.evil.com/f.pdf",
                "https://files.example.com.evil.com",
            ),
            (
                "https://evil.files.example.com/f.pdf",
                "https://evil.files.example.com",
            ),
            ("https://files.example.com@evil.com/f.pdf", "https://evil.com"),
            (
                "https://user:pass@files.example.com/f.pdf",
                "https://files.example.com",
            ),
            (
                "https://files.example.com:8443/f.pdf",
                "https://files.example.com",
            ),
            ("https://files.example.com./f.pdf", "https://files.example.com."),
            ("file:///etc/passwd", "file://(no host)"),
            ("/relative/f.pdf", "(no scheme)://(no host)"),
            ("https://[invalid/f.pdf", "https://%5Binvalid"),
        ]:
            with self.subTest(url=url):
                with self.assertRaises(ValueError) as context:
                    utils.download_authenticated_url(
                        url, allowed_hosts=_ALLOWED_HOSTS
                    )
                self.assertIn(
                    f"credentials to {target}:", str(context.exception)
                )

        mock_httpx_get.assert_not_called()
        mock_create_credentials.assert_not_called()

    @patch("ads_mcp.utils.httpx.get")
    @patch("ads_mcp.utils._create_credentials")
    def test_download_authenticated_url_rejects_unparseable_urls(
        self, mock_create_credentials, mock_httpx_get
    ):
        """Malformed URLs, including hosts that only fail IDNA decoding once
        .host is read, fail with the same "Invalid URL" error."""
        for url in ["https://[::1/f.pdf", "https://xn--zz/f.pdf"]:
            with self.subTest(url=url):
                with self.assertRaisesRegex(ValueError, "^Invalid URL: "):
                    utils.download_authenticated_url(
                        url, allowed_hosts=_ALLOWED_HOSTS
                    )

        mock_httpx_get.assert_not_called()
        mock_create_credentials.assert_not_called()

    @patch("ads_mcp.utils.httpx.get")
    @patch("ads_mcp.utils._create_credentials")
    def test_download_authenticated_url_rejects_str_allowed_hosts(
        self, mock_create_credentials, mock_httpx_get
    ):
        """A bare str would make the host check a substring test."""
        with self.assertRaises(TypeError):
            utils.download_authenticated_url(
                "https://le.com/f.pdf", allowed_hosts="files.example.com"
            )

        mock_httpx_get.assert_not_called()
        mock_create_credentials.assert_not_called()

    @patch("ads_mcp.utils.httpx.get")
    @patch("ads_mcp.utils._create_credentials")
    def test_download_authenticated_url_http_error_omits_path_and_query(
        self, mock_create_credentials, mock_httpx_get
    ):
        """httpx's own status error includes the full URL; ours names only
        the status, scheme and host."""
        url = "https://files.example.com/f.pdf?sig=secret"
        mock_create_credentials.return_value = MagicMock(valid=True)
        mock_httpx_get.return_value = httpx.Response(
            404, request=httpx.Request("GET", url)
        )

        with self.assertRaises(httpx.HTTPStatusError) as context:
            utils.download_authenticated_url(url, allowed_hosts=_ALLOWED_HOSTS)

        message = str(context.exception)
        self.assertEqual(
            message, "HTTP 404 Not Found from https://files.example.com"
        )
        self.assertNotIn("sig=secret", message)
        self.assertEqual(context.exception.response.status_code, 404)

    @patch("ads_mcp.utils.httpx.get")
    @patch("ads_mcp.utils._create_credentials")
    def test_download_authenticated_url_accepts_allowed_host_variants(
        self, mock_create_credentials, mock_httpx_get
    ):
        """Every allowed host is accepted, and case or an explicit default
        port don't change the host. Each request carries the token."""
        mock_create_credentials.return_value = MagicMock(
            valid=True, token="fake-token"
        )
        for url in [
            _FILE_URL,
            "https://Files.Example.com/f.pdf",
            "https://files.example.com:443/f.pdf",
            "https://docs.example.org/f.pdf",
        ]:
            with self.subTest(url=url):
                mock_httpx_get.reset_mock()

                utils.download_authenticated_url(
                    url, allowed_hosts=_ALLOWED_HOSTS
                )

                mock_httpx_get.assert_called_once_with(
                    httpx.URL(url),
                    headers={"Authorization": "Bearer fake-token"},
                    timeout=30.0,
                )
                self.assertIsInstance(
                    mock_httpx_get.call_args.args[0], httpx.URL
                )


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
