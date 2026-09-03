# Plan B — Invoice/billing tools

Branch: `feature/invoice-billing-tools` (off `upgrade/ads-api-v25`, so this
is built against v25 from the start). Standalone from Part A
(`.agents/plan-a-v24-v25-upgrade.md`) other than that branch dependency.

## Context

An MCP user requested access to monthly billing documents/invoices for
accounting/reconciliation workflows. Google Ads API exposes this via a
dedicated `InvoiceService.ListInvoices` RPC — not reachable through the
existing generic `search` tool, since invoices are not a GAQL resource.

Requires the target account to have **monthly invoicing enabled** — most
advertisers are on automatic (credit-card) payments and won't have any
invoices at all. This is a real limitation of the feature, not a bug to work
around.

## Design (confirmed with the user)

- **Two tools**, not one: `list_invoices` (metadata only, cheap per month) and
  `download_invoice_pdf` (fetches one invoice's PDF on demand). Keeps
  browsing-by-month cheap and PDF fetch opt-in.
- **`billing_setup` input**: caller passes a plain numeric `billing_setup_id`
  (consistent with the existing `customer_id`/`login_customer_id` "plain
  numeric string" convention in `search.py`'s hints); the tool builds the
  full resource name internally via
  `utils.get_googleads_service("GoogleAdsService").billing_setup_path(customer_id, billing_setup_id)`.

## New file: `ads_mcp/tools/invoices.py`

Follows `core.py`'s pattern (direct service-client RPC call via
`utils.get_googleads_service(...)`), not `search.py`'s GAQL-builder pattern,
since `InvoiceService` isn't a GAQL resource.

```python
@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def list_invoices(
    customer_id: str,
    billing_setup_id: str,
    issue_year: str,
    issue_month: str,
) -> list[dict[str, Any]]:
    """Lists invoices issued for a given billing setup and month.

    Requires the account to have monthly invoicing enabled — most advertisers
    are on automatic payments and will get an empty/error result. `customer_id`
    must be a serving account. `billing_setup_id` is discoverable via the
    `search` tool: SELECT billing_setup.id FROM billing_setup.
    `issue_month` is the month name in uppercase (e.g. "MARCH").
    Invoices before 2019-01 are not retrievable.
    """
    ga_service = utils.get_googleads_service("GoogleAdsService")
    billing_setup = ga_service.billing_setup_path(customer_id, billing_setup_id)

    invoice_service = utils.get_googleads_service("InvoiceService")
    try:
        response = invoice_service.list_invoices(
            customer_id=customer_id,
            billing_setup=billing_setup,
            issue_year=issue_year,
            issue_month=issue_month.upper(),
        )
    except GoogleAdsException as ex:
        # same error-shaping as search.py's search()
        ...
    return [proto.Message.to_dict(invoice) for invoice in response.invoices]


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def download_invoice_pdf(pdf_url: str) -> dict[str, Any]:
    """Downloads one invoice's PDF, given the `pdf_url` returned by list_invoices.

    Returns base64-encoded PDF content, since MCP tool results must be JSON.
    """
    content = utils.download_authenticated_url(pdf_url)
    return {
        "content_type": "application/pdf",
        "content_base64": base64.b64encode(content).decode("ascii"),
    }
```

- Error handling in `list_invoices` reuses the exact `GoogleAdsException` →
  `ToolError` shaping already in `search.py` (request ID + per-error
  messages) — no new error-handling pattern invented.
- Output formatting reuses `proto.Message.to_dict` the same way
  `utils.format_output_value` already does for single messages — no new
  per-field allowlist/formatting code, full invoice data (id, resource_name,
  `pdf_url`, dates, amount fields, account-budget summaries) flows through
  generically, same philosophy as `search`.
- `download_invoice_pdf` takes `pdf_url` directly (already returned by
  `list_invoices`) rather than re-deriving it, avoiding a second lookup RPC —
  there is no `GetInvoice` singular-fetch method, only `ListInvoices`.

## New utility: `ads_mcp/utils.py`

Add one small function reusing the credentials machinery that already exists
(`_create_credentials()`), since `pdf_url` requires the same OAuth bearer
token as the gRPC calls, fetched over plain HTTPS (not gRPC) — same shape as
`discovery.py`/`metrics.py`'s existing raw `httpx.get` calls elsewhere in this
codebase:

```python
def download_authenticated_url(url: str) -> bytes:
    """Downloads a URL that requires the same Ads OAuth credentials as gRPC calls."""
    credentials = _create_credentials()
    credentials.refresh(google.auth.transport.requests.Request())
    response = httpx.get(url, headers={"Authorization": f"Bearer {credentials.token}"})
    response.raise_for_status()
    return response.content
```

(`httpx` is already a dependency; `google.auth.transport.requests` ships with
`google-auth`, already a transitive dep via `google-ads`. No new dependency —
stdlib/already-installed only.)

## Wiring

- `ads_mcp/server.py`: add `invoices` to the existing tool-import tuple:
  `from ads_mcp.tools import core, get_resource_metadata, search, invoices  # noqa: F401`
  — this one line is what registers both new tools with the running server.

## Tests (new + regenerated, mirroring existing patterns exactly)

**New file `tests/tools/invoices_test.py`** (same `unittest.TestCase` +
`unittest.mock.patch`/`MagicMock` style as `tests/tools/search_test.py` and
`tests/tools/get_resource_metadata_test.py` — no new test framework/fixtures):
- `test_list_invoices_basic` — mock `ads_mcp.utils.get_googleads_service` to
  return a `MagicMock()`; assert `billing_setup_path(customer_id,
  billing_setup_id)` is called and its result is passed as `billing_setup`;
  assert `issue_month` is uppercased before the call; assert the returned list
  matches formatted mock `Invoice` objects.
- `test_list_invoices_google_ads_exception` — same shape as
  `search_test.py::test_search_google_ads_exception`, asserting `ToolError`
  with request ID + message.
- `test_download_invoice_pdf_basic` — mock `ads_mcp.utils.download_authenticated_url`
  to return known bytes; assert `content_base64` round-trips correctly and
  `content_type` is `"application/pdf"`.
- `test_download_invoice_pdf_http_error` — mock the helper to raise
  `httpx.HTTPStatusError`; assert it propagates as a `ToolError` (or a clear
  error), not an unhandled exception.

**`tests/utils_test.py` addition:**
- `test_download_authenticated_url` — mock `httpx.get` and the credentials
  path, assert the `Authorization: Bearer <token>` header is set and
  `response.content` is returned; assert `raise_for_status` is called (mirrors
  how `discovery_test.py` already asserts on `httpx.get` call args).

**Regenerate `tests/smoke/golden_tools_list.json`** via `nox -s
update_smoke_golden` once both tools are registered — required, the smoke
test does an exact-string diff and will otherwise fail on the two new tool
schemas.

**Optional (not required for `nox -s tests`/`smoke_tests` to pass, but adds
LLM-selection coverage):** one or two new entries in
`tests/smoke/llm_cases.json` (e.g. a "list my invoices for March 2026 for
account X" prompt expecting `list_invoices`), exercised only when
`GEMINI_API_KEY` is set via `nox -s llm_tests`.

## Verification

- `nox -s lint`, `nox -s tests`, `nox -s smoke_tests` all green, including the
  full Part A suite still passing (no regressions from B).
- Manual live check against a real account **with monthly invoicing enabled**
  (this is the main untestable-in-CI assumption — most sandbox/test accounts
  won't have it): call `list_invoices` for a known past month, confirm
  `pdf_url` is present, then call `download_invoice_pdf` and confirm the
  returned base64 decodes to a valid PDF (`%PDF-` header bytes).
- Manual check on an account *without* monthly invoicing enabled, to see what
  error actually surfaces (docs suggest `ACTION_NOT_PERMITTED` or similar) and
  confirm it comes through as a readable `ToolError` rather than a raw
  traceback — no special-casing is planned beyond the existing generic
  `GoogleAdsException` handler unless this check turns up something the
  generic handler mishandles.
