"""Validações de localização do notebook e mensagens de aviso contextuais."""

from __future__ import annotations

import re

from app.parser.notebook_parser import ParsedNotebook
from app.validators.models import Severity, ValidationResult

_INGESTAO_CATALOG = re.compile(r"\b3_prd_ingestao\b", re.IGNORECASE)
_LAKEHOUSE_CATALOGS = re.compile(
    r"\b3_prd_lakehouse(?:_rwd)?\b", re.IGNORECASE
)


def _detect_target_catalog(notebook: ParsedNotebook) -> str | None:
    """Detecta qual catálogo é referenciado no notebook."""
    full = notebook.full_code
    if _INGESTAO_CATALOG.search(full):
        return "3_prd_ingestao"
    if _LAKEHOUSE_CATALOGS.search(full):
        match = _LAKEHOUSE_CATALOGS.search(full)
        return match.group(0) if match else "3_prd_lakehouse"
    return None


def validate_location(notebook: ParsedNotebook) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    catalog = _detect_target_catalog(notebook)

    if catalog == "3_prd_ingestao":
        results.append(ValidationResult(
            category="Localização do Notebook",
            severity=Severity.WARNING,
            message="Notebook referencia catálogo 3_prd_ingestao.",
            details=(
                "Se atentar quanto a localização do notebook, conforme classificação:\n"
                "  - 0_feature: notebooks parametrizáveis que podem ser aplicados para "
                "diversos sistemas, como integrações via API e arquivos Sharepoint;\n"
                "  - 1_raw: notebooks específicos e aplicados para ou por determinado "
                "sistema, como provenientes do TASY ou Forcare, por exemplo."
            ),
        ))
        results.append(ValidationResult(
            category="Localização do Notebook",
            severity=Severity.WARNING,
            message="Para novos schemas no catálogo 3_prd_ingestao, deverá haver a inclusão da Tag Governada 'tipo sistema'.",
        ))

    if catalog and catalog.startswith("3_prd_lakehouse"):
        results.append(ValidationResult(
            category="Localização do Notebook",
            severity=Severity.WARNING,
            message=f"Notebook referencia catálogo {catalog}.",
            details=(
                "Se atentar quanto a localização do notebook, conforme classificação:\n"
                "  - Schemas iniciados com 2_tru: Notebook de criação de tabela de segunda camada;\n"
                "  - Schema 3_ref: Notebook de criação de tabela fato e dimensão;\n"
                "  - Schema 4_rel: Notebook de criação relatório;\n"
                "  - Schemas iniciados com 5_srv: Notebook de criação de tabela para terceiros ou parceiros. Validar com a liderança;\n"
                "  - Schema 6_ext: Notebook de criação de tabela para terceiros ou parceiros. Validar com a liderança."
            ),
        ))

    if not catalog:
        results.append(ValidationResult(
            category="Localização do Notebook",
            severity=Severity.WARNING,
            message="Não foi possível identificar o catálogo de destino no notebook.",
            details="Verifique manualmente se o notebook está na localização correta.",
        ))

    return results
