"""Dual-mode authentication for Databricks Apps."""

import os
import base64
from databricks.sdk import WorkspaceClient

IS_DATABRICKS_APP = bool(os.environ.get("DATABRICKS_APP_NAME"))

# Cache the PAT read from Databricks Secrets (loaded once at first use)
_cached_pat: str | None = None


def _get_pat() -> str | None:
    """Read PAT from env or Databricks Secrets (cached after first read)."""
    global _cached_pat
    # 1st: env var (set manually or via future app.yaml secret binding)
    token = os.environ.get("APP_DATABRICKS_TOKEN")
    if token:
        return token
    # 2nd: Databricks Secrets via service principal (cached)
    if _cached_pat:
        return _cached_pat
    try:
        sp_client = WorkspaceClient()  # auto-injected service principal
        secret = sp_client.secrets.get_secret(scope="radar-ia", key="observability-token")
        # SDK returns value as base64-encoded string
        _cached_pat = base64.b64decode(secret.value).decode("utf-8")
        return _cached_pat
    except Exception:
        return None


def get_workspace_client(user_token: str = None) -> WorkspaceClient:
    """Get WorkspaceClient - works both locally and in Databricks Apps."""
    if IS_DATABRICKS_APP:
        host = os.environ.get("DATABRICKS_HOST", "")
        if host and not host.startswith("http"):
            host = f"https://{host}"
        # 1st: forwarded user OAuth token (browser request)
        token = user_token
        # 2nd: PAT from env or Databricks Secrets
        if not token:
            token = _get_pat()
        if token and host:
            # Temporarily remove OAuth env vars to avoid conflict with PAT.
            # Safe in asyncio (single-threaded, no await in this block).
            _oauth_keys = ("DATABRICKS_CLIENT_ID", "DATABRICKS_CLIENT_SECRET",
                           "DATABRICKS_CLIENT_CREDENTIALS_PROVIDER")
            _saved = {k: os.environ.pop(k) for k in _oauth_keys if k in os.environ}
            try:
                return WorkspaceClient(host=host, token=token)
            finally:
                os.environ.update(_saved)
        # Last resort: service principal (auto-injected credentials)
        return WorkspaceClient()
    profile = os.environ.get("DATABRICKS_PROFILE", "cosin-aws-serverless")
    return WorkspaceClient(profile=profile)
