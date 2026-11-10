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

"""Tools for listing and downloading Google Ads invoices."""

import base64
from typing import Any, cast

import ads_mcp.utils as utils
import proto
from ads_mcp.coordinator import mcp
from fastmcp.exceptions import ToolError
from google.ads.googleads.errors import GoogleAdsException
from google.ads.googleads.v25.enums.types.month_of_year import MonthOfYearEnum
from google.ads.googleads.v25.resources.types.invoice import Invoice
from google.ads.googleads.v25.services.services.google_ads_service import (
    GoogleAdsServiceClient,
)
from google.ads.googleads.v25.services.services.invoice_service import (
    InvoiceServiceClient,
)
from mcp.types import ToolAnnotations

# Hosts download_invoice_pdf may send the caller's OAuth token to.
_INVOICE_PDF_HOSTS = frozenset(
    {"googleads.googleapis.com", "payments.google.com"}
)

_MONTHS = frozenset(MonthOfYearEnum.MonthOfYear.__members__) - {
    "UNSPECIFIED",
    "UNKNOWN",
}


def _normalize_issue_month(issue_month: str) -> str:
    """Returns the MonthOfYear enum name for `issue_month`, e.g. "MARCH".

    An unknown name would otherwise fail inside proto-plus as a bare
    KeyError, which reaches the client without saying what was wrong.
    """
    month = issue_month.strip().upper()
    if month not in _MONTHS:
        raise ToolError(
            f"Invalid issue_month {issue_month!r}: use an English month "
            'name, e.g. "MARCH".'
        )
    return month


def _fetch_invoices(
    customer_id: str,
    billing_setup_id: str,
    issue_year: str,
    issue_month: str,
    login_customer_id: str | None,
) -> list[Invoice]:
    """Calls InvoiceService.ListInvoices for one billing setup and month."""
    month = _normalize_issue_month(issue_month)
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
            issue_month=month,  # type: ignore[arg-type]
        )
    except GoogleAdsException as ex:
        error_msgs = [
            f"Google Ads API Error: {error.message}"
            for error in ex.failure.errors
        ]
        raise ToolError(
            f"Request ID: {ex.request_id}\n" + "\n".join(error_msgs)
        )

    return list(response.invoices)


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

    To get an invoice's PDF, pass its `id` with the same arguments to
    `download_invoice_pdf`.

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
    invoices = _fetch_invoices(
        customer_id,
        billing_setup_id,
        issue_year,
        issue_month,
        login_customer_id,
    )
    return [proto.Message.to_dict(invoice) for invoice in invoices]


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True))
def download_invoice_pdf(
    customer_id: str,
    billing_setup_id: str,
    issue_year: str,
    issue_month: str,
    invoice_id: str,
    login_customer_id: str | None = None,
) -> dict[str, Any]:
    """Downloads one invoice's PDF document.

    Takes the same arguments as `list_invoices` plus the invoice's `id`. The
    invoice is looked up again and the PDF Google links it to is downloaded.

    Args:
        customer_id: The id of the serving customer account (plain numeric
            string, e.g. "1234567890").
        billing_setup_id: The numeric id of the billing setup the invoice
            belongs to.
        issue_year: The invoice issue year, e.g. "2026".
        issue_month: The invoice issue month name in uppercase, e.g. "MARCH".
        invoice_id: The `id` of the invoice, as returned by `list_invoices`.
        login_customer_id: The customer ID of the manager account, required
            when customer_id is a client account (sub-account) under a
            manager (MCC) — same as `list_invoices`.

    Returns:
        A dict with `content_type` and the base64-encoded PDF in
        `content_base64` (MCP tool results must be JSON-serializable, so raw
        binary content can't be returned directly).
    """
    wanted_id = invoice_id.strip()
    # An empty id would match an invoice whose id is unset.
    if not wanted_id:
        raise ToolError("invoice_id is required.")

    invoices = _fetch_invoices(
        customer_id,
        billing_setup_id,
        issue_year,
        issue_month,
        login_customer_id,
    )
    invoice = next((i for i in invoices if i.id == wanted_id), None)
    if invoice is None:
        raise ToolError(
            f"Invoice {wanted_id} not found for billing setup "
            f"{billing_setup_id} in {_normalize_issue_month(issue_month)} "
            f"{issue_year}. Use "
            "list_invoices to see the invoice ids for that month."
        )
    if not invoice.pdf_url:
        raise ToolError(f"Invoice {wanted_id} has no PDF.")

    try:
        content = utils.download_authenticated_url(
            invoice.pdf_url, allowed_hosts=_INVOICE_PDF_HOSTS
        )
    except Exception as ex:
        raise ToolError(f"Failed to download invoice PDF: {ex}")

    return {
        "content_type": "application/pdf",
        "content_base64": base64.b64encode(content).decode("ascii"),
    }
