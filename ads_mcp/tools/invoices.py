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

"""Tools for listing and downloading Google Ads invoices."""

import base64
from typing import Any, cast

import ads_mcp.utils as utils
import proto
from ads_mcp.coordinator import mcp
from fastmcp.exceptions import ToolError
from google.ads.googleads.errors import GoogleAdsException
from google.ads.googleads.v25.services.services.google_ads_service import (
    GoogleAdsServiceClient,
)
from google.ads.googleads.v25.services.services.invoice_service import (
    InvoiceServiceClient,
)
from mcp.types import ToolAnnotations


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True))
def list_invoices(
    customer_id: str,
    billing_setup_id: str,
    issue_year: str,
    issue_month: str,
    login_customer_id: str | None = None,
) -> list[dict[str, Any]]:
    """Lists invoices issued for a given billing setup and month.

    Requires the account to have monthly invoicing enabled. Most advertisers
    are on automatic payments and will get an empty result or an error for
    this tool.

    Args:
        customer_id: The id of the serving customer account (plain numeric
            string, e.g. "1234567890").
        billing_setup_id: The numeric id of the billing setup. Discoverable
            via the `search` tool: SELECT billing_setup.id FROM billing_setup.
        issue_year: The invoice issue year, e.g. "2026". Invoices before 2019
            cannot be retrieved.
        issue_month: The invoice issue month name in uppercase, e.g. "MARCH".
        login_customer_id: The customer ID of the manager account, required
            when customer_id is a client account (sub-account) under a
            manager (MCC) — same as the `search` tool's parameter of the
            same name.
    """
    if login_customer_id:
        utils.set_login_customer_id(login_customer_id)

    ga_service = cast(
        GoogleAdsServiceClient, utils.get_googleads_service("GoogleAdsService")
    )
    billing_setup = ga_service.billing_setup_path(customer_id, billing_setup_id)

    invoice_service = cast(
        InvoiceServiceClient, utils.get_googleads_service("InvoiceService")
    )
    try:
        response = invoice_service.list_invoices(
            customer_id=customer_id,
            billing_setup=billing_setup,
            issue_year=issue_year,
            # proto-plus enum fields accept the enum member's name as a str
            # and resolve it at construction time; the generated stub only
            # types the enum member itself.
            issue_month=issue_month.upper(),  # type: ignore[arg-type]
        )
    except GoogleAdsException as ex:
        error_msgs = [
            f"Google Ads API Error: {error.message}"
            for error in ex.failure.errors
        ]
        raise ToolError(
            f"Request ID: {ex.request_id}\n" + "\n".join(error_msgs)
        )

    return [proto.Message.to_dict(invoice) for invoice in response.invoices]


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True))
def download_invoice_pdf(pdf_url: str) -> dict[str, Any]:
    """Downloads one invoice's PDF document.

    Args:
        pdf_url: The `pdf_url` of an invoice, as returned by `list_invoices`.

    Returns:
        A dict with `content_type` and the base64-encoded PDF in
        `content_base64` (MCP tool results must be JSON-serializable, so raw
        binary content can't be returned directly).
    """
    try:
        content = utils.download_authenticated_url(pdf_url)
    except Exception as ex:
        raise ToolError(f"Failed to download invoice PDF: {ex}")

    return {
        "content_type": "application/pdf",
        "content_base64": base64.b64encode(content).decode("ascii"),
    }
