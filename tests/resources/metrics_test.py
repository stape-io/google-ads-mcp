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

"""Tests for the metrics resource."""

import unittest
import urllib.request
from unittest import mock

from ads_mcp.resources import metrics


class MetricsTest(unittest.TestCase):
    @mock.patch("ads_mcp.resources.metrics.httpx.get")
    def test_get_metrics(self, mock_get):
        # Setup mock response
        mock_response = mock.MagicMock()
        mock_response.text = "Mock metrics content"
        mock_get.return_value = mock_response
        mock_get.return_value = mock_response

        # Call function
        result = metrics.get_metrics()

        # Assertions
        self.assertEqual(result, "Mock metrics content")

        # Verify httpx.get was called correctly
        mock_get.assert_called_once_with(
            "https://developers.google.com/google-ads/api/fields/latest/metrics",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        mock_response.raise_for_status.assert_called_once()
