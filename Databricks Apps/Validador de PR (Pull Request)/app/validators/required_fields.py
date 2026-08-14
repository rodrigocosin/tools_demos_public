"""Validações de campos e registros obrigatórios."""

from __future__ import annotations

import re

from app.parser.notebook_parser import ParsedNotebook
from app.validators.models import Severity, ValidationResult

_FAT_TABLE = re.compile(r"\bfat_\w+", re.IGNORECASE)
_DIM_TABLE = re.compile(r"\bdim_\w+", re.IGNORECASE)
_DAT_CARGA = re.compile(r"\bdat_carga\b", re.IGNORECASE)
_SK_SISTEMA = re.compile(r"\bsk_sistema_origem\b", re.IGNORECASE)


def validate_required_fields(notebook: ParsedNotebook) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    full_text = notebook.full_code

    has_fat = bool(_FAT_TABLE.search(full_text))
    has_dim = bool(_DIM_TABLE.search(full_text))
    has_dat_carga = bool(_DAT_CARGA.search(full_text))
    has_sk_sistema = bool(_SK_SISTEMA.search(full_text))

    # Tabelas fat_: requer dat_carga e sk_sistema_origem
    if has_fat:
        if has_dat_carga and has_sk_sistema:
            results.append(ValidationResult(
                category="Campos Obrigatórios",
                severity=Severity.OK,
                message="Tabela 'fat_': campos obrigatórios 'dat_carga' e 'sk_sistema_origem' encontrados.",
            ))
        else:
            missing = []
            if not has_dat_carga:
                missing.append("dat_carga")
            if not has_sk_sistema:
                missing.append("sk_sistema_origem")
            results.append(ValidationResult(
                category="Campos Obrigatórios",
                severity=Severity.ERROR,
                message=f"Tabela 'fat_': campo(s) obrigatório(s) ausente(s): {', '.join(missing)}.",
                details="Para tabelas com prefixo 'fat_', devem constar as colunas dat_carga e sk_sistema_origem.",
            ))

    # Tabelas dim_: requer dat_carga
    if has_dim:
        if has_dat_carga:
            results.append(ValidationResult(
                category="Campos Obrigatórios",
                severity=Severity.OK,
                message="Tabela 'dim_': campo obrigatório 'dat_carga' encontrado.",
            ))
        else:
            results.append(ValidationResult(
                category="Campos Obrigatórios",
                severity=Severity.ERROR,
                message="Tabela 'dim_': campo obrigatório 'dat_carga' ausente.",
                details="Para tabelas com prefixo 'dim_', deve constar a coluna dat_carga.",
            ))

        # Aviso sobre registro obrigatório -1
        results.append(ValidationResult(
            category="Registros Obrigatórios",
            severity=Severity.WARNING,
            message="Validar a presença do registro obrigatório -1.",
            details=(
                "Para tabelas 'dim_', deve existir o registro obrigatório:\n"
                "  CÓDIGO: -1 | DESCRIÇÃO: Não identificado | DESCRIÇÃO ABREVIADA: NI"
            ),
        ))

    return results
