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

"""Tests for the release_notes resource."""

import unittest
from unittest import mock

from ads_mcp import utils
from ads_mcp.resources import release_notes


class ReleaseNotesTest(unittest.TestCase):
    def setUp(self):
        release_notes.get_release_notes.cache_clear()

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
            follow_redirects=True,
            timeout=30.0,
        )
        mock_response.raise_for_status.assert_called_once()

    @mock.patch("ads_mcp.resources.release_notes.httpx.get")
    def test_second_read_does_not_refetch(self, mock_get):
        mock_get.return_value = mock.MagicMock(
            text="Mock release notes content"
        )

        release_notes.get_release_notes()
        release_notes.get_release_notes()

        mock_get.assert_called_once()

    @mock.patch("ads_mcp.utils.time.monotonic")
    @mock.patch("ads_mcp.resources.release_notes.httpx.get")
    def test_read_after_ttl_refetches(self, mock_get, mock_monotonic):
        mock_get.side_effect = [
            mock.MagicMock(text="old"),
            mock.MagicMock(text="new"),
        ]

        mock_monotonic.return_value = 1000.0
        self.assertEqual(release_notes.get_release_notes(), "old")
        mock_monotonic.return_value = 1000.0 + utils.RESOURCE_TTL_SECONDS - 1
        self.assertEqual(release_notes.get_release_notes(), "old")
        mock_monotonic.return_value = 1000.0 + utils.RESOURCE_TTL_SECONDS
        self.assertEqual(release_notes.get_release_notes(), "new")
        self.assertEqual(mock_get.call_count, 2)
