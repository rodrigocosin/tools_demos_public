"""File validation using Pandera — builds DataFrameSchema dynamically from field definitions."""
from __future__ import annotations

import re

import pandas as pd
import pandera as pa
from pandera.errors import SchemaErrors

from server.models import SchemaField, ValidationError

EMAIL_PATTERN = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"

# Maps our datatype strings to Pandera dtypes
DTYPE_MAP: dict[str, object] = {
    "string":   str,
    "integer":  pa.Int64,
    "decimal":  pa.Float64,
    "date":     pa.DateTime,
    "datetime": pa.DateTime,
    "boolean":  pa.Bool,
}


def _checks_for_field(field: SchemaField) -> list[pa.Check]:
    """Build Pandera Check list from a SchemaField definition."""
    checks: list[pa.Check] = []

    # String max-length (size only applies to string type)
    if field.datatype == "string" and field.size != "unlimited":
        n = int(field.size)
        checks.append(
            pa.Check(
                lambda s, n=n: s.str.len() <= n,
                element_wise=False,
                error=f"Comprimento excede o máximo de {n}",
                name=f"max_length({n})",
            )
        )

    rule = (field.validation_rule or "").strip()

    # NO_NULL is handled by nullable=False at Column level; nothing extra needed
    if not rule or rule == "NO_NULL":
        return checks

    if rule == "NO_DUPLICATE":
        checks.append(
            pa.Check(
                lambda s: ~s.duplicated(),
                element_wise=False,
                error="Valores duplicados não são permitidos",
                name="no_duplicate",
            )
        )

    elif rule == "POSITIVE":
        checks.append(pa.Check.gt(0, error="Valor deve ser positivo (> 0)"))

    elif rule == "NON_NEGATIVE":
        checks.append(pa.Check.ge(0, error="Valor deve ser não-negativo (≥ 0)"))

    elif rule.startswith("IN_RANGE:"):
        parts = rule[9:].split(":")
        if len(parts) == 2:
            try:
                lo = float(parts[0]) if parts[0] else None
                hi = float(parts[1]) if parts[1] else None
                if lo is not None and hi is not None:
                    checks.append(
                        pa.Check.in_range(lo, hi, error=f"Valor fora do range [{lo}, {hi}]")
                    )
                elif lo is not None:
                    checks.append(pa.Check.ge(lo, error=f"Valor abaixo do mínimo {lo}"))
                elif hi is not None:
                    checks.append(pa.Check.le(hi, error=f"Valor acima do máximo {hi}"))
            except (ValueError, IndexError):
                pass

    elif rule == "NO_WHITESPACE":
        checks.append(
            pa.Check(
                lambda s: s == s.str.strip(),
                element_wise=False,
                error="Valor contém espaços em branco no início ou fim",
                name="no_whitespace",
            )
        )

    elif rule == "UPPERCASE":
        checks.append(
            pa.Check(
                lambda s: s.map(lambda v: True if not v else v == v.upper()),
                element_wise=False,
                error="Valor deve estar em maiúsculas",
                name="uppercase",
            )
        )

    elif rule == "LOWERCASE":
        checks.append(
            pa.Check(
                lambda s: s.map(lambda v: True if not v else v == v.lower()),
                element_wise=False,
                error="Valor deve estar em minúsculas",
                name="lowercase",
            )
        )

    elif rule == "EMAIL":
        checks.append(
            pa.Check.str_matches(EMAIL_PATTERN, error="Formato de email inválido")
        )

    else:
        # Treat as custom regex
        try:
            re.compile(rule)
            checks.append(
                pa.Check.str_matches(rule, error=f"Não corresponde à expressão: {rule}")
            )
        except re.error:
            pass  # Invalid regex — skip silently

    return checks


def _build_pandera_schema(fields: list[SchemaField]) -> pa.DataFrameSchema:
    """Build a pa.DataFrameSchema from a list of SchemaField definitions."""
    columns: dict[str, pa.Column] = {}

    for field in fields:
        dtype = DTYPE_MAP.get(field.datatype, str)
        nullable = not field.required and field.validation_rule != "NO_NULL"
        checks = _checks_for_field(field)

        columns[field.name] = pa.Column(
            dtype=dtype,
            checks=checks or None,
            nullable=nullable,
            coerce=True,      # coerce "42" → int, "2024-01-01" → datetime, etc.
            required=field.required,
        )

    return pa.DataFrameSchema(columns=columns, coerce=True, strict=False)


def validate_dataframe(df: pd.DataFrame, fields: list[SchemaField]) -> list[ValidationError]:
    """Validate a pandas DataFrame using a Pandera schema built from field definitions."""
    errors: list[ValidationError] = []

    df_cols_lower = {c.lower().strip(): c for c in df.columns}
    field_map = {f.name.lower().strip(): f for f in fields}

    # 1. Check for missing required columns before building schema
    for key, field in field_map.items():
        if field.required and key not in df_cols_lower:
            errors.append(
                ValidationError(
                    row=0,
                    column=field.name,
                    error=f"Coluna obrigatória '{field.name}' está ausente no arquivo",
                )
            )
    if errors:
        return errors

    # 2. Rename df columns to canonical names (case-insensitive match)
    rename_map = {
        col: field_map[col.lower().strip()].name
        for col in df.columns
        if col.lower().strip() in field_map and col != field_map[col.lower().strip()].name
    }
    if rename_map:
        df = df.rename(columns=rename_map)

    # 3. Build schema only for columns present in both schema and file
    present_fields = [f for f in fields if f.name in df.columns]
    schema = _build_pandera_schema(present_fields)

    # 4. Run validation — lazy=True collects all errors instead of stopping at first
    try:
        schema.validate(df, lazy=True)
    except SchemaErrors as exc:
        for _, row in exc.failure_cases.iterrows():
            col = str(row.get("column") or "")
            idx = row.get("index")
            row_num = int(idx) + 1 if idx is not None and not pd.isna(idx) else 0
            check_name = str(row.get("check") or "")
            failure_case = row.get("failure_case")

            # Map Pandera internal check names to friendly messages
            if check_name == "not_nullable":
                msg = "Valor obrigatório não pode ser vazio"
            elif "coerce_dtype" in check_name or check_name.startswith("dtype"):
                field = next((f for f in present_fields if f.name == col), None)
                dt = field.datatype if field else "?"
                msg = f"Tipo inválido para '{dt}': obtido '{failure_case}'"
            elif check_name == "no_duplicate":
                msg = f"Valor duplicado: '{failure_case}'"
            elif check_name.startswith("max_length"):
                msg = f"Comprimento {len(str(failure_case))} excede o limite"
            else:
                # check_name already contains the custom error= string we passed
                msg = check_name if check_name else f"Valor inválido: '{failure_case}'"

            errors.append(ValidationError(row=row_num, column=col, error=msg))

    return errors
