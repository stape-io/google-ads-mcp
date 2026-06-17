# MCP Server for Google Ads

This is a server that supports remote MCP connections, with Google OAuth built-in and provides an interface to the Google Ads  API.

## Access the remote MCP server from Claude Desktop

Open Claude Desktop and navigate to Settings -> Developer -> Edit Config. This opens the configuration file that controls which MCP servers Claude can access.

Replace the content with the following configuration. Once you restart Claude Desktop, a browser window will open showing your OAuth login page. Complete the authentication flow to grant Claude access to your MCP server. After you grant access, the tools will become available for you to use.

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

Some MCP clients (like Cursor AI) have a 60-characterlimit for the combined MCP server name + tool namelength. If you use a longer server name in yourconfiguration (e.g.,`google-ads-mcp-your-additional-long-name`), some toolsmay be filtered out.
To avoid this issue:
- Use shorter server names in your MCP configuration (eg., `google-ads-mcp`)

**Clearing MCP Cache**

[mcp-remote](https://github.com/geelen/mcp-remote#readme) stores all the credential information inside ~/.mcp-auth(or wherever your MCP_REMOTE_CONFIG_DIR points to). Ifyou're having persistent issues, try running:
You can run rm -rf ~/.mcp-auth to clear any locallystored state and tokens.

```bash
rm -rf ~/.mcp-auth
```

to clear any locally stored state and tokens.
rm -rf ~/.mcp-auth
Then restarting your MCP client.
