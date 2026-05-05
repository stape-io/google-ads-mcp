#!/usr/bin/env python3
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
