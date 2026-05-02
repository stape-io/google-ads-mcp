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

"""Entry point for the MCP server."""

import os

from ads_mcp.coordinator import mcp
from ads_mcp.resources import (
    discovery,  # noqa: F401
    metrics,  # noqa: F401
    release_notes,  # noqa: F401
    segments,  # noqa: F401
)

# The following imports are necessary to register the tools with the `mcp`
# object, even though they are not directly used in this file.
# The `# noqa: F401` comment tells the linter to ignore the "unused import"
# warning.
from ads_mcp.tools import core, get_resource_metadata, search  # noqa: F401


def run_server() -> None:
    _CLIENT_ID = os.environ.get("GOOGLE_ADS_MCP_OAUTH_CLIENT_ID")
    _CLIENT_SECRET = os.environ.get("GOOGLE_ADS_MCP_OAUTH_CLIENT_SECRET")
    port = int(os.environ.get("PORT", "8080"))

    if _CLIENT_ID and _CLIENT_SECRET:
        mcp.run(transport="streamable-http", port=port, host="0.0.0.0")
    else:
        mcp.run()


if __name__ == "__main__":
    run_server()
