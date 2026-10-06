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

# importing from server to ensure all tools are registered with the MCP instance
from ads_mcp.server import (
    mcp,
)
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

app = mcp.http_app(stateless_http=True)


def healthz(_: Request) -> Response:
    return JSONResponse(content={"status": "ok"})


app.add_route("/healthz", healthz, methods=["GET"])
