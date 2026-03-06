"""Configuration and authentication for Databricks resources."""
import os

IS_DATABRICKS_APP = bool(os.environ.get("DATABRICKS_APP_NAME"))

CATALOG = os.environ.get("CATALOG", "cosin_aws_serverless_catalog")
SCHEMA = os.environ.get("SCHEMA", "exames_clinicos")
SERVING_ENDPOINT = os.environ.get("SERVING_ENDPOINT", "databricks-meta-llama-3-3-70b-instruct")
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/uploads_volume"


def get_workspace_host() -> str:
    """Get workspace host with https:// prefix."""
    if IS_DATABRICKS_APP:
        host = os.environ.get("DATABRICKS_HOST", "")
        if host and not host.startswith("http"):
            host = f"https://{host}"
        return host
    return os.environ.get(
        "DATABRICKS_HOST",
        "https://fevm-cosin-aws-serverless.cloud.databricks.com",
    )


def get_token() -> str:
    """Get auth token - from env or SDK."""
    if IS_DATABRICKS_APP:
        try:
            from databricks.sdk import WorkspaceClient
            w = WorkspaceClient()
            if w.config.token:
                return w.config.token
            headers = w.config.authenticate()
            if headers and "Authorization" in headers:
                return headers["Authorization"].replace("Bearer ", "")
        except Exception as e:
            print(f"SDK auth failed: {e}")
    return os.environ.get(
        "DATABRICKS_TOKEN",
        "?????????????????????????????",
    )


def get_warehouse_id() -> str:
    """Get SQL warehouse ID."""
    return os.environ.get("DATABRICKS_WAREHOUSE_ID", "0c2def7684630e5e")
