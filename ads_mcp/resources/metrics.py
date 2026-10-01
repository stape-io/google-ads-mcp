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

"""Metrics resource."""

import httpx

from ads_mcp.coordinator import mcp
from ads_mcp.utils import RESOURCE_TTL_SECONDS, ttl_cache


@mcp.resource(
    uri="resource://metrics",
    mime_type="text/html",
)
@ttl_cache(RESOURCE_TTL_SECONDS)
def get_metrics() -> str:
    """Retrieve the Google Ads API metrics documentation.

    Provides the official documentation for metrics in the Google Ads API,
    listing all available metrics that can be queried to analyze performance
    data.

    Use this resource to identify which metrics are available and how they are
    calculated.

    Returns:
        str: The metrics documentation in HTML format.
    """
    url = "https://developers.google.com/google-ads/api/fields/latest/metrics"
    # These docs pages are multi-MB; httpx's 5s default is not enough.
    response = httpx.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        follow_redirects=True,
        timeout=30.0,
    )
    response.raise_for_status()
    return response.text
