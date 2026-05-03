# Google Ads MCP Server — Helm Chart

This chart deploys the Google Ads MCP Server on Kubernetes with support for
both the **Google OAuth provider** and a **remote auth provider**.

## Prerequisites

- Kubernetes cluster
- Helm 3.x
- Docker image of the MCP server pushed to an accessible registry

## Quick start

Copy the relevant example values file, fill in the required fields, then install:

```bash
# Google OAuth provider (default)
helm install google-ads-mcp ./chart -f chart/values-google.yaml

# Remote auth provider
helm install google-ads-mcp ./chart -f chart/values-remote.yaml
```

## Authentication providers

### 1. Google OAuth provider (default)

Uses FastMCP's OAuth proxy so end-users authenticate through Google.

**Required values / secret keys:**

| Values path | Secret key | Notes |
|---|---|---|
| `secret.data.developerToken` | `developer-token` | Google Ads developer token |
| `secret.data.googleOauthClientId` | `google-oauth-client-id` | OAuth 2.0 Client ID |
| `secret.data.googleOauthClientSecret` | `google-oauth-client-secret` | OAuth 2.0 Client Secret |

**Optional values:**

| Values path | Default | Notes |
|---|---|---|
| `baseUrl` | `https://<host>` | Public URL of the server |
| `auth.google.requireAuthorizationConsent` | `external` | `external` \| `true` \| `false` |
| `auth.google.extraAuthorizeParams` | — | JSON string, e.g. `'{"access_type":"offline"}'` |
| `auth.google.jwtSigningKeyEnabled` | `false` | Set `true` + provide `secret.data.googleOauthJwtSigningKey` |
| `auth.google.storage.type` | `in-memory` | `in-memory` \| `redis` \| `disk` |
| `auth.google.storage.diskDirectory` | — | Only for `disk` storage |
| `auth.google.storage.encryptionKeyEnabled` | `false` | Set `true` + provide `secret.data.authStorageEncryptionKey` |
| `secret.data.authStorageRedisUrl` | — | Required when `storage.type: redis` |
| `loginCustomerId` | — | Manager account customer ID |

See [values-google.yaml](values-google.yaml) for a full example.

### 2. Remote auth provider

Delegates authentication to an existing OAuth 2.0 authorization server.
Storage is **not required** for this provider.

**Required values / secret keys:**

| Values path | Secret key | Notes |
|---|---|---|
| `secret.data.developerToken` | `developer-token` | Google Ads developer token |
| `auth.remote.serverUrl` | — | Authorization server URL |
| `auth.remote.tokenVerifier.url` | — | Token introspection endpoint |

**Optional values:**

| Values path | Default | Notes |
|---|---|---|
| `baseUrl` | `https://<host>` | Public URL of the server |
| `auth.remote.tokenVerifier.method` | `GET` | HTTP method for introspection |
| `auth.remote.tokenVerifier.contentType` | `application/json` | Content-Type for introspection |
| `auth.remote.tokenVerifier.auth` | — | `bearer` \| `basic` \| `` (none) |
| `auth.remote.tokenVerifier.bearerTokenEnabled` | `false` | Set `true` + provide `secret.data.tokenVerifierBearerToken` |
| `secret.data.tokenVerifierBasicUsername` | — | Required when `tokenVerifier.auth: basic` |
| `secret.data.tokenVerifierBasicPassword` | — | Required when `tokenVerifier.auth: basic` |
| `auth.remote.jwtProvider.enabled` | `false` | Generate short-lived JWTs for introspection |
| `auth.remote.jwtProvider.algorithm` | `RS256` | Signing algorithm, e.g. `Ed25519` |
| `auth.remote.jwtProvider.tokenLifetime` | `00:01:00` | HH:MM:SS |
| `auth.remote.jwtProvider.claims` | — | JSON string of extra JWT claims |
| `secret.data.jwtProviderPrivateKeys` | — | Required when `jwtProvider.enabled: true` |

See [values-remote.yaml](values-remote.yaml) for a full example.

## Storage options (Google provider only)

### in-memory (default)
No external dependencies. State is lost on pod restart. Suitable for
single-replica deployments only.

```yaml
auth:
  google:
    storage:
      type: in-memory
```

### redis
Persistent across restarts. Required for multi-replica deployments.

```yaml
auth:
  google:
    storage:
      type: redis
      encryptionKeyEnabled: true  # strongly recommended
secret:
  create: true
  data:
    authStorageRedisUrl: "redis://redis-service:6379/0"
    authStorageEncryptionKey: "your-fernet-key"
```

### disk
Persists to the pod filesystem. Requires a PersistentVolume if you need
data to survive pod restarts.

```yaml
auth:
  google:
    storage:
      type: disk
      diskDirectory: "/data/auth"  # optional, defaults to working directory
      encryptionKeyEnabled: true  # strongly recommended
secret:
  create: true
  data:
    authStorageEncryptionKey: "your-fernet-key"
```

## Secret management

Set `secret.create: true` to let the chart create the Kubernetes Secret from
`secret.data.*` values. This is convenient for development but **not recommended
for production** — manage the Secret externally instead (e.g. with Vault,
External Secrets Operator, or `kubectl create secret`).

When managing externally, create a Secret named `<release-name>` with the
following keys as required by your provider:

| Secret key | Required for |
|---|---|
| `developer-token` | all providers |
| `google-oauth-client-id` | Google provider |
| `google-oauth-client-secret` | Google provider |
| `google-oauth-jwt-signing-key` | Google provider, when `jwtSigningKeyEnabled: true` |
| `auth-storage-redis-url` | Google provider, when `storage.type: redis` |
| `auth-storage-encryption-key` | Google provider, when `encryptionKeyEnabled: true` |
| `token-verifier-bearer-token` | remote provider, when `bearerTokenEnabled: true` |
| `token-verifier-basic-username` | remote provider, when `tokenVerifier.auth: basic` |
| `token-verifier-basic-password` | remote provider, when `tokenVerifier.auth: basic` |
| `jwt-provider-private-keys` | remote provider, when `jwtProvider.enabled: true` |

Example (Google provider):

```bash
kubectl create secret generic google-ads-mcp \
  --from-literal=developer-token="YOUR_DEVELOPER_TOKEN" \
  --from-literal=google-oauth-client-id="YOUR_CLIENT_ID" \
  --from-literal=google-oauth-client-secret="YOUR_CLIENT_SECRET"
```

## Upgrading and uninstalling

```bash
# Upgrade
helm upgrade google-ads-mcp ./chart -f chart/values-google.yaml

# Uninstall
helm uninstall google-ads-mcp
```

## Troubleshooting

```bash
# Deployment status
kubectl get deployment google-ads-mcp
kubectl describe deployment google-ads-mcp

# Pod logs
kubectl logs -l app.kubernetes.io/name=google-ads-mcp

# Inspect Secret and ConfigMap
kubectl describe secret google-ads-mcp
kubectl describe configmap google-ads-mcp
```
