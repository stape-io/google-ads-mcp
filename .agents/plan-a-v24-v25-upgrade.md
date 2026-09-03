# Plan A — v24 → v25 upgrade

Branch: `upgrade/ads-api-v25` (off `main`). Standalone, no dependency on
Part B (`.agents/plan-b-invoices-billing.md`, which branches from this one).

## Context

This repo is pinned to Google Ads API v24 (`google-ads>=30.1.0`), one version
behind the upstream fork it diverged from. This is a mechanical,
behavior-preserving version bump to v25.

## Scope (every `v24` reference in the repo, confirmed via grep — nothing else touches API version)

| File | Change |
|---|---|
| `pyproject.toml` | `google-ads>=30.1.0` → `google-ads>=31.2.0,<32.0.0` (matches upstream's pin for a v25 default; the added upper bound closes a silent-drift gap — today's unbounded `>=` means a routine dependency refresh could jump the live API version with zero code change) |
| `ads_mcp/utils.py` | `from google.ads.googleads.v24.services.services.google_ads_service import GoogleAdsServiceClient` → `v25` |
| `ads_mcp/tools/core.py` | `from google.ads.googleads.v24.services.services.customer_service import CustomerServiceClient` and `.types.customer_service import ListAccessibleCustomersResponse` → `v25` |
| `ads_mcp/tools/get_resource_metadata.py` | `from google.ads.googleads.v24.services.services.google_ads_field_service import GoogleAdsFieldServiceClient` and `.types.google_ads_field_service import SearchGoogleAdsFieldsRequest` → `v25` |
| `ads_mcp/resources/discovery.py` | `url = "...$discovery/rest?version=v24"` → `version=v25` |
| `tests/utils_test.py` | `from google.ads.googleads.v24.enums.types.campaign_status import CampaignStatusEnum` and `from google.ads.googleads.v24.common.types.metrics import Metrics` → `v25` |
| `tests/resources/discovery_test.py` | `mock_get.assert_called_once_with("...version=v24", ...)` → `version=v25` |

These `v24.*` imports are type-only (used for `cast()`/direct typing, not
runtime version selection — `GoogleAdsClient()` is constructed without an
explicit `version=` and defaults to whatever the installed `google-ads`
package considers current), so this is low-risk: no runtime logic in
`search.py`, `core.py`, `get_resource_metadata.py`, or `utils.py` changes,
only import paths.

## Generated data files (must be regenerated, not hand-edited, in this order)

1. **`ads_mcp/gaql_resources.txt`** — run the existing
   `google-ads-mcp-update-gaql` entry point
   (`ads_mcp/update_references.py:update_gaql_resource_file`) against a live
   v25-capable client/credentials. This drops `campaign_lifecycle_goal` and
   `customer_lifecycle_goal` (confirmed removed in v25 per the upgrade guide,
   and confirmed present in this file today at lines 63/92) and picks up
   anything newly queryable. Requires a real `GOOGLE_ADS_DEVELOPER_TOKEN` +
   credentials — if unavailable at implementation time, fall back to manually
   deleting just those two known lines and flag that a live regen is still
   owed.
2. **`tests/smoke/golden_tools_list.json`** and **`golden_resources_list.json`**
   — run `nox -s update_smoke_golden` (→ `tests/smoke/generate_golden.py`).
   Must happen *after* step 1, because the `search` tool's description embeds
   the live contents of `gaql_resources.txt` at import time, so the golden
   snapshot of `search`'s description will otherwise go stale even though the
   tool's Python signature didn't change.

## Verification

- `nox -s lint` — formatting unaffected, should stay green.
- `nox -s tests` — full unit suite (`python -m unittest discover --buffer -s=tests -p "*_test.py"`); must pass with zero changes to test *logic*, only the v25 import swaps above.
- `nox -s smoke_tests` — boots the real server over stdio and diffs `tools/list`/`resources/list` against the regenerated golden files; this is the regression gate for tool-surface changes.
- Manual live check (not covered by mocked unit tests): call `list_accessible_customers` and one `search` query against a real/sandbox Ads account with v25-compatible credentials, to confirm the actual gRPC calls succeed — unit tests mock `get_googleads_service` entirely, so they cannot catch a genuine v25 API incompatibility.
- `nox -s llm_tests` — optional (requires `GEMINI_API_KEY`), no changes expected here since no tool names/descriptions changed meaningfully.
