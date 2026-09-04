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

| Tool | What it does |
| --- | --- |
| `list_accessible_customers` | Lists the customer account IDs directly accessible by the authenticated user |
| `search` | Runs a GAQL query against the Google Ads API |
| `get_resource_metadata` | Returns the selectable, filterable, and sortable fields for a Google Ads resource |

Plus a handful of read-only resources (discovery document, metrics, segments, release notes) that give the model reference documentation for building queries.

## Installation

This server is a remote, HTTP-based MCP endpoint at `https://mcp-google-ads.stape.io/mcp`. Most clients reach it through [`mcp-remote`](https://github.com/geelen/mcp-remote#readme), a small bridge that lets stdio-only clients talk to a remote HTTP MCP server; a few clients (VS Code, Cursor) speak HTTP directly.

Restart the client after changing its config. A browser window opens for the Google OAuth flow the first time a tool is used — complete it to grant access to your Google Ads account.

### Claude Desktop

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

### Claude Code

```bash
claude mcp add google-ads-mcp -- npx -y mcp-remote https://mcp-google-ads.stape.io/mcp
```

This writes the server entry into `.mcp.json` / your Claude Code MCP config. Run `/mcp` inside Claude Code to confirm it connected.

### VS Code

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

### GitHub Copilot

GitHub Copilot Chat in VS Code uses VS Code's own MCP client, so it reads the same `.vscode/mcp.json` file — see [VS Code](#vs-code) above. No separate configuration is needed.

### Copilot CLI

Copilot CLI needs the `mcp-remote` bridge too. Add this to `~/.copilot/mcp-config.json`:

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

See [GitHub's docs](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers) for the equivalent `copilot mcp add` subcommand.

### Cursor

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

### ChatGPT

1. In ChatGPT, enable Developer mode: Settings → Apps & Connectors → Advanced settings → Developer mode.
2. Go to Settings → Connectors → Create, and set the server URL to `https://mcp-google-ads.stape.io/mcp`.
3. Set Authentication to **OAuth** and complete the Google login in the browser window that opens.

ChatGPT only reaches servers over the public internet, it can't spawn a local process — so there's no local option here, only the hosted server.

### Other MCP clients

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
