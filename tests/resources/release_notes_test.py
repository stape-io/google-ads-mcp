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

"""Tests for the release_notes resource."""

import unittest
import urllib.request
from unittest import mock

from ads_mcp.resources import release_notes


class ReleaseNotesTest(unittest.TestCase):
    @mock.patch("ads_mcp.resources.release_notes.httpx.get")
    def test_get_release_notes(self, mock_get):
        # Setup mock response
        mock_response = mock.MagicMock()
        mock_response.text = "Mock release notes content"
        mock_get.return_value = mock_response

        # Call function
        result = release_notes.get_release_notes()

        # Assertions
        self.assertEqual(result, "Mock release notes content")

        # Verify httpx.get was called correctly
        mock_get.assert_called_once_with(
            "https://developers.google.com/google-ads/api/docs/release-notes",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        mock_response.raise_for_status.assert_called_once()
