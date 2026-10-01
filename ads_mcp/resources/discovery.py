# Copyright 2026 Google LLC.
# Modified by Stape, 2026
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

"""Discovery document resource."""

import httpx

from ads_mcp.coordinator import mcp
from ads_mcp.utils import RESOURCE_TTL_SECONDS, ttl_cache


@mcp.resource(
    uri="resource://discovery-document",
    mime_type="application/json",
)
@ttl_cache(RESOURCE_TTL_SECONDS)
def get_discovery_document() -> str:
    """Retrieve the Google Ads API discovery document.

    Provides the discovery document for the Google Ads API, which
    describes the API surface, including resources, methods, and schemas.

    Use this resource to get a high-level overview of the API surface or to find
    available resources. However, for finding specific fields, you MUST use the
    `get_resource_metadata` tool instead, as it provides more targeted and
    up-to-date information for queries.

    Returns:
        str: The discovery document in JSON format.
    """
    url = "https://googleads.googleapis.com/$discovery/rest?version=v25"

    # These docs pages are multi-MB; httpx's 5s default is not enough.
    response = httpx.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        follow_redirects=True,
        timeout=30.0,
    )
    response.raise_for_status()
    return response.text
