"""Validações de cabeçalho e informações iniciais do notebook."""

from __future__ import annotations

import re

from app.parser.notebook_parser import ParsedNotebook
from app.validators.models import Severity, ValidationResult

_FUNCIONALIDADE_PATTERN = re.compile(
    r"funcionalidade\s+e\s+objetivo", re.IGNORECASE
)
_VERSOES_PATTERN = re.compile(r"vers[õo]es", re.IGNORECASE)
_DDL_PATTERN = re.compile(
    r"\bCREATE\s+OR\s+REPLACE\s+TABLE\b", re.IGNORECASE
)
_SHOW_CREATE_PATTERN = re.compile(
    r"\bSHOW\s+CREATE\s+TABLE\b", re.IGNORECASE
)
_SANDBOX_CATALOG = re.compile(r"\b3_prd_sandbox\b", re.IGNORECASE)
_INGESTAO_CATALOG = re.compile(r"\b3_prd_ingestao\b", re.IGNORECASE)
_LAKEHOUSE_CATALOGS = re.compile(
    r"\b3_prd_lakehouse(?:_rwd)?\b", re.IGNORECASE
)
_SCHEMA_3REF_4REL = re.compile(r"\b(3_ref|4_rel)\b", re.IGNORECASE)


def validate_header(notebook: ParsedNotebook) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    full_text = notebook.full_code

    # 1. Cabeçalho: "Funcionalidade e objetivo"
    has_func = any(
        _FUNCIONALIDADE_PATTERN.search(c.content)
        for c in notebook.cells
    )
    if has_func:
        results.append(ValidationResult(
            category="Cabeçalho",
            severity=Severity.OK,
            message="Célula 'Funcionalidade e objetivo' encontrada.",
        ))
    else:
        results.append(ValidationResult(
            category="Cabeçalho",
            severity=Severity.ERROR,
            message="Célula 'Funcionalidade e objetivo' NÃO encontrada.",
            details="O notebook deve conter uma célula de cabeçalho com 'Funcionalidade e objetivo'.",
        ))

    # 2. Cabeçalho: "Versões"
    has_versoes = any(
        _VERSOES_PATTERN.search(c.content)
        for c in notebook.cells
    )
    if has_versoes:
        results.append(ValidationResult(
            category="Cabeçalho",
            severity=Severity.OK,
            message="Célula 'Versões' encontrada.",
        ))
    else:
        results.append(ValidationResult(
            category="Cabeçalho",
            severity=Severity.ERROR,
            message="Célula 'Versões' NÃO encontrada.",
            details="O notebook deve conter uma célula de cabeçalho com tabela de 'Versões' (Versão, Data, Desenvolvedor, Descrição).",
        ))

    # Aviso de atualização de versão
    if has_versoes:
        results.append(ValidationResult(
            category="Cabeçalho",
            severity=Severity.WARNING,
            message="Validar se houve atualização da versão do cabeçalho do notebook.",
        ))

    # 3. Não deve conter DDL (CREATE OR REPLACE TABLE)
    ddl_cells = [c for c in notebook.cells if _DDL_PATTERN.search(c.content)]
    if ddl_cells:
        results.append(ValidationResult(
            category="Informações Iniciais",
            severity=Severity.ERROR,
            message="Encontrada DDL 'CREATE OR REPLACE TABLE' no notebook.",
            details=f"Células com DDL: {[c.index for c in ddl_cells]}. Não deve constar DDL de criação de tabela.",
        ))
    else:
        results.append(ValidationResult(
            category="Informações Iniciais",
            severity=Severity.OK,
            message="Nenhuma DDL 'CREATE OR REPLACE TABLE' encontrada.",
        ))

    # 4. Deve conter SHOW CREATE TABLE
    has_show = any(_SHOW_CREATE_PATTERN.search(c.content) for c in notebook.cells)
    if has_show:
        results.append(ValidationResult(
            category="Informações Iniciais",
            severity=Severity.OK,
            message="Comando 'SHOW CREATE TABLE' encontrado.",
        ))
    else:
        results.append(ValidationResult(
            category="Informações Iniciais",
            severity=Severity.ERROR,
            message="Comando 'SHOW CREATE TABLE' NÃO encontrado.",
            details="O notebook deve conter uma célula com o comando SHOW CREATE TABLE.",
        ))

    # 5. Não deve conter tabelas do catálogo 3_prd_sandbox
    if _SANDBOX_CATALOG.search(full_text):
        results.append(ValidationResult(
            category="Informações Iniciais",
            severity=Severity.ERROR,
            message="Referência ao catálogo '3_prd_sandbox' encontrada.",
            details="Não deve conter tabelas do catálogo 3_prd_sandbox no notebook.",
        ))
    else:
        results.append(ValidationResult(
            category="Informações Iniciais",
            severity=Severity.OK,
            message="Nenhuma referência ao catálogo '3_prd_sandbox'.",
        ))

    # 6. Não deve conter 3_prd_ingestao em notebooks de 3_ref/4_rel dos catálogos lakehouse
    has_lakehouse = _LAKEHOUSE_CATALOGS.search(full_text)
    has_ref_rel = _SCHEMA_3REF_4REL.search(full_text)
    has_ingestao = _INGESTAO_CATALOG.search(full_text)

    if has_lakehouse and has_ref_rel and has_ingestao:
        results.append(ValidationResult(
            category="Informações Iniciais",
            severity=Severity.ERROR,
            message="Referência a '3_prd_ingestao' em notebook de schemas 3_ref/4_rel do catálogo lakehouse.",
            details="Não deve conter tabelas do catálogo 3_prd_ingestao em notebooks de criação de tabelas dos schemas 3_ref e 4_rel.",
        ))
    elif has_lakehouse and has_ref_rel:
        results.append(ValidationResult(
            category="Informações Iniciais",
            severity=Severity.OK,
            message="Notebook de schemas 3_ref/4_rel sem referências indevidas a 3_prd_ingestao.",
        ))

    return results
