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
  - [Useful resources](#useful-resources)
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

This server is a remote, HTTP-based MCP endpoint at `https://mcp-google-ads.stape.io/mcp`, with Google OAuth built in. Clients that complete the OAuth flow themselves (Claude Desktop, Claude Code, VS Code, Copilot CLI, Cursor, ChatGPT) connect straight to that URL; the rest (Antigravity, stdio-only clients) reach it through [`mcp-remote`](https://github.com/geelen/mcp-remote#readme), a small bridge to remote HTTP MCP servers.

Each client signs you in with Google the first time it connects, to grant access to your Google Ads data. Restart the client after changing its config.

### Claude Desktop

<details>
<summary>⬇️ Click to expand ⬇️</summary>

**Custom connector (recommended).**

1. Go to **Customize → Connectors → Add custom connector**. On Team and Enterprise plans, an Owner adds it under **Organization settings → Connectors → Add → Custom** instead, and each member then selects **Connect** on it under **Customize → Connectors** and signs in with their own Google account.
2. Set a name (e.g. `google-ads-mcp`) and the URL to `https://mcp-google-ads.stape.io/mcp`. If the dialog asks how to authenticate, choose **Sign in now**; if it asks for an OAuth client, choose **Register automatically**.
3. Select **Add**, then **Connect**, and sign in with Google.

The connector also works on claude.ai.

**`mcp-remote`.** To configure it through `claude_desktop_config.json` (Settings → Developer → Edit Config) instead:

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

Claude Code speaks HTTP directly, including the OAuth flow, so no bridge is needed:

```bash
claude mcp add --transport http google-ads-mcp https://mcp-google-ads.stape.io/mcp
```

Then run `/mcp` inside Claude Code (or `claude mcp login google-ads-mcp` from the shell) and sign in with Google. `claude mcp list` shows whether it connected.

This adds the server to the current project only. Add `--scope user` to use it in every project, or `--scope project` to write it to the project's `.mcp.json` so teammates get it too (each still signs in with their own Google account).

</details>

### VS Code

<details>
<summary>⬇️ Click to expand ⬇️</summary>

VS Code's MCP client supports HTTP servers and their OAuth flow natively, no `mcp-remote` needed. Add this to `.vscode/mcp.json` (this workspace) or to the file **MCP: Open User Configuration** opens (every workspace):

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

VS Code asks you to sign in with Google when the server first starts.

</details>

### GitHub Copilot

<details>
<summary>⬇️ Click to expand ⬇️</summary>

GitHub Copilot Chat in VS Code uses VS Code's own MCP client, so it reads the same MCP configuration — see [VS Code](#vs-code) above. No separate configuration is needed.

</details>

### Copilot CLI

<details>
<summary>⬇️ Click to expand ⬇️</summary>

Copilot CLI completes OAuth natively for remote HTTP servers:

```bash
copilot mcp add --transport http google-ads-mcp https://mcp-google-ads.stape.io/mcp
```

This writes the server entry into `~/.copilot/mcp-config.json`; sign in with Google when Copilot CLI prompts you. Run `copilot mcp get google-ads-mcp` to check it. Inside an interactive session, `/mcp add` does the same through a form. See [GitHub's docs](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers#using-the-copilot-mcp-add-subcommand) for more.

</details>

### Cursor

<details>
<summary>⬇️ Click to expand ⬇️</summary>

Cursor speaks HTTP directly, including the OAuth flow, no `mcp-remote` needed. Add this to `.cursor/mcp.json` (this project) or `~/.cursor/mcp.json` (every project):

```json
{
  "mcpServers": {
    "google-ads-mcp": {
      "url": "https://mcp-google-ads.stape.io/mcp"
    }
  }
}
```

Then sign in with Google from the server's entry under **Customize** in Cursor's sidebar.

</details>

### Antigravity

<details>
<summary>⬇️ Click to expand ⬇️</summary>

Antigravity's OAuth support for remote HTTP servers doesn't get a token to the server yet ([antigravity-cli#25](https://github.com/google-antigravity/antigravity-cli/issues/25)), so use `mcp-remote` here. Add this to `~/.gemini/config/mcp_config.json`, which the Antigravity editor and CLI share. In the editor, open it from the agent panel via **… → MCP Servers → Manage MCP Servers → View raw config**:

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

Or, from the Antigravity CLI:

```bash
agy mcp add google-ads-mcp -- npx -y mcp-remote https://mcp-google-ads.stape.io/mcp
```

`mcp-remote` opens the Google sign-in in your browser the first time it connects.

</details>

### ChatGPT

<details>
<summary>⬇️ Click to expand ⬇️</summary>

1. In ChatGPT on the web, go to [Plugins](https://chatgpt.com/plugins), select **+**, then **Add custom MCP server**.
2. Enter a name (e.g. `google-ads-mcp`) and, under **Connection**, set the server URL to `https://mcp-google-ads.stape.io/mcp`.
3. Set authentication to **OAuth**. The server supports Dynamic Client Registration, so no client ID or secret is needed.
4. Confirm the risk warning (**I understand and want to continue**), then select **Create as a plugin**.
5. Install the plugin from your personal plugins, sign in with Google, and pick it with `@` in the prompt box.

Workspace admins can restrict custom MCP servers. See [OpenAI's docs](https://developers.openai.com/api/docs/guides/custom-mcp-server) for more.

</details>

### Other MCP clients

<details>
<summary>⬇️ Click to expand ⬇️</summary>

If your client supports remote HTTP MCP servers with OAuth, point it at `https://mcp-google-ads.stape.io/mcp`, as in the [Cursor](#cursor) config. Otherwise, use `mcp-remote`:

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

If you're connecting through [`mcp-remote`](https://github.com/geelen/mcp-remote#readme) (Antigravity, Claude Desktop configured that way, or other clients using the `mcp-remote` block), it stores all the credential information inside `~/.mcp-auth` (or wherever your `MCP_REMOTE_CONFIG_DIR` points to). If you're having persistent issues, try running:

```bash
rm -rf ~/.mcp-auth
```

Then restart your MCP client.

## Local Development

This server runs on Python 3.11+ and [`uv`](https://docs.astral.sh/uv/) for dependency management, with [`nox`](https://nox.thea.codes/) driving lint/test sessions.

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
nox -s tests         # unit tests, across Python 3.11-3.14
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

## Useful resources

- [Step-by-step guide: MCP Server for Google Ads](https://stape.io/blog/mcp-server-for-google-ads)

## Open Source

The **MCP Server for Google Ads** is a fork of [Google's `google-ads-mcp`](https://github.com/googleads/google-ads-mcp), maintained by [Stape Team](https://stape.io/) under the Apache 2.0 license. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for contribution guidelines.
