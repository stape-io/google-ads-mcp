# Copyright 2026 Google LLC.
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

"""Module declaring the singleton MCP instance.

The singleton allows other modules to register their tools with the same MCP
server using `@mcp.tool` annotations, thereby 'coordinating' the bootstrapping
of the server.
"""

import os

from fastmcp import FastMCP
from fastmcp.server.auth.providers.google import GoogleProvider

from ads_mcp.auth import get_token_verifier

_CLIENT_ID = os.environ.get("GOOGLE_ADS_MCP_OAUTH_CLIENT_ID")
_CLIENT_SECRET = os.environ.get("GOOGLE_ADS_MCP_OAUTH_CLIENT_SECRET")
_REMOTE_AUTH_ENABLED = (
    os.environ.get("GOOGLE_ADS_MCP_AUTH", "").lower() == "remote"
)
_BASE_URL = os.environ.get("GOOGLE_ADS_MCP_BASE_URL", "http://localhost:8080")

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/adwords",
]

if _REMOTE_AUTH_ENABLED:
    token_verifier = get_token_verifier(
        required_scopes=SCOPES,
    )
    mcp = FastMCP("Google Ads Server", token_verifier=token_verifier)
elif _CLIENT_ID and _CLIENT_SECRET:
    auth = GoogleProvider(
        client_id=_CLIENT_ID,
        client_secret=_CLIENT_SECRET,
        base_url=_BASE_URL,
        required_scopes=SCOPES,
    )
else:
    mcp = FastMCP("Google Ads Server")
