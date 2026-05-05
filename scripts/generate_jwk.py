#!/usr/bin/env python3
"""Generate an Ed25519 JWK key pair using joserfc.

The generated private key is used for GOOGLE_ADS_MCP_AUTH_JWT_PROVIDER_PRIVATE_KEYS
(auth.remote.jwtProvider.enabled: true). The server uses the private key to sign
short-lived JWTs that authenticate outbound token-verification requests.

The key format is OKP (Octet Key Pair) as defined in RFC 8037:
  - kty: "OKP"  — key type
  - crv: "Ed25519" — elliptic curve
  - x   — public key (base64url-encoded 32 bytes)
  - d   — private key scalar (base64url-encoded 32 bytes, keep secret)
  - kid — key ID, used to select the correct key during JWT verification

Multiple keys can be listed in the array to support key rotation:
  GOOGLE_ADS_MCP_AUTH_JWT_PROVIDER_PRIVATE_KEYS='[{...key1...},{...key2...}]'

Output files:
  <kid>_private.json — full JWK including private scalar (d), never share
  <kid>_public.json  — public JWK only, safe to share with the auth server

Usage:
    uv run scripts/generate_jwk.py
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
    print(f"Generated key with kid: {key.kid}")
