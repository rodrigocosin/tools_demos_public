"""Funções compartilhadas de extração de metadados de notebooks SQL."""

from __future__ import annotations

import re

from app.parser.notebook_parser import ParsedNotebook

# Extrai nomes de tabelas de comandos SQL comuns
TABLE_REF_PATTERN = re.compile(
    r"""(?:CREATE\s+(?:OR\s+REPLACE\s+)?(?:STREAMING\s+)?(?:LIVE\s+)?TABLE|"""
    r"""INSERT\s+(?:INTO|OVERWRITE)|"""
    r"""MERGE\s+INTO|"""
    r"""ALTER\s+TABLE|"""
    r"""SHOW\s+CREATE\s+TABLE|"""
    r"""DESCRIBE\s+(?:EXTENDED\s+)?(?:TABLE\s+)?|"""
    r"""SELECT\s+.*\s+FROM|"""
    r"""FROM)\s+"""
    r"""(?:`?(\w+)`?\.`?(\w+)`?\.`?(\w+)`?)""",
    re.IGNORECASE | re.MULTILINE,
)

# Extrai criação de views
VIEW_PATTERN = re.compile(
    r"CREATE\s+(?:OR\s+REPLACE\s+)?(?:TEMP\s+|TEMPORARY\s+)?VIEW\s+"
    r"(?:`?(\w+)`?\.`?(\w+)`?\.)?`?(\w+)`?",
    re.IGNORECASE,
)

# Extrai definição de colunas dentro de CREATE TABLE
COLUMN_DEF_PATTERN = re.compile(
    r"^\s*`?([a-z_]\w*)`?\s+(?:STRING|INT|BIGINT|DOUBLE|FLOAT|DECIMAL|BOOLEAN|DATE|TIMESTAMP|BINARY|ARRAY|MAP|STRUCT)\b",
    re.IGNORECASE | re.MULTILINE,
)

# Extrai coluna de ALTER COLUMN
ALTER_COLUMN_PATTERN = re.compile(
    r"\bALTER\s+COLUMN\s+`?([a-z_]\w*)`?",
    re.IGNORECASE,
)

# Extrai coluna de COMMENT ON COLUMN
COMMENT_ON_COLUMN_PATTERN = re.compile(
    r"\bCOMMENT\s+ON\s+COLUMN\s+\S+\.`?([a-z_]\w*)`?",
    re.IGNORECASE,
)

# Extrai COMMENT strings
COMMENT_PATTERN = re.compile(
    r"""COMMENT\s+['"](.+?)['"]""",
    re.IGNORECASE | re.DOTALL,
)

COMMENT_ON_PATTERN = re.compile(
    r"""COMMENT\s+ON\s+(?:TABLE|COLUMN)\s+\S+\s+IS\s+['"](.+?)['"]""",
    re.IGNORECASE | re.DOTALL,
)

# Extrai pares tag=valor
TAG_PAIR_PATTERN = re.compile(
    r"""['"](\w+)['"]\s*=\s*['"](\w+)['"]""",
    re.IGNORECASE,
)

# Detecta masking tags com valor (não N/A_MASKING)
MASKING_TAG_PATTERN = re.compile(
    r"""['"](?:PII|PHI|ESTRATEGICA)['"]\s*=\s*['"](?!N/A_MASKING)([A-Z_]+)['"]""",
    re.IGNORECASE,
)

# Detecta funções de mascaramento
MASK_FUNCTION_PATTERN = re.compile(r"\boc_mask_(\w+)", re.IGNORECASE)

SQL_KEYWORDS = frozenset({
    "select", "from", "where", "merge", "into", "as",
    "set", "table", "column", "and", "or", "not", "on",
})


def extract_table_refs(notebook: ParsedNotebook) -> list[tuple[str, str, str]]:
    """Extrai referências a tabelas (catalog, schema, table) do notebook."""
    refs = []
    for cell in notebook.cells:
        for match in TABLE_REF_PATTERN.finditer(cell.content):
            catalog, schema, table = match.group(1), match.group(2), match.group(3)
            if catalog and schema and table:
                refs.append((catalog.lower(), schema.lower(), table.lower()))
    return refs


def extract_view_names(notebook: ParsedNotebook) -> list[str]:
    """Extrai nomes de views criadas no notebook."""
    views = []
    for cell in notebook.cells:
        for match in VIEW_PATTERN.finditer(cell.content):
            view_name = match.group(3)
            if view_name:
                views.append(view_name.lower())
    return views


def extract_column_names(notebook: ParsedNotebook) -> list[str]:
    """Extrai nomes de colunas definidas no notebook."""
    columns = set()
    for cell in notebook.cells:
        for match in COLUMN_DEF_PATTERN.finditer(cell.content):
            col = match.group(1).lower()
            if col not in SQL_KEYWORDS:
                columns.add(col)
        for match in ALTER_COLUMN_PATTERN.finditer(cell.content):
            columns.add(match.group(1).lower())
        for match in COMMENT_ON_COLUMN_PATTERN.finditer(cell.content):
            columns.add(match.group(1).lower())
    return list(columns)


def extract_comments(notebook: ParsedNotebook) -> list[str]:
    """Extrai todas as strings de COMMENT do notebook."""
    full_text = notebook.full_code
    comments = []
    for match in COMMENT_PATTERN.finditer(full_text):
        comments.append(match.group(1).strip())
    for match in COMMENT_ON_PATTERN.finditer(full_text):
        comments.append(match.group(1).strip())
    return comments


def extract_tag_pairs(notebook: ParsedNotebook) -> list[tuple[str, str]]:
    """Extrai pares (tag, valor) do notebook."""
    pairs = []
    for match in TAG_PAIR_PATTERN.finditer(notebook.full_code):
        pairs.append((match.group(1).upper(), match.group(2).upper()))
    return pairs


def extract_tag_pairs_raw(notebook: ParsedNotebook) -> list[tuple[str, str, str]]:
    """Extrai pares (tag_original, valor_original, texto_match) para validação de case."""
    results = []
    for match in TAG_PAIR_PATTERN.finditer(notebook.full_code):
        results.append((match.group(1), match.group(2), match.group(0)))
    return results


def extract_mask_functions(notebook: ParsedNotebook) -> list[str]:
    """Extrai sufixos de funções oc_mask_*."""
    return MASK_FUNCTION_PATTERN.findall(notebook.full_code)


def extract_masking_tags(notebook: ParsedNotebook) -> list[str]:
    """Extrai valores de tags PII/PHI/ESTRATEGICA que requerem mascaramento."""
    return MASKING_TAG_PATTERN.findall(notebook.full_code)
