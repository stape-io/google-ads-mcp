# MCP Server for Google Ads
[![Trust Score](https://archestra.ai/mcp-catalog/api/badge/quality/stape-io/google-ads-mcp)](https://archestra.ai/mcp-catalog/stape-io__google-ads-mcp)

An interface to the Google Ads API over MCP, with Google OAuth built in.

## Table of Contents

- [MCP Server for Google Ads](#mcp-server-for-google-ads)
  - [Table of Contents](#table-of-contents)
  - [Available tools](#available-tools)
  - [Installation](#installation)
    - [Claude Desktop](#claude-desktop)
    - [Claude Code](#claude-code)
    - [VS Code](#vs-code)
    - [GitHub Copilot](#github-copilot)
    - [Copilot CLI](#copilot-cli)
    - [Cursor](#cursor)
    - [Antigravity](#antigravity)
    - [ChatGPT](#chatgpt)
    - [Other MCP clients](#other-mcp-clients)
    - [Troubleshooting](#troubleshooting)
  - [Local Development](#local-development)
    - [Setup](#setup)
    - [Running locally](#running-locally)
    - [Testing](#testing)
    - [Linting and formatting](#linting-and-formatting)
  - [Open Source](#open-source)

## Available tools

All tools are read-only. The typical flow for a query is: `list_accessible_customers` to find an account, `get_resource_metadata` to look up valid fields for a resource, then `search` to run the actual query.

### `list_accessible_customers`

Returns the customer IDs directly accessible by the authenticated user. No arguments. Use this first when the user hasn't given you a customer ID — most other tools require one.

### `search`

Runs a query against the Google Ads API's `search` method (GAQL — Google Ads Query Language) and returns the matching rows.

| Argument | Required | Description |
| --- | --- | --- |
| `customer_id` | yes | Plain numeric account ID (e.g. `1234567890`, no dashes) |
| `fields` | yes | Fields to select, e.g. `["campaign.id", "campaign.name", "metrics.clicks"]` |
| `resource` | yes | The GAQL resource to query, e.g. `campaign`, `ad_group`, `billing_setup` |
| `conditions` | no | List of `WHERE` conditions, combined with `AND` |
| `orderings` | no | List of `ORDER BY` clauses |
| `limit` | no | Max number of rows to return |
| `login_customer_id` | no | Manager (MCC) account ID — required when `customer_id` is a client account under a manager |

The tool's description (fed to the model) is generated at runtime from `ads_mcp/gaql_resources.txt` and includes the full list of valid resources for the pinned API version, plus hints on date formats, pagination limits, and troubleshooting `login_customer_id` permission errors — see `ads_mcp/tools/search.py` for the exact text.

### `get_resource_metadata`

Given a resource name (e.g. `campaign`, `ad_group`), returns which fields on it are `selectable`, `filterable`, and `sortable` — including compatible `metrics.*` and `segments.*` fields. Field names aren't guessable from the API docs alone; this is the tool that's meant to be called before building a `search` query against a resource you haven't queried before.

| Argument | Required | Description |
| --- | --- | --- |
| `resource_name` | yes | The Google Ads resource name, e.g. `campaign` |

### `list_invoices`

Lists invoices issued for a given billing setup and month. Requires the account to have monthly invoicing enabled — most advertisers are on automatic payments and won't have any invoices to list.

| Argument | Required | Description |
| --- | --- | --- |
| `customer_id` | yes | Plain numeric ID of the serving customer account |
| `billing_setup_id` | yes | Numeric billing setup ID — discoverable via `search`: `SELECT billing_setup.id FROM billing_setup` |
| `issue_year` | yes | Invoice issue year, e.g. `"2026"` (invoices before 2019 aren't retrievable) |
| `issue_month` | yes | Invoice issue month name, e.g. `"march"` |
| `login_customer_id` | no | Manager (MCC) account ID — required when `customer_id` is a client account under a manager, same rule as `search` |

### `download_invoice_pdf`

Downloads one invoice's PDF, given the `pdf_url` returned by `list_invoices`.

| Argument | Required | Description |
| --- | --- | --- |
| `pdf_url` | yes | The `pdf_url` field from a `list_invoices` result |

Returns a JSON object (`content_type`, `content_base64`) rather than raw bytes, since MCP tool results must be JSON-serializable.

### Resources

A handful of read-only MCP resources give the model reference documentation instead of requiring a tool call:

| Resource URI | Content |
| --- | --- |
| `resource://discovery-document` | The Google Ads API discovery document (JSON) — resources, methods, and schemas at a high level |
| `resource://metrics` | Official docs listing every queryable metric |
| `resource://segments` | Official docs listing every queryable segment |
| `resource://release-notes` | Official Google Ads API release notes (new features, deprecations, breaking changes) |

These are fetched live from `developers.google.com`/`googleads.googleapis.com` on each read, not bundled into the repo.

## Installation

This server is a remote, HTTP-based MCP endpoint at `https://mcp-google-ads.stape.io/mcp`. Clients whose MCP support completes the Google OAuth flow natively (Claude Code, VS Code, Copilot CLI, Cursor, ChatGPT) connect straight to that URL; the rest need the [`mcp-remote`](https://github.com/geelen/mcp-remote#readme) bridge, a small proxy that lets stdio-only clients talk to a remote HTTP MCP server.

Restart the client after changing its config. A browser window opens for the Google OAuth flow the first time a tool is used — complete it to grant access to your Google Ads account.

### Claude Desktop

<details>
<summary>⬇️ Click to expand ⬇️</summary>

Open Claude Desktop and navigate to Settings -> Developer -> Edit Config. Add this to the configuration file:

```json
{
  "mcpServers": {
    "google-ads-mcp": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://mcp-google-ads.stape.io/mcp"
      ]
    }
  }
}
```

</details>

### Claude Code

<details>
<summary>⬇️ Click to expand ⬇️</summary>

Claude Code speaks HTTP directly, including the OAuth handshake, so no bridge is needed:

```bash
claude mcp add --transport http google-ads-mcp https://mcp-google-ads.stape.io/mcp
```

A browser window opens for the Google OAuth flow the first time a tool is used. This writes the server entry into `.mcp.json` / your Claude Code MCP config. Run `/mcp` inside Claude Code to confirm it connected.

</details>

### VS Code

<details>
<summary>⬇️ Click to expand ⬇️</summary>

VS Code's MCP client supports HTTP servers and their OAuth flow natively, no `mcp-remote` needed. Add this to `.vscode/mcp.json`:

```json
{
  "servers": {
    "google-ads-mcp": {
      "type": "http",
      "url": "https://mcp-google-ads.stape.io/mcp"
    }
  }
}
```

</details>

### GitHub Copilot

<details>
<summary>⬇️ Click to expand ⬇️</summary>

GitHub Copilot Chat in VS Code uses VS Code's own MCP client, so it reads the same `.vscode/mcp.json` file — see [VS Code](#vs-code) above. No separate configuration is needed.

</details>

### Copilot CLI

<details>
<summary>⬇️ Click to expand ⬇️</summary>

Copilot CLI also completes OAuth natively for remote HTTP servers, no bridge needed. Add this to `~/.copilot/mcp-config.json`:

```json
{
  "mcpServers": {
    "google-ads-mcp": {
      "type": "http",
      "url": "https://mcp-google-ads.stape.io/mcp"
    }
  }
}
```

See [GitHub's docs](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers) for the equivalent `copilot mcp add` subcommand.

</details>

### Cursor

<details>
<summary>⬇️ Click to expand ⬇️</summary>

Cursor speaks HTTP directly, no `mcp-remote` needed. Add this to `.cursor/mcp.json` (project-level) or `~/.cursor/mcp.json` (global — Settings → MCP → Add new global MCP server):

```json
{
  "mcpServers": {
    "google-ads-mcp": {
      "url": "https://mcp-google-ads.stape.io/mcp"
    }
  }
}
```

</details>

### Antigravity

<details>
<summary>⬇️ Click to expand ⬇️</summary>

Antigravity's own OAuth support for remote HTTP servers doesn't reliably reach a token to the server yet ([antigravity-cli#25](https://github.com/google-antigravity/antigravity-cli/issues/25)), so use `mcp-remote` here too, the same way Claude Desktop does. Add this to `~/.gemini/config/mcp_config.json` (global) or `.agents/mcp_config.json` (workspace-local) — accessible from the editor's agent panel via **… → MCP Servers → Manage MCP Servers → View raw config**:

```json
{
  "mcpServers": {
    "google-ads-mcp": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://mcp-google-ads.stape.io/mcp"
      ]
    }
  }
}
```

</details>

### ChatGPT

<details>
<summary>⬇️ Click to expand ⬇️</summary>

1. In ChatGPT, enable Developer mode: Settings → Apps & Connectors → Advanced settings → Developer mode.
2. Go to Settings → Connectors → Create, and set the server URL to `https://mcp-google-ads.stape.io/mcp`.
3. Set Authentication to **OAuth** and complete the Google login in the browser window that opens.

ChatGPT only reaches servers over the public internet, it can't spawn a local process — so there's no local option here, only the hosted server.

</details>

### Other MCP clients

<details>
<summary>⬇️ Click to expand ⬇️</summary>

Any other MCP-compatible client that expects a stdio-style `command`/`args` config can use the same `mcp-remote` block:

```json
{
  "mcpServers": {
    "google-ads-mcp": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://mcp-google-ads.stape.io/mcp"
      ]
    }
  }
}
```

</details>

### Troubleshooting

**MCP Server Name Length Limit**

Some MCP clients (like Cursor AI) have a 60-character limit for the combined MCP server name + tool name length. If you use a longer server name in your configuration (e.g., `google-ads-mcp-your-additional-long-name`), some tools may be filtered out.

To avoid this issue:
- Use shorter server names in your MCP configuration (e.g., `google-ads-mcp`)

**Clearing MCP Cache**

[mcp-remote](https://github.com/geelen/mcp-remote#readme) stores all the credential information inside `~/.mcp-auth` (or wherever your `MCP_REMOTE_CONFIG_DIR` points to). If you're having persistent issues, try running:

```bash
rm -rf ~/.mcp-auth
```

Then restart your MCP client.

## Local Development

This server runs on Python 3.10+ and [`uv`](https://docs.astral.sh/uv/) for dependency management, with [`nox`](https://nox.thea.codes/) driving lint/test sessions.

### Setup

```bash
git clone https://github.com/stape-io/google-ads-mcp
cd google-ads-mcp
cp example.env .env   # fill in your own values, see below
uv sync --group dev
```

Running locally against the real Google Ads API needs two things in `.env`:
- `GOOGLE_ADS_DEVELOPER_TOKEN` — a developer token for your Google Ads manager account.
- Google credentials the client library can pick up via [Application Default Credentials](https://google-auth.readthedocs.io/en/master/reference/google.auth.html#google.auth.default), authorized for the `https://www.googleapis.com/auth/adwords` scope.

See `example.env` for the full list of variables, including the ones needed to run the server as a hosted OAuth-fronted deployment rather than stdio.

### Running locally

```bash
uv run google-ads-mcp
```

Point your MCP client at the local checkout instead of the hosted URL:

```json
{
  "mcpServers": {
    "google-ads-mcp-local": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/google-ads-mcp", "google-ads-mcp"]
    }
  }
}
```

### Testing

```bash
nox -s tests         # unit tests, across Python 3.10-3.13
nox -s smoke_tests    # boots the real server over stdio, diffs tools/list & resources/list against golden files
nox -s llm_tests      # tool-selection tests against Gemini, needs GEMINI_API_KEY
```

Unit tests mock the Google Ads client entirely, so they can't catch a real API incompatibility — smoke tests catch tool-surface regressions (renamed/removed tools, changed schemas), but a live account is still the only way to verify an actual gRPC call succeeds.

If you change a tool's schema or add/remove a tool, regenerate the smoke-test golden files:

```bash
nox -s update_smoke_golden
```

### Linting and formatting

```bash
nox -s format   # applies black formatting
nox -s lint     # checks formatting only, fails on drift
```

## Open Source

The **MCP Server for Google Ads** is a fork of [Google's `google-ads-mcp`](https://github.com/googleads/google-ads-mcp), maintained by [Stape Team](https://stape.io/) under the Apache 2.0 license. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for contribution guidelines.
