"""Validações de nomenclatura de notebooks, tabelas, views e campos."""

from __future__ import annotations

import re

from app.parser.notebook_parser import ParsedNotebook
from app.validators.extractors import (
    extract_column_names,
    extract_table_refs,
    extract_view_names,
)
from app.validators.models import Severity, ValidationResult

VALID_FIELD_PREFIXES = (
    "ano_", "cod_", "dat_", "dsc_", "dia_", "flg_",
    "grp_", "mes_", "nom_", "num_", "prc_", "qtd_",
    "sgl_", "vlr_", "xml_",
)


def validate_notebook_naming(notebook: ParsedNotebook) -> list[ValidationResult]:
    """Valida nomenclatura do arquivo do notebook."""
    results: list[ValidationResult] = []
    fname = notebook.filename.lower()

    # Remove extensão
    name = fname
    dot_pos = name.rfind(".")
    if dot_pos >= 0:
        name = name[:dot_pos]

    full_text = notebook.full_code.lower()

    if "3_prd_ingestao" in full_text:
        if name.startswith("nb_ingestao_"):
            results.append(ValidationResult(
                category="Nomenclatura de Notebook",
                severity=Severity.OK,
                message=f"Nome do notebook '{notebook.filename}' segue o padrão para ingestão (nb_ingestao_[sistema]_[tabela]).",
            ))
        else:
            results.append(ValidationResult(
                category="Nomenclatura de Notebook",
                severity=Severity.ERROR,
                message=f"Nome do notebook '{notebook.filename}' NÃO segue o padrão para ingestão.",
                details="Para notebooks do catálogo 3_prd_ingestao, o nome deve seguir: nb_ingestao_[nome do sistema de origem]_[nome da tabela].",
            ))

    if re.search(r"3_prd_lakehouse(?:_rwd)?", full_text):
        if name.startswith("nb_") and not name.startswith("nb_ingestao_"):
            results.append(ValidationResult(
                category="Nomenclatura de Notebook",
                severity=Severity.OK,
                message=f"Nome do notebook '{notebook.filename}' segue o padrão para lakehouse (nb_[sistema]_[tabela]).",
            ))
        else:
            results.append(ValidationResult(
                category="Nomenclatura de Notebook",
                severity=Severity.ERROR,
                message=f"Nome do notebook '{notebook.filename}' NÃO segue o padrão para lakehouse.",
                details="Para notebooks dos catálogos 3_prd_lakehouse/3_prd_lakehouse_rwd, o nome deve seguir: nb_[nome do sistema de origem]_[nome da tabela].",
            ))

    return results


def validate_table_naming(notebook: ParsedNotebook) -> list[ValidationResult]:
    """Valida nomenclatura das tabelas referenciadas."""
    results: list[ValidationResult] = []
    refs = extract_table_refs(notebook)

    for catalog, schema, table in refs:
        # Tabelas devem ser minúsculas
        if table != table.lower():
            results.append(ValidationResult(
                category="Nomenclatura de Tabelas",
                severity=Severity.ERROR,
                message=f"Tabela '{table}' contém letras maiúsculas.",
                details="Nomes de tabelas devem ser em letras minúsculas.",
            ))

        # Regras para catálogos lakehouse
        if catalog in ("3_prd_lakehouse", "3_prd_lakehouse_rwd"):
            if schema.startswith("2_tru"):
                if not table.startswith("tbl_tru_"):
                    results.append(ValidationResult(
                        category="Nomenclatura de Tabelas",
                        severity=Severity.ERROR,
                        message=f"Tabela '{table}' no schema '{schema}' deve iniciar com 'tbl_tru_'.",
                        details=f"Tabelas em schemas iniciados com 2_tru devem ter prefixo 'tbl_tru_'. Encontrado: '{table}'.",
                    ))
                else:
                    results.append(ValidationResult(
                        category="Nomenclatura de Tabelas",
                        severity=Severity.OK,
                        message=f"Tabela '{table}' segue o prefixo correto 'tbl_tru_'.",
                    ))

            elif schema == "3_ref":
                if not (table.startswith("fat_") or table.startswith("dim_")):
                    results.append(ValidationResult(
                        category="Nomenclatura de Tabelas",
                        severity=Severity.ERROR,
                        message=f"Tabela '{table}' no schema '3_ref' deve iniciar com 'fat_' ou 'dim_'.",
                        details=f"Tabelas no schema 3_ref devem ter prefixo 'fat_' ou 'dim_'. Encontrado: '{table}'.",
                    ))
                else:
                    results.append(ValidationResult(
                        category="Nomenclatura de Tabelas",
                        severity=Severity.OK,
                        message=f"Tabela '{table}' segue o prefixo correto para schema 3_ref.",
                    ))

            elif schema == "4_rel":
                if not table.startswith("rel_"):
                    results.append(ValidationResult(
                        category="Nomenclatura de Tabelas",
                        severity=Severity.ERROR,
                        message=f"Tabela '{table}' no schema '4_rel' deve iniciar com 'rel_'.",
                        details=f"Tabelas no schema 4_rel devem ter prefixo 'rel_'. Encontrado: '{table}'.",
                    ))
                else:
                    results.append(ValidationResult(
                        category="Nomenclatura de Tabelas",
                        severity=Severity.OK,
                        message=f"Tabela '{table}' segue o prefixo correto 'rel_'.",
                    ))

    if not refs:
        results.append(ValidationResult(
            category="Nomenclatura de Tabelas",
            severity=Severity.WARNING,
            message="Nenhuma referência a tabelas (catalog.schema.table) foi detectada no notebook.",
        ))

    return results


def validate_view_naming(notebook: ParsedNotebook) -> list[ValidationResult]:
    """Valida nomenclatura de views."""
    results: list[ValidationResult] = []
    views = extract_view_names(notebook)

    for view in views:
        if view != view.lower():
            results.append(ValidationResult(
                category="Nomenclatura de Views",
                severity=Severity.ERROR,
                message=f"View '{view}' contém letras maiúsculas.",
                details="Nomes de views devem ser em letras minúsculas.",
            ))
        if not view.startswith("vie_"):
            results.append(ValidationResult(
                category="Nomenclatura de Views",
                severity=Severity.ERROR,
                message=f"View '{view}' não inicia com o prefixo 'vie_'.",
                details=f"Views devem iniciar com o prefixo 'vie_'. Encontrado: '{view}'.",
            ))
        else:
            results.append(ValidationResult(
                category="Nomenclatura de Views",
                severity=Severity.OK,
                message=f"View '{view}' segue a nomenclatura correta.",
            ))

    return results


def validate_field_naming(notebook: ParsedNotebook) -> list[ValidationResult]:
    """Valida nomenclatura de campos (colunas)."""
    results: list[ValidationResult] = []
    full_text = notebook.full_code.lower()

    # Exceção: tabelas do catálogo 3_prd_ingestao não precisam de prefixo
    if "3_prd_ingestao" in full_text and "3_prd_lakehouse" not in full_text:
        results.append(ValidationResult(
            category="Nomenclatura de Campos",
            severity=Severity.OK,
            message="Catálogo 3_prd_ingestao: regra de prefixo de campos não se aplica.",
        ))
        return results

    columns = extract_column_names(notebook)
    invalid_cols = []

    for col in columns:
        if not any(col.startswith(prefix) for prefix in VALID_FIELD_PREFIXES):
            invalid_cols.append(col)

    if invalid_cols:
        prefixes_str = ", ".join(VALID_FIELD_PREFIXES)
        results.append(ValidationResult(
            category="Nomenclatura de Campos",
            severity=Severity.ERROR,
            message=f"{len(invalid_cols)} campo(s) não seguem os prefixos obrigatórios.",
            details=f"Campos inválidos: {', '.join(invalid_cols[:20])}{'...' if len(invalid_cols) > 20 else ''}. "
                    f"Prefixos válidos: {prefixes_str}.",
        ))
    elif columns:
        results.append(ValidationResult(
            category="Nomenclatura de Campos",
            severity=Severity.OK,
            message=f"Todos os {len(columns)} campos detectados seguem os prefixos obrigatórios.",
        ))
    else:
        results.append(ValidationResult(
            category="Nomenclatura de Campos",
            severity=Severity.WARNING,
            message="Nenhuma definição de campo detectada para validação de prefixos.",
        ))

    return results
