# importing from server to ensure all tools are registered with the MCP instance
from ads_mcp.server import (
    mcp,
)

app = mcp.http_app()
