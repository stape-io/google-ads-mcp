#!/usr/bin/env python3

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

"""Generate a Fernet symmetric encryption key.

The key is used for GOOGLE_ADS_MCP_AUTH_STORAGE_ENCRYPTION_KEY
helm chart values:
    auth.google.storage.encryptionKeyEnabled: true
    secret.data.authStorageEncryptionKey: <generated key>

Usage:
    uv run scripts/generate_fernet_key.py
"""

import base64
import os


def generate_fernet_key() -> str:
    """Return a URL-safe base64-encoded 32-byte Fernet key."""
    return base64.urlsafe_b64encode(os.urandom(32)).decode()


if __name__ == "__main__":
    key = generate_fernet_key()
    print("Fernet key (keep secret):")
    print(key)
    print()
    print("Set in values.yaml:")
    print(f"  authStorageEncryptionKey: {key!r}")
