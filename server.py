# importing from server to ensure all tools are registered with the MCP instance
from ads_mcp.server import (
    mcp,
)
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

app = mcp.http_app()


def healthz(_: Request) -> Response:
    return JSONResponse(content={"status": "ok"})

app.add_route("/healthz", healthz, methods=["GET"])
