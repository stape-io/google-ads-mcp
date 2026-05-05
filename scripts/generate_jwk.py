#!/usr/bin/env python3
"""Generate an Ed25519 JWK key pair using joserfc.

Usage:
    pip install joserfc
    python scripts/generate_jwk.py
"""

import json

from joserfc import jwk
from joserfc._rfc7517.models import AsymmetricKey, SymmetricKey
from joserfc.jwk import OctKey


def save_asymmetric_key_to_file(key: AsymmetricKey) -> None:
    if key.kid is None:
        key.ensure_kid()
    with open(f"{key.kid}_private.json", "w+") as f:
        json.dump(key.as_dict(private=True), f)

    with open(f"{key.kid}_public.json", "w+") as f:
        json.dump(key.as_dict(private=False), f)

def save_symmetric_key_to_file(key: SymmetricKey) -> None:
    if key.kid is None:
        key.ensure_kid()
    with open(f"{key.kid}.json", "w+") as f:
        json.dump(key.as_dict(), f)

def save_key_to_file(key: jwk.Key) -> None:
    if isinstance(key, AsymmetricKey):
        save_asymmetric_key_to_file(key)
    elif isinstance(key, OctKey):
        save_symmetric_key_to_file(key)
    else:
        raise ValueError("Unsupported key type")

if __name__ == "__main__":
    key = jwk.generate_key(
        key_type="OKP",
        crv_or_size="Ed25519",
        auto_kid=True,
        parameters={"use": "sig",}
    )
    save_key_to_file(key)
