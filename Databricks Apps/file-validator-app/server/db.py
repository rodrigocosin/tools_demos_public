"""Database connection and query helpers using Databricks SQL Connector."""

from __future__ import annotations

import os
from databricks import sql
from databricks.sdk import WorkspaceClient

CATALOG = "cosin_aws_serverless_catalog"
DB_SCHEMA = "file_validator"
SCHEMA_TABLE = f"{CATALOG}.{DB_SCHEMA}.file_schemas"
UPLOAD_TABLE = f"{CATALOG}.{DB_SCHEMA}.uploaded_files"
UPLOAD_VOLUME_PATH = f"/Volumes/{CATALOG}/{DB_SCHEMA}/uploads"


def _get_token() -> str:
    """Get access token via Databricks SDK credential chain.

    In Databricks Apps the SDK automatically uses the injected service principal
    credentials (DATABRICKS_CLIENT_ID / DATABRICKS_CLIENT_SECRET). Locally it
    falls back to ~/.databrickscfg or DATABRICKS_TOKEN env var.
    """
    # Prefer an explicit token if already set (e.g. local dev with PAT)
    env_token = os.environ.get("DATABRICKS_TOKEN")
    if env_token:
        return env_token

    # Use SDK credential chain (handles Databricks Apps service principal)
    w = WorkspaceClient()
    auth_headers = w.config.authenticate()
    bearer = auth_headers.get("Authorization", "")
    return bearer.replace("Bearer ", "")


def get_connection():
    host = os.environ.get(
        "DATABRICKS_HOST", "fevm-cosin-aws-serverless.cloud.databricks.com"
    )
    warehouse_id = os.environ.get("WAREHOUSE_ID", "0c2def7684630e5e")
    token = _get_token()

    return sql.connect(
        server_hostname=host,
        http_path=f"/sql/1.0/warehouses/{warehouse_id}",
        access_token=token,
    )


def execute_query(query: str, params: dict | None = None) -> list[dict]:
    """Execute a query and return results as list of dicts."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        return []
    finally:
        conn.close()


def execute_statement(statement: str, params: dict | None = None) -> None:
    """Execute a statement (INSERT, UPDATE, DELETE) without returning results."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(statement, params)
    finally:
        conn.close()


def init_tables():
    """Create required tables and volume if they don't exist."""
    execute_statement(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{DB_SCHEMA}.uploads")

    create_schemas = f"""
    CREATE TABLE IF NOT EXISTS {SCHEMA_TABLE} (
        schema_id STRING,
        schema_name STRING,
        fields STRING,
        created_at TIMESTAMP,
        updated_at TIMESTAMP
    )
    """
    create_uploads = f"""
    CREATE TABLE IF NOT EXISTS {UPLOAD_TABLE} (
        upload_id STRING,
        schema_name STRING,
        file_name STRING,
        uploaded_at TIMESTAMP,
        row_count INT,
        data STRING,
        volume_path STRING
    )
    """
    execute_statement(create_schemas)
    execute_statement(create_uploads)

    # Add volume_path column to existing tables that predate this change
    try:
        execute_statement(f"ALTER TABLE {UPLOAD_TABLE} ADD COLUMN volume_path STRING")
    except Exception:
        pass  # Column already exists
