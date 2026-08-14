"""API routes for schema management and file validation."""
from __future__ import annotations

import io
import json
import os
import uuid
from datetime import datetime, date

import pandas as pd
import requests
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from server.db import SCHEMA_TABLE, UPLOAD_TABLE, UPLOAD_VOLUME_PATH, execute_query, execute_statement
from server.models import SchemaCreate, SchemaUpdate, ValidationResult
from server.validator import validate_dataframe

router = APIRouter(prefix="/api")


def _serialize_row(row: dict) -> dict:
    """Convert non-JSON-serializable types in a row dict."""
    out = {}
    for k, v in row.items():
        if isinstance(v, (datetime, date)):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


def _sql_escape(value: str) -> str:
    """Escape a string for safe embedding in a SQL string literal.

    Backslashes must be doubled so the SQL engine stores them literally,
    and single quotes must be escaped.
    """
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _parse_fields_json(raw: str) -> list:
    """Parse fields JSON, handling cases where backslashes were not
    properly escaped during storage."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try fixing unescaped backslashes by doubling them
        import re
        fixed = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', raw)
        return json.loads(fixed)


# ---- Schema CRUD ----


@router.get("/schemas")
def list_schemas():
    rows = execute_query(
        f"SELECT schema_id, schema_name, fields, created_at, updated_at FROM {SCHEMA_TABLE} ORDER BY schema_name"
    )
    result = []
    for row in rows:
        row = _serialize_row(row)
        if isinstance(row.get("fields"), str):
            row["fields"] = _parse_fields_json(row["fields"])
        result.append(row)
    return result


@router.post("/schemas")
def create_schema(body: SchemaCreate):
    schema_id = str(uuid.uuid4())
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    fields_json = json.dumps([f.model_dump() for f in body.fields])
    name_escaped = _sql_escape(body.schema_name)
    fields_escaped = _sql_escape(fields_json)

    execute_statement(
        f"""INSERT INTO {SCHEMA_TABLE} (schema_id, schema_name, fields, created_at, updated_at)
        VALUES ('{schema_id}', '{name_escaped}', '{fields_escaped}', '{now}', '{now}')"""
    )
    return {"schema_id": schema_id, "message": "Schema created"}


@router.put("/schemas/{schema_id}")
def update_schema(schema_id: str, body: SchemaUpdate):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    fields_json = json.dumps([f.model_dump() for f in body.fields])
    name_escaped = _sql_escape(body.schema_name)
    fields_escaped = _sql_escape(fields_json)

    execute_statement(
        f"""UPDATE {SCHEMA_TABLE}
        SET schema_name = '{name_escaped}',
            fields = '{fields_escaped}',
            updated_at = '{now}'
        WHERE schema_id = '{schema_id}'"""
    )
    return {"message": "Schema updated"}


@router.delete("/schemas/{schema_id}")
def delete_schema(schema_id: str):
    execute_statement(f"DELETE FROM {SCHEMA_TABLE} WHERE schema_id = '{schema_id}'")
    return {"message": "Schema deleted"}


# ---- File Validation & Upload ----


def _upload_to_volume(volume_path: str, data: bytes) -> None:
    """Upload raw file bytes to a Databricks Volume using the Files API."""
    from server.db import _get_token
    host = os.environ.get("DATABRICKS_HOST", "fevm-cosin-aws-serverless.cloud.databricks.com")
    token = _get_token()
    if not host.startswith("http"):
        host = f"https://{host}"
    url = f"{host}/api/2.0/fs/files{volume_path}"
    resp = requests.put(
        url,
        data=data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/octet-stream"},
        timeout=120,
    )
    resp.raise_for_status()


def _read_upload(file: UploadFile) -> pd.DataFrame:
    """Read uploaded file into a pandas DataFrame."""
    filename = file.filename or ""
    if filename.lower().endswith(".csv"):
        return pd.read_csv(file.file, dtype=str, keep_default_na=False)
    elif filename.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(file.file, dtype=str, keep_default_na=False)
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Upload CSV or Excel (.xlsx/.xls).",
        )


@router.post("/validate")
def validate_file(file: UploadFile = File(...), schema_id: str = Form(...)):
    """Validate an uploaded file against a schema definition."""
    # Fetch schema
    rows = execute_query(
        f"SELECT fields FROM {SCHEMA_TABLE} WHERE schema_id = '{schema_id}'"
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Schema not found")

    fields_raw = rows[0]["fields"]
    if isinstance(fields_raw, str):
        fields_raw = _parse_fields_json(fields_raw)

    from server.models import SchemaField

    fields = [SchemaField(**f) for f in fields_raw]

    # Read file
    df = _read_upload(file)

    # Validate
    errors = validate_dataframe(df, fields)

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        row_count=len(df),
    )


@router.post("/upload")
def upload_file(file: UploadFile = File(...), schema_id: str = Form(...)):
    """Validate file, save original to volume and sample (10 rows) to Delta table."""
    # Read raw bytes first so we can upload the original unchanged later
    raw_bytes = file.file.read()
    file.file = io.BytesIO(raw_bytes)  # reset stream for DataFrame parsing

    # Fetch schema
    rows = execute_query(
        f"SELECT schema_name, fields FROM {SCHEMA_TABLE} WHERE schema_id = '{schema_id}'"
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Schema not found")

    schema_name = rows[0]["schema_name"]
    fields_raw = rows[0]["fields"]
    if isinstance(fields_raw, str):
        fields_raw = _parse_fields_json(fields_raw)

    from server.models import SchemaField

    fields = [SchemaField(**f) for f in fields_raw]

    # Read and validate
    df = _read_upload(file)
    errors = validate_dataframe(df, fields)

    if errors:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Validation failed",
                "errors": [e.model_dump() for e in errors],
            },
        )

    upload_id = str(uuid.uuid4())
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    original_filename = file.filename or "unknown"

    # Upload original file (unchanged) to volume
    volume_path = f"{UPLOAD_VOLUME_PATH}/{upload_id}_{original_filename}"
    try:
        _upload_to_volume(volume_path, raw_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file to volume: {e}")

    # Store only first 10 rows as sample in Delta table
    sample_json = df.head(10).to_json(orient="records")
    sample_escaped = _sql_escape(sample_json)
    name_escaped = _sql_escape(schema_name)
    file_name_escaped = _sql_escape(original_filename)
    volume_path_escaped = _sql_escape(volume_path)

    execute_statement(
        f"""INSERT INTO {UPLOAD_TABLE}
        (upload_id, schema_name, file_name, uploaded_at, row_count, data, volume_path)
        VALUES ('{upload_id}', '{name_escaped}', '{file_name_escaped}', '{now}',
                {len(df)}, '{sample_escaped}', '{volume_path_escaped}')"""
    )

    return {
        "upload_id": upload_id,
        "message": "File uploaded successfully",
        "row_count": len(df),
        "volume_path": volume_path,
    }
