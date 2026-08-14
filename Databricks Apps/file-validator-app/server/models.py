"""Pydantic models for request/response validation."""

from pydantic import BaseModel


class SchemaField(BaseModel):
    name: str
    datatype: str  # string, integer, decimal, date, datetime, boolean
    size: str  # 10, 20, 50, 100, 200, 500, unlimited
    required: bool = False
    validation_rule: str = ""


class SchemaCreate(BaseModel):
    schema_name: str
    fields: list[SchemaField]


class SchemaUpdate(BaseModel):
    schema_name: str
    fields: list[SchemaField]


class ValidationError(BaseModel):
    row: int
    column: str
    error: str


class ValidationResult(BaseModel):
    valid: bool
    errors: list[ValidationError]
    row_count: int
