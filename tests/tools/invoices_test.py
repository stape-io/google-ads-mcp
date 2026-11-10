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

"""Test cases for the invoices tools."""

import base64
import unittest
from unittest.mock import MagicMock, patch

import httpx
from ads_mcp.tools import invoices
from fastmcp.exceptions import ToolError
from google.ads.googleads.v25.resources.types.invoice import Invoice

_PDF_URL = "https://googleads.googleapis.com/invoice-2.pdf"

# Written out rather than read from invoices._INVOICE_PDF_HOSTS, so a typo or
# a wider set in the tool fails these tests.
_EXPECTED_PDF_HOSTS = frozenset(
    {"googleads.googleapis.com", "payments.google.com"}
)

_LIST_ARGS = {
    "customer_id": "1234567890",
    "billing_setup_id": "999",
    "issue_year": "2026",
    "issue_month": "march",
}

_DOWNLOAD_ARGS = {**_LIST_ARGS, "invoice_id": "2"}


def _mock_invoice_service(mock_get_service, invoices_list):
    """Points get_googleads_service at a mock returning `invoices_list`."""
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service
    mock_service.billing_setup_path.return_value = (
        "customers/1234567890/billingSetups/999"
    )
    mock_service.list_invoices.return_value = MagicMock(invoices=invoices_list)
    return mock_service


class TestListInvoices(unittest.TestCase):
    """Test cases for the list_invoices tool."""

    @patch("ads_mcp.utils.get_googleads_service")
    def test_list_invoices_basic(self, mock_get_service):
        """Tests that list_invoices builds the billing_setup path, uppercases
        issue_month, and formats the returned invoices."""
        mock_service = _mock_invoice_service(
            mock_get_service,
            [
                Invoice(id="1", pdf_url="https://example.com/1.pdf"),
                Invoice(id="2", pdf_url="https://example.com/2.pdf"),
            ],
        )

        results = invoices.list_invoices(**_LIST_ARGS)

        mock_service.billing_setup_path.assert_called_once_with(
            "1234567890", "999"
        )
        mock_service.list_invoices.assert_called_once_with(
            customer_id="1234567890",
            billing_setup="customers/1234567890/billingSetups/999",
            issue_year="2026",
            issue_month="MARCH",
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["id"], "1")
        self.assertEqual(results[0]["pdf_url"], "https://example.com/1.pdf")
        self.assertEqual(results[1]["id"], "2")

    @patch("ads_mcp.utils.get_googleads_service")
    def test_list_invoices_strips_issue_month(self, mock_get_service):
        mock_service = _mock_invoice_service(mock_get_service, [])

        invoices.list_invoices(**{**_LIST_ARGS, "issue_month": " March "})

        self.assertEqual(
            mock_service.list_invoices.call_args.kwargs["issue_month"], "MARCH"
        )

    @patch("ads_mcp.utils.get_googleads_service")
    def test_list_invoices_invalid_issue_month(self, mock_get_service):
        """An unknown month is a clear ToolError, not proto-plus's bare
        KeyError, and no request is made."""
        for month in ["MARC", "13", "", "unspecified", "UNKNOWN"]:
            with self.subTest(month=month):
                with self.assertRaises(ToolError) as context:
                    invoices.list_invoices(
                        **{**_LIST_ARGS, "issue_month": month}
                    )

                self.assertIn("Invalid issue_month", str(context.exception))

        mock_get_service.assert_not_called()

    @patch("ads_mcp.utils.set_login_customer_id")
    @patch("ads_mcp.utils.get_googleads_service")
    def test_list_invoices_sets_login_customer_id(
        self, mock_get_service, mock_set_login_customer_id
    ):
        """Tests that a provided login_customer_id is set before the calls."""
        _mock_invoice_service(mock_get_service, [])

        invoices.list_invoices(**_LIST_ARGS, login_customer_id="9876543210")

        mock_set_login_customer_id.assert_called_once_with("9876543210")

    @patch("ads_mcp.utils.set_login_customer_id")
    @patch("ads_mcp.utils.get_googleads_service")
    def test_list_invoices_without_login_customer_id(
        self, mock_get_service, mock_set_login_customer_id
    ):
        """Tests that login_customer_id is left unset when not provided."""
        _mock_invoice_service(mock_get_service, [])

        invoices.list_invoices(**_LIST_ARGS)

        mock_set_login_customer_id.assert_not_called()

    @patch("ads_mcp.utils.get_googleads_service")
    def test_list_invoices_google_ads_exception(self, mock_get_service):
        """Tests that list_invoices surfaces GoogleAdsException as a ToolError."""
        from google.ads.googleads.errors import GoogleAdsException

        mock_service = _mock_invoice_service(mock_get_service, [])

        mock_error = MagicMock()
        mock_error.message = "Billing setup not found"
        mock_failure = MagicMock()
        mock_failure.errors = [mock_error]

        mock_ex = GoogleAdsException(
            MagicMock(), MagicMock(), MagicMock(), MagicMock()
        )
        mock_ex.failure = mock_failure
        mock_ex.request_id = "req-456"

        mock_service.list_invoices.side_effect = mock_ex

        with self.assertRaises(ToolError) as context:
            invoices.list_invoices(**{**_LIST_ARGS, "issue_month": "MARCH"})

        self.assertIn(
            "Google Ads API Error: Billing setup not found",
            str(context.exception),
        )
        self.assertIn("Request ID: req-456", str(context.exception))


class TestDownloadInvoicePdf(unittest.TestCase):
    """Test cases for the download_invoice_pdf tool."""

    @patch("ads_mcp.utils.download_authenticated_url")
    @patch("ads_mcp.utils.get_googleads_service")
    def test_downloads_the_matching_invoice(
        self, mock_get_service, mock_download
    ):
        """Looks the invoice up by id and downloads the pdf_url Google
        returned for it, restricted to the invoice PDF hosts."""
        mock_service = _mock_invoice_service(
            mock_get_service,
            [
                Invoice(id="1", pdf_url="https://googleads.googleapis.com/1"),
                Invoice(id="2", pdf_url=_PDF_URL),
            ],
        )
        mock_download.return_value = b"%PDF-1.4 fake content"

        result = invoices.download_invoice_pdf(**_DOWNLOAD_ARGS)

        mock_service.list_invoices.assert_called_once_with(
            customer_id="1234567890",
            billing_setup="customers/1234567890/billingSetups/999",
            issue_year="2026",
            issue_month="MARCH",
        )
        mock_download.assert_called_once_with(
            _PDF_URL, allowed_hosts=_EXPECTED_PDF_HOSTS
        )
        self.assertEqual(result["content_type"], "application/pdf")
        self.assertEqual(
            base64.b64decode(result["content_base64"]),
            b"%PDF-1.4 fake content",
        )

    @patch("ads_mcp.utils.set_login_customer_id")
    @patch("ads_mcp.utils.download_authenticated_url")
    @patch("ads_mcp.utils.get_googleads_service")
    def test_sets_login_customer_id(
        self, mock_get_service, mock_download, mock_set_login_customer_id
    ):
        _mock_invoice_service(
            mock_get_service, [Invoice(id="2", pdf_url=_PDF_URL)]
        )
        mock_download.return_value = b"%PDF"

        invoices.download_invoice_pdf(
            **_DOWNLOAD_ARGS, login_customer_id="9876543210"
        )

        mock_set_login_customer_id.assert_called_once_with("9876543210")

    @patch("ads_mcp.utils.download_authenticated_url")
    @patch("ads_mcp.utils.get_googleads_service")
    def test_unknown_invoice_id(self, mock_get_service, mock_download):
        _mock_invoice_service(
            mock_get_service, [Invoice(id="1", pdf_url=_PDF_URL)]
        )

        with self.assertRaises(ToolError) as context:
            invoices.download_invoice_pdf(**_DOWNLOAD_ARGS)

        self.assertIn("Invoice 2 not found", str(context.exception))
        mock_download.assert_not_called()

    @patch("ads_mcp.utils.download_authenticated_url")
    @patch("ads_mcp.utils.get_googleads_service")
    def test_blank_invoice_id(self, mock_get_service, mock_download):
        """A blank id is rejected before the lookup, so it can't match an
        invoice whose id is unset."""
        _mock_invoice_service(mock_get_service, [Invoice(pdf_url=_PDF_URL)])

        for invoice_id in ["", "   "]:
            with self.subTest(invoice_id=invoice_id):
                with self.assertRaises(ToolError) as context:
                    invoices.download_invoice_pdf(
                        **{**_DOWNLOAD_ARGS, "invoice_id": invoice_id}
                    )

                self.assertIn("invoice_id is required", str(context.exception))

        mock_get_service.assert_not_called()
        mock_download.assert_not_called()

    @patch("ads_mcp.utils.download_authenticated_url")
    @patch("ads_mcp.utils.get_googleads_service")
    def test_invoice_without_pdf(self, mock_get_service, mock_download):
        _mock_invoice_service(mock_get_service, [Invoice(id="2")])

        with self.assertRaises(ToolError) as context:
            invoices.download_invoice_pdf(**_DOWNLOAD_ARGS)

        self.assertIn("has no PDF", str(context.exception))
        mock_download.assert_not_called()

    @patch("ads_mcp.utils.download_authenticated_url")
    @patch("ads_mcp.utils.get_googleads_service")
    def test_http_error(self, mock_get_service, mock_download):
        _mock_invoice_service(
            mock_get_service, [Invoice(id="2", pdf_url=_PDF_URL)]
        )
        mock_download.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=MagicMock()
        )

        with self.assertRaises(ToolError):
            invoices.download_invoice_pdf(**_DOWNLOAD_ARGS)


class TestDownloadInvoicePdfOverMcp(unittest.IsolatedAsyncioTestCase):
    """Calls the tool through the real server, so the lookup, the host check
    and the request are tested on the path a client actually takes."""

    async def _call(self, arguments):
        from ads_mcp.server import mcp
        from fastmcp import Client

        async with Client(mcp) as client:
            return await client.call_tool(
                "download_invoice_pdf", arguments, raise_on_error=False
            )

    @patch("ads_mcp.utils.httpx.get")
    @patch("fastmcp.server.dependencies.get_access_token")
    @patch("ads_mcp.utils.get_googleads_service")
    async def test_invoice_pdf_hosts_get_token(
        self, mock_get_service, mock_get_access_token, mock_httpx_get
    ):
        mock_get_access_token.return_value = MagicMock(token="user-token")
        mock_httpx_get.return_value = MagicMock(content=b"%PDF-1.4")

        for host in sorted(_EXPECTED_PDF_HOSTS):
            url = f"https://{host}/invoice-2.pdf"
            with self.subTest(host=host):
                mock_httpx_get.reset_mock()
                _mock_invoice_service(
                    mock_get_service, [Invoice(id="2", pdf_url=url)]
                )

                result = await self._call(_DOWNLOAD_ARGS)

                self.assertFalse(result.is_error, result.content)
                mock_httpx_get.assert_called_once_with(
                    httpx.URL(url),
                    headers={"Authorization": "Bearer user-token"},
                    timeout=30.0,
                )
                self.assertIsInstance(
                    mock_httpx_get.call_args.args[0], httpx.URL
                )

    @patch("ads_mcp.utils.httpx.get")
    @patch("fastmcp.server.dependencies.get_access_token")
    @patch("ads_mcp.utils.get_googleads_service")
    async def test_pdf_url_on_other_host_gets_no_token(
        self, mock_get_service, mock_get_access_token, mock_httpx_get
    ):
        """If an invoice's pdf_url is on another host, the error names it."""
        mock_get_access_token.return_value = MagicMock(token="user-token")
        _mock_invoice_service(
            mock_get_service,
            [Invoice(id="2", pdf_url="https://elsewhere.example/2.pdf")],
        )

        result = await self._call(_DOWNLOAD_ARGS)

        self.assertTrue(result.is_error)
        self.assertIn("https://elsewhere.example", result.content[0].text)
        mock_httpx_get.assert_not_called()

    @patch("ads_mcp.utils.httpx.get")
    @patch("fastmcp.server.dependencies.get_access_token")
    @patch("ads_mcp.utils.get_googleads_service")
    async def test_url_argument_is_not_accepted(
        self, mock_get_service, mock_get_access_token, mock_httpx_get
    ):
        """The tool has no URL argument: a call passing only pdf_url fails
        validation before anything is looked up or requested."""
        mock_get_access_token.return_value = MagicMock(token="user-token")

        result = await self._call({"pdf_url": "https://elsewhere.example/x"})

        self.assertTrue(result.is_error)
        mock_get_service.assert_not_called()
        mock_httpx_get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
