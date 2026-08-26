import os
import time
import urllib.request
import urllib.parse
import json

_cached_token = None
_token_expiry = 0


def get_workspace_host() -> str:
    host = os.environ.get("DATABRICKS_HOST", "")
    if host and not host.startswith("http"):
        host = f"https://{host}"
    return host.rstrip("/")


def get_auth_headers() -> dict:
    """Return Authorization headers using M2M OAuth2 or static token."""
    token = _get_token()
    return {"Authorization": f"Bearer {token}"}


def _get_token() -> str:
    global _cached_token, _token_expiry

    # Static token for local dev
    static_token = os.environ.get("DATABRICKS_TOKEN", "")
    if static_token:
        return static_token

    # Use cached token if still valid (with 60s buffer)
    if _cached_token and time.time() < _token_expiry - 60:
        return _cached_token

    # M2M OAuth2 via client credentials (auto-injected in Databricks Apps)
    client_id = os.environ.get("DATABRICKS_CLIENT_ID", "")
    client_secret = os.environ.get("DATABRICKS_CLIENT_SECRET", "")
    host = get_workspace_host()

    if not client_id or not client_secret:
        raise RuntimeError("No DATABRICKS_TOKEN or DATABRICKS_CLIENT_ID/SECRET found")

    data = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "all-apis",
    }).encode()

    req = urllib.request.Request(
        f"{host}/oidc/v1/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())

    _cached_token = result["access_token"]
    expires_in = result.get("expires_in", 3600)
    _token_expiry = time.time() + expires_in

    return _cached_token
