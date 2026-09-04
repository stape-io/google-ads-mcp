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

"""Test cases for the invoices tools."""

import unittest
from unittest.mock import MagicMock, patch

from ads_mcp.tools import invoices
from google.ads.googleads.v25.resources.types.invoice import Invoice


class TestListInvoices(unittest.TestCase):
    """Test cases for the list_invoices tool."""

    @patch("ads_mcp.utils.get_googleads_service")
    def test_list_invoices_basic(self, mock_get_service):
        """Tests that list_invoices builds the billing_setup path, uppercases
        issue_month, and formats the returned invoices."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.billing_setup_path.return_value = (
            "customers/1234567890/billingSetups/999"
        )

        mock_response = MagicMock()
        mock_response.invoices = [
            Invoice(id="1", pdf_url="https://example.com/1.pdf"),
            Invoice(id="2", pdf_url="https://example.com/2.pdf"),
        ]
        mock_service.list_invoices.return_value = mock_response

        results = invoices.list_invoices(
            customer_id="1234567890",
            billing_setup_id="999",
            issue_year="2026",
            issue_month="march",
        )

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

    @patch("ads_mcp.utils.set_login_customer_id")
    @patch("ads_mcp.utils.get_googleads_service")
    def test_list_invoices_sets_login_customer_id(
        self, mock_get_service, mock_set_login_customer_id
    ):
        """Tests that a provided login_customer_id is set before the calls."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.billing_setup_path.return_value = (
            "customers/1234567890/billingSetups/999"
        )
        mock_response = MagicMock()
        mock_response.invoices = []
        mock_service.list_invoices.return_value = mock_response

        invoices.list_invoices(
            customer_id="1234567890",
            billing_setup_id="999",
            issue_year="2026",
            issue_month="march",
            login_customer_id="9876543210",
        )

        mock_set_login_customer_id.assert_called_once_with("9876543210")

    @patch("ads_mcp.utils.set_login_customer_id")
    @patch("ads_mcp.utils.get_googleads_service")
    def test_list_invoices_without_login_customer_id(
        self, mock_get_service, mock_set_login_customer_id
    ):
        """Tests that login_customer_id is left unset when not provided."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.billing_setup_path.return_value = (
            "customers/1234567890/billingSetups/999"
        )
        mock_response = MagicMock()
        mock_response.invoices = []
        mock_service.list_invoices.return_value = mock_response

        invoices.list_invoices(
            customer_id="1234567890",
            billing_setup_id="999",
            issue_year="2026",
            issue_month="march",
        )

        mock_set_login_customer_id.assert_not_called()

    @patch("ads_mcp.utils.get_googleads_service")
    def test_list_invoices_google_ads_exception(self, mock_get_service):
        """Tests that list_invoices surfaces GoogleAdsException as a ToolError."""
        from google.ads.googleads.errors import GoogleAdsException

        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.billing_setup_path.return_value = (
            "customers/1234567890/billingSetups/999"
        )

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

        from fastmcp.exceptions import ToolError

        with self.assertRaises(ToolError) as context:
            invoices.list_invoices(
                customer_id="1234567890",
                billing_setup_id="999",
                issue_year="2026",
                issue_month="MARCH",
            )

        self.assertIn(
            "Google Ads API Error: Billing setup not found",
            str(context.exception),
        )
        self.assertIn("Request ID: req-456", str(context.exception))


class TestDownloadInvoicePdf(unittest.TestCase):
    """Test cases for the download_invoice_pdf tool."""

    @patch("ads_mcp.utils.download_authenticated_url")
    def test_download_invoice_pdf_basic(self, mock_download):
        mock_download.return_value = b"%PDF-1.4 fake content"

        result = invoices.download_invoice_pdf(
            pdf_url="https://example.com/invoice.pdf"
        )

        mock_download.assert_called_once_with("https://example.com/invoice.pdf")
        self.assertEqual(result["content_type"], "application/pdf")

        import base64

        self.assertEqual(
            base64.b64decode(result["content_base64"]),
            b"%PDF-1.4 fake content",
        )

    @patch("ads_mcp.utils.download_authenticated_url")
    def test_download_invoice_pdf_http_error(self, mock_download):
        import httpx
        from fastmcp.exceptions import ToolError

        mock_download.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=MagicMock()
        )

        with self.assertRaises(ToolError):
            invoices.download_invoice_pdf(
                pdf_url="https://example.com/missing.pdf"
            )


if __name__ == "__main__":
    unittest.main()
