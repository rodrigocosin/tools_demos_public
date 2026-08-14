"""
Parser para notebooks Databricks nos formatos .py e .ipynb.
Extrai células individuais para análise estática (sem execução de código).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field


@dataclass
class NotebookCell:
    index: int
    content: str
    language: str  # "python", "sql", "markdown", "unknown"


@dataclass
class ParsedNotebook:
    filename: str
    format: str  # "py" or "ipynb"
    cells: list[NotebookCell] = field(default_factory=list)
    raw_content: str = ""

    @property
    def full_code(self) -> str:
        return "\n".join(c.content for c in self.cells)

    @property
    def sql_cells(self) -> list[NotebookCell]:
        return [c for c in self.cells if c.language == "sql"]

    @property
    def python_cells(self) -> list[NotebookCell]:
        return [c for c in self.cells if c.language == "python"]

    @property
    def markdown_cells(self) -> list[NotebookCell]:
        return [c for c in self.cells if c.language == "markdown"]


# Separador padrão de células em notebooks Databricks exportados como .py
_DATABRICKS_CELL_SEP = re.compile(r"# COMMAND ----------")
# Magic commands que indicam linguagem
_MAGIC_SQL = re.compile(r"^\s*#\s*MAGIC\s+%sql\b", re.MULTILINE)
_MAGIC_MD = re.compile(r"^\s*#\s*MAGIC\s+%md\b", re.MULTILINE)
_MAGIC_PREFIX = re.compile(r"^\s*#\s*MAGIC\s+", re.MULTILINE)
# Detecta header do Databricks notebook
_DATABRICKS_HEADER = re.compile(r"^#\s*Databricks notebook source", re.IGNORECASE)

# Tamanho máximo de arquivo: 5 MB
MAX_FILE_SIZE = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {".py", ".ipynb"}


def _detect_cell_language(content: str, default_lang: str = "python") -> str:
    if _MAGIC_SQL.search(content):
        return "sql"
    if _MAGIC_MD.search(content):
        return "markdown"
    # Heurísticas para SQL puro (sem magic)
    stripped = content.strip().upper()
    sql_keywords = (
        "SELECT ", "CREATE ", "ALTER ", "DROP ", "INSERT ",
        "MERGE ", "SHOW ", "DESCRIBE ", "SET ", "USE ",
        "GRANT ", "REVOKE ", "WITH ",
    )
    if any(stripped.startswith(kw) for kw in sql_keywords):
        return "sql"
    return default_lang


def _clean_magic_lines(content: str) -> str:
    """Remove prefixos MAGIC das linhas para obter o conteúdo real."""
    lines = content.split("\n")
    cleaned = []
    for line in lines:
        cleaned_line = re.sub(r"^\s*#\s*MAGIC\s+", "", line)
        cleaned.append(cleaned_line)
    return "\n".join(cleaned)


def parse_py_notebook(content: str, filename: str) -> ParsedNotebook:
    """Parse de notebook Databricks exportado como .py"""
    notebook = ParsedNotebook(filename=filename, format="py", raw_content=content)

    # Remove header do Databricks se presente
    lines = content.split("\n")
    start_idx = 0
    if lines and _DATABRICKS_HEADER.match(lines[0]):
        start_idx = 1

    content_without_header = "\n".join(lines[start_idx:])

    # Divide em células
    raw_cells = _DATABRICKS_CELL_SEP.split(content_without_header)

    for i, raw_cell in enumerate(raw_cells):
        cell_content = raw_cell.strip()
        if not cell_content:
            continue
        language = _detect_cell_language(cell_content)
        # Limpa magic commands para análise
        clean_content = _clean_magic_lines(cell_content)
        notebook.cells.append(NotebookCell(
            index=i,
            content=clean_content,
            language=language,
        ))

    return notebook


def parse_ipynb_notebook(content: str, filename: str) -> ParsedNotebook:
    """Parse de notebook no formato Jupyter (.ipynb)"""
    notebook = ParsedNotebook(filename=filename, format="ipynb", raw_content=content)

    try:
        nb_json = json.loads(content)
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(f"Arquivo .ipynb inválido: {e}") from e

    if not isinstance(nb_json, dict) or "cells" not in nb_json:
        raise ValueError("Arquivo .ipynb não contém estrutura válida de notebook.")

    cells = nb_json.get("cells", [])
    if not isinstance(cells, list):
        raise ValueError("Campo 'cells' do notebook não é uma lista.")

    for i, cell in enumerate(cells):
        if not isinstance(cell, dict):
            continue
        cell_type = cell.get("cell_type", "")
        source_lines = cell.get("source", [])

        if isinstance(source_lines, list):
            source = "".join(source_lines)
        elif isinstance(source_lines, str):
            source = source_lines
        else:
            continue

        source = source.strip()
        if not source:
            continue

        if cell_type == "markdown":
            language = "markdown"
        elif cell_type == "code":
            language = _detect_cell_language(source)
        else:
            language = "unknown"

        notebook.cells.append(NotebookCell(
            index=i,
            content=source,
            language=language,
        ))

    return notebook


def parse_notebook(content: bytes, filename: str) -> ParsedNotebook:
    """
    Ponto de entrada principal. Detecta formato e faz o parse.
    Aplica validações de segurança (tamanho, extensão).
    """
    if len(content) > MAX_FILE_SIZE:
        raise ValueError(
            f"Arquivo excede o tamanho máximo permitido de {MAX_FILE_SIZE // (1024*1024)} MB."
        )

    # Validar extensão
    ext = ""
    dot_pos = filename.rfind(".")
    if dot_pos >= 0:
        ext = filename[dot_pos:].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Formato não suportado: '{ext}'. Use .py ou .ipynb."
        )

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError("Arquivo não está em formato UTF-8 válido.") from e

    if ext == ".py":
        return parse_py_notebook(text, filename)
    else:
        return parse_ipynb_notebook(text, filename)
